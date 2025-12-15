"""
Agent Orchestration Patterns for Semantic Kernel
Implements Sequential, Concurrent, and Handoff orchestration patterns
Enhanced with comprehensive metrics collection
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from ..utils.metrics_collector import MetricsCollector
from ..utils.cost_tracking import CostCalculator
import tiktoken


logger = logging.getLogger(__name__)


def _format_missing_deployment_message() -> str:
    """Generate a helpful message when the Azure deployment is missing."""
    configured = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_GPT4_DEPLOYMENT")
    deployment = configured or "<unset>"
    return (
        "Unable to reach the configured Azure OpenAI deployment. "
        f"Expected deployment '{deployment}', but Azure returned DeploymentNotFound.\n"
        "Fix this by either creating the deployment in your Azure OpenAI resource or updating "
        "AZURE_OPENAI_CHAT_DEPLOYMENT (and related settings) to match an existing deployment."
    )


def _coerce_to_text(payload: Any) -> str:
    """Convert agent output to plain text."""
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, ChatMessageContent):
        # Prefer direct string content when available
        if isinstance(payload.content, str):
            return payload.content
        items = getattr(payload, "items", None)
        if items:
            texts = [getattr(item, "text", "") for item in items if getattr(item, "text", "")]
            if texts:
                return "\n".join(texts)
        return str(payload)
    if isinstance(payload, list):
        texts = [_coerce_to_text(item) for item in payload]
        return "\n".join(filter(None, texts))
    if isinstance(payload, dict):
        try:
            return json.dumps(payload, indent=2, sort_keys=True)
        except (TypeError, ValueError):
            return str(payload)
    return str(payload)


class SequentialOrchestration:
    """
    Sequential orchestration pattern - agents execute in order
    
    Each agent receives the output from the previous agent as context.
    Useful for workflows where each step depends on the previous step.
    
    Example: Market Data → Sentiment Analysis → Investment Synthesis
    """
    
    def __init__(
        self,
        agents: List[ChatCompletionAgent],
        metrics_collector: Optional[MetricsCollector] = None
    ):
        """
        Initialize sequential orchestration
        
        Args:
            agents: List of agents to execute in order
            metrics_collector: Optional metrics collector for tracking
        """
        self.agents = agents
        self.metrics_collector = metrics_collector
        self.execution_history: List[Dict[str, Any]] = []
    
    async def execute(
        self,
        initial_query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute agents sequentially
        
        Args:
            initial_query: Initial user query
            context: Optional context to pass to all agents
        
        Returns:
            Dictionary with results from all agents
        """
        start_time = datetime.now()
        
        # Start orchestration tracking
        if self.metrics_collector:
            event_id = self.metrics_collector.start_event(
                "orchestration",
                "Sequential Orchestration"
            )
        
        results = {
            "initial_query": initial_query,
            "context": context or {},
            "agents": [],
            "final_result": None
        }
        
        current_message = initial_query
        history = []
        
        for idx, agent in enumerate(self.agents):
            agent_start = datetime.now()
            
            # Start agent tracking
            if self.metrics_collector:
                agent_event_id = self.metrics_collector.start_event(
                    "agent_execution",
                    f"Agent: {agent.name}"
                )
            
            # Add context from previous agents if available
            if results["agents"]:
                previous_results = "\n\n".join([
                    f"Previous output from {r['agent_name']}:\n{r['response']}"
                    for r in results["agents"]
                ])
                current_message = f"{initial_query}\n\nContext:\n{previous_results}"
            
            # Prepare chat history
            history.append(
                ChatMessageContent(
                    role=AuthorRole.USER,
                    content=current_message
                )
            )
            
            # Execute agent
            response_text = ""
            agent_status = "success"
            error_message = None
            try:
                async for message in agent.invoke(history):
                    if message.role == AuthorRole.ASSISTANT:
                        response_text = _coerce_to_text(message.content)
                        break
            except Exception as exc:  # pragma: no cover - defensive path
                error_message = str(exc)
                if "DeploymentNotFound" in error_message or "API deployment" in error_message:
                    agent_status = "error"
                    response_text = _format_missing_deployment_message()
                    logger.error("Azure OpenAI deployment missing: %s", error_message)
                else:
                    if self.metrics_collector:
                        self.metrics_collector.end_event(agent_event_id, status="error")
                    raise
            
            agent_end = datetime.now()
            agent_duration = (agent_end - agent_start).total_seconds() * 1000  # Convert to ms
            
            # Estimate tokens if we have a metrics collector
            input_tokens = 0
            output_tokens = 0
            cost = 0.0
            
            if self.metrics_collector:
                # Count tokens using tiktoken
                input_tokens = self.metrics_collector.cost_calculator.count_messages([
                    {"role": "user", "content": current_message}
                ])
                if response_text:
                    output_tokens = self.metrics_collector.cost_calculator.count_tokens(response_text)
                
                # Calculate cost (assuming gpt-4o)
                cost = self.metrics_collector.cost_calculator.calculate_llm_cost(
                    input_tokens,
                    output_tokens
                )
                temperature = getattr(agent, "temperature", 0.0)
                max_tokens = getattr(agent, "max_tokens", 0)
                
                # Record agent execution
                self.metrics_collector.record_agent_execution(
                    agent_name=agent.name,
                    agent_id=f"{agent.name.lower().replace(' ', '_')}_{idx}",
                    duration_ms=agent_duration,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    model="gpt-4o",  # Default model
                    cost=cost,
                    status=agent_status if response_text else "error",
                    response=response_text or "",
                    start_time=agent_start,
                    end_time=agent_end,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # End agent tracking
                end_status = agent_status if response_text else "error"
                self.metrics_collector.end_event(agent_event_id, status=end_status)
            elif error_message is not None:
                # Ensure error is logged when we don't have metrics collector
                logger.error("Agent %s failed: %s", agent.name, error_message)
            
            # Record result
            agent_result = {
                "agent_name": agent.name,
                "agent_index": idx,
                "response": response_text,
                "duration_seconds": agent_duration / 1000,
                "duration_ms": agent_duration,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
                "timestamp": agent_end.isoformat(),
                "status": agent_status if response_text else "error"
            }
            if error_message:
                agent_result["error"] = error_message
            results["agents"].append(agent_result)
            
            # Add agent response to history
            if response_text:
                history.append(
                    ChatMessageContent(
                        role=AuthorRole.ASSISTANT,
                        content=response_text,
                        name=agent.name
                    )
                )
        
        # Set final result as the last agent's response
        if results["agents"]:
            results["final_result"] = results["agents"][-1]["response"]
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        results["total_duration_seconds"] = total_duration
        results["total_duration_ms"] = total_duration * 1000
        results["execution_pattern"] = "sequential"
        
        # End orchestration tracking
        if self.metrics_collector:
            self.metrics_collector.end_event(event_id, status="success")
        
        # Store in history
        self.execution_history.append(results)
        
        return results


class ConcurrentOrchestration:
    """
    Concurrent orchestration pattern - agents execute in parallel
    
    All agents receive the same input and execute simultaneously.
    Useful for gathering multiple perspectives or independent analyses.
    
    Example: Parallel analysis of Market Data + Sentiment + Technical Indicators
    """
    
    def __init__(
        self,
        agents: List[ChatCompletionAgent],
        metrics_collector: Optional[MetricsCollector] = None
    ):
        """
        Initialize concurrent orchestration
        
        Args:
            agents: List of agents to execute in parallel
            metrics_collector: Optional metrics collector for tracking
        """
        self.agents = agents
        self.metrics_collector = metrics_collector
        self.execution_history: List[Dict[str, Any]] = []
    
    async def execute(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute agents concurrently
        
        Args:
            query: User query to send to all agents
            context: Optional context to pass to all agents
        
        Returns:
            Dictionary with results from all agents
        """
        start_time = datetime.now()
        
        # Start orchestration tracking
        if self.metrics_collector:
            event_id = self.metrics_collector.start_event(
                "orchestration",
                "Concurrent Orchestration"
            )
        
        results = {
            "query": query,
            "context": context or {},
            "agents": [],
            "combined_result": None
        }
        
        # Create tasks for all agents
        async def execute_agent(agent: ChatCompletionAgent, idx: int) -> Dict[str, Any]:
            agent_start = datetime.now()
            
            # Start agent tracking
            if self.metrics_collector:
                agent_event_id = self.metrics_collector.start_event(
                    "agent_execution",
                    f"Agent: {agent.name}"
                )
            
            history = [
                ChatMessageContent(
                    role=AuthorRole.USER,
                    content=query
                )
            ]
            
            response_text = ""
            agent_status = "success"
            error_message = None
            try:
                async for message in agent.invoke(history):
                    if message.role == AuthorRole.ASSISTANT:
                        response_text = _coerce_to_text(message.content)
                        break
            except Exception as exc:  # pragma: no cover - defensive path
                error_message = str(exc)
                if "DeploymentNotFound" in error_message or "API deployment" in error_message:
                    agent_status = "error"
                    response_text = _format_missing_deployment_message()
                    logger.error("Azure OpenAI deployment missing: %s", error_message)
                else:
                    if self.metrics_collector:
                        self.metrics_collector.end_event(agent_event_id, status="error")
                    raise
            
            agent_end = datetime.now()
            agent_duration = (agent_end - agent_start).total_seconds() * 1000
            
            # Estimate tokens and cost
            input_tokens = 0
            output_tokens = 0
            cost = 0.0
            
            if self.metrics_collector:
                input_tokens = self.metrics_collector.cost_calculator.count_messages([
                    {"role": "user", "content": query}
                ])
                if response_text:
                    output_tokens = self.metrics_collector.cost_calculator.count_tokens(response_text)
                
                cost = self.metrics_collector.cost_calculator.calculate_llm_cost(
                    input_tokens,
                    output_tokens
                )
                temperature = getattr(agent, "temperature", 0.0)
                max_tokens = getattr(agent, "max_tokens", 0)
                
                # Record agent execution
                self.metrics_collector.record_agent_execution(
                    agent_name=agent.name,
                    agent_id=f"{agent.name.lower().replace(' ', '_')}_{idx}",
                    duration_ms=agent_duration,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    model="gpt-4o",
                    cost=cost,
                    status=agent_status if response_text else "error",
                    response=response_text or "",
                    start_time=agent_start,
                    end_time=agent_end,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # End agent tracking
                end_status = agent_status if response_text else "error"
                self.metrics_collector.end_event(agent_event_id, status=end_status)
            elif error_message is not None:
                logger.error("Agent %s failed: %s", agent.name, error_message)
            
            result_payload = {
                "agent_name": agent.name,
                "agent_index": idx,
                "response": response_text,
                "duration_seconds": agent_duration / 1000,
                "duration_ms": agent_duration,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
                "timestamp": agent_end.isoformat(),
                "status": agent_status if response_text else "error"
            }
            if error_message:
                result_payload["error"] = error_message
            return result_payload
        
        # Execute all agents concurrently
        tasks = [execute_agent(agent, idx) for idx, agent in enumerate(self.agents)]
        agent_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in agent_results:
            if isinstance(result, Exception):
                results["agents"].append({
                    "error": str(result),
                    "agent_name": "Unknown",
                    "response": None
                })
            else:
                results["agents"].append(result)
        
        # Combine all responses
        successful_results = [r for r in results["agents"] if r.get("response")]
        if successful_results:
            combined = "\n\n".join([
                f"### {r['agent_name']}:\n{r['response']}"
                for r in successful_results
            ])
            results["combined_result"] = combined
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        results["total_duration_seconds"] = total_duration
        results["total_duration_ms"] = total_duration * 1000
        results["execution_pattern"] = "concurrent"
        
        # End orchestration tracking
        if self.metrics_collector:
            self.metrics_collector.end_event(event_id, status="success")
        
        # Store in history
        self.execution_history.append(results)
        
        return results


class HandoffOrchestration:
    """
    Handoff orchestration pattern - dynamic agent selection
    
    An agent can explicitly hand off to another agent based on the query.
    Useful for routing queries to specialized agents.
    
    Example: Triage Agent → Market Data Agent or Sentiment Agent
    """
    
    def __init__(
        self,
        agents: Dict[str, ChatCompletionAgent],
        router: Optional[Callable[[str], str]] = None,
        metrics_collector: Optional[MetricsCollector] = None
    ):
        """
        Initialize handoff orchestration
        
        Args:
            agents: Dictionary mapping agent names to agent instances
            router: Optional function to determine which agent to use
            metrics_collector: Optional metrics collector for tracking
        """
        self.agents = agents
        self.router = router
        self.metrics_collector = metrics_collector
        self.execution_history: List[Dict[str, Any]] = []
    
    async def execute(
        self,
        query: str,
        initial_agent: Optional[str] = None,
        max_handoffs: int = 5
    ) -> Dict[str, Any]:
        """
        Execute with handoff support
        
        Args:
            query: User query
            initial_agent: Name of agent to start with (uses router if None)
            max_handoffs: Maximum number of handoffs to prevent loops
        
        Returns:
            Dictionary with execution results
        """
        start_time = datetime.now()
        
        # Start orchestration tracking
        if self.metrics_collector:
            event_id = self.metrics_collector.start_event(
                "orchestration",
                "Handoff Orchestration"
            )
        
        results = {
            "query": query,
            "handoff_chain": [],
            "final_result": None
        }
        
        # Determine initial agent
        current_agent_name = initial_agent
        if current_agent_name is None and self.router:
            current_agent_name = self.router(query)
        elif current_agent_name is None:
            # Default to first agent
            current_agent_name = list(self.agents.keys())[0]
        
        history = [
            ChatMessageContent(
                role=AuthorRole.USER,
                content=query
            )
        ]
        
        handoff_count = 0
        
        while handoff_count < max_handoffs:
            if current_agent_name not in self.agents:
                results["handoff_chain"].append({
                    "error": f"Agent '{current_agent_name}' not found",
                    "agent_name": current_agent_name
                })
                break
            
            agent = self.agents[current_agent_name]
            agent_start = datetime.now()
            
            # Start agent tracking
            if self.metrics_collector:
                agent_event_id = self.metrics_collector.start_event(
                    "agent_execution",
                    f"Agent: {current_agent_name}"
                )
            
            # Execute agent
            response_text = ""
            async for message in agent.invoke(history):
                if message.role == AuthorRole.ASSISTANT:
                    response_text = _coerce_to_text(message.content)
                    break
            
            agent_end = datetime.now()
            agent_duration = (agent_end - agent_start).total_seconds() * 1000
            
            # Estimate tokens and cost
            input_tokens = 0
            output_tokens = 0
            cost = 0.0
            
            if self.metrics_collector:
                input_tokens = self.metrics_collector.cost_calculator.count_messages([
                    {"role": "user", "content": query}
                ])
                if response_text:
                    output_tokens = self.metrics_collector.cost_calculator.count_tokens(response_text)
                
                cost = self.metrics_collector.cost_calculator.calculate_llm_cost(
                    input_tokens,
                    output_tokens
                )
                temperature = getattr(agent, "temperature", 0.0)
                max_tokens = getattr(agent, "max_tokens", 0)
                
                # Record agent execution
                self.metrics_collector.record_agent_execution(
                    agent_name=current_agent_name,
                    agent_id=f"{current_agent_name.lower().replace(' ', '_')}_{handoff_count}",
                    duration_ms=agent_duration,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    model="gpt-4o",
                    cost=cost,
                    status="success" if response_text else "error",
                    response=response_text or "",
                    start_time=agent_start,
                    end_time=agent_end,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # End agent tracking
                end_status = "success" if response_text else "error"
                self.metrics_collector.end_event(agent_event_id, status=end_status)
            
            # Record handoff
            handoff = {
                "agent_name": current_agent_name,
                "response": response_text,
                "duration_seconds": agent_duration / 1000,
                "duration_ms": agent_duration,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
                "timestamp": agent_end.isoformat(),
                "handoff_index": handoff_count
            }
            results["handoff_chain"].append(handoff)
            
            # Add response to history
            if response_text:
                history.append(
                    ChatMessageContent(
                        role=AuthorRole.ASSISTANT,
                        content=response_text,
                        name=current_agent_name
                    )
                )
            
            # Check for handoff signal (simple implementation)
            # In practice, you'd parse the response for explicit handoff commands
            # For now, we stop after one agent
            break
        
        # Set final result
        if results["handoff_chain"]:
            results["final_result"] = results["handoff_chain"][-1].get("response")
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        results["total_duration_seconds"] = total_duration
        results["total_duration_ms"] = total_duration * 1000
        results["execution_pattern"] = "handoff"
        results["total_handoffs"] = len(results["handoff_chain"])
        
        # End orchestration tracking
        if self.metrics_collector:
            self.metrics_collector.end_event(event_id, status="success")
        
        # Store in history
        self.execution_history.append(results)
        
        return results


# Example usage and testing
async def test_orchestrations():
    """Test all orchestration patterns"""
    from sk_config import get_global_config
    from market_data_agent_sk import MarketDataAgentSK
    
    print("Testing Orchestration Patterns\n")
    print("=" * 60)
    
    # Create agents
    config = get_global_config()
    market_agent = MarketDataAgentSK()
    
    # Test 1: Sequential orchestration (simplified - using same agent multiple times)
    print("\nTest 1: Sequential Orchestration")
    print("-" * 60)
    
    sequential = SequentialOrchestration(
        agents=[market_agent.agent]  # In practice, use different agents
    )
    
    result = await sequential.execute(
        "What is the current price of AAPL?"
    )
    
    print(f"Pattern: {result['execution_pattern']}")
    print(f"Total duration: {result['total_duration_seconds']:.2f}s")
    print(f"Agents executed: {len(result['agents'])}")
    if result['final_result']:
        print(f"Final result: {result['final_result'][:200]}...")
    
    # Test 2: Concurrent orchestration
    print("\n\nTest 2: Concurrent Orchestration")
    print("-" * 60)
    
    concurrent = ConcurrentOrchestration(
        agents=[market_agent.agent]  # In practice, use different agents
    )
    
    result = await concurrent.execute(
        "Analyze MSFT and GOOGL performance over the last 7 days"
    )
    
    print(f"Pattern: {result['execution_pattern']}")
    print(f"Total duration: {result['total_duration_seconds']:.2f}s")
    print(f"Agents executed: {len(result['agents'])}")
    if result['combined_result']:
        print(f"Combined result: {result['combined_result'][:200]}...")
    
    # Test 3: Handoff orchestration
    print("\n\nTest 3: Handoff Orchestration")
    print("-" * 60)
    
    handoff = HandoffOrchestration(
        agents={"MarketDataAgent": market_agent.agent}
    )
    
    result = await handoff.execute(
        "Get AAPL stock price",
        initial_agent="MarketDataAgent"
    )
    
    print(f"Pattern: {result['execution_pattern']}")
    print(f"Total duration: {result['total_duration_seconds']:.2f}s")
    print(f"Handoffs: {result['total_handoffs']}")
    if result['final_result']:
        print(f"Final result: {result['final_result'][:200]}...")
    
    print("\n" + "=" * 60)
    print("✅ Orchestration tests completed!")


if __name__ == "__main__":
    asyncio.run(test_orchestrations())
