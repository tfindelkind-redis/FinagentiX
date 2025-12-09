"""
Orchestrator Agent - Coordinates workflow across specialized agents.

This agent:
- Receives user queries about stocks/investments
- Routes queries to specialized agents based on semantic analysis
- Coordinates parallel and sequential workflows
- Synthesizes final responses
"""

from typing import Dict, List, Optional, Any
from src.agents.base_agent import BaseAgent


class OrchestratorAgent(BaseAgent):
    """
    Orchestrates multi-agent workflows for investment analysis.
    
    Uses semantic routing to determine which specialized agents to invoke,
    coordinates their execution, and synthesizes final responses.
    """
    
    def __init__(self):
        instructions = """You are the Orchestrator Agent for FinagentiX, an AI-powered investment analysis system.

Your role is to:
1. Analyze incoming user queries about stocks, investments, or financial analysis
2. Determine which specialized agents are needed to answer the query:
   - Market Data Agent: For stock prices, technical indicators, trading volume
   - News Sentiment Agent: For news articles and sentiment analysis
   - Risk Assessment Agent: For volatility, risk metrics, portfolio analysis
   - Fundamental Analysis Agent: For SEC filings, financial statements, company fundamentals
3. Coordinate agent execution (parallel when possible, sequential when needed)
4. Call the Synthesis Agent to combine results into a coherent response
5. Return the final answer to the user

You have access to:
- Semantic routing cache to check for similar historical queries
- Router cache to reuse workflow decisions
- All specialized agent tools

When routing:
- For price queries: Use Market Data Agent
- For news/sentiment: Use News Sentiment Agent
- For risk/volatility: Use Risk Agent
- For financials/earnings: Use Fundamental Agent
- For complex queries: Coordinate multiple agents in parallel

Always check caches first to minimize costs and latency.
"""
        
        super().__init__(
            name="orchestrator",
            instructions=instructions,
            tools=None  # Will be populated with agent coordination tools in Phase 5.4
        )
    
    async def run(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Orchestrate multi-agent workflow for the given task.
        
        Args:
            task: User query about stocks/investments
            context: Optional context including conversation history, user preferences
            
        Returns:
            Dict with:
                - answer: Final synthesized response
                - agents_used: List of agents invoked
                - cache_hits: Number of cache hits
                - latency_ms: Total latency
        """
        # Check semantic cache for identical or similar queries
        cached_response = self.check_semantic_cache(task)
        if cached_response:
            return {
                "answer": cached_response["answer"],
                "agents_used": cached_response.get("agents_used", []),
                "cache_hits": 1,
                "latency_ms": cached_response.get("latency_ms", 0),
                "cached": True
            }
        
        # Check router cache for workflow pattern
        import hashlib
        import json
        
        workflow_key = f"route:{hashlib.md5(task.encode()).hexdigest()}"
        cached_workflow = self.redis.get(workflow_key)
        
        if cached_workflow:
            # Reuse cached routing decision
            workflow = json.loads(cached_workflow)
            agents_to_invoke = workflow["agents"]
        else:
            # Determine which agents to invoke using LLM
            # This will be implemented in Phase 5.4
            agents_to_invoke = await self._route_query(task, context)
            
            # Cache routing decision
            self.redis.setex(
                workflow_key,
                self.config.routing_cache_ttl,
                json.dumps({
                    "agents": agents_to_invoke,
                    "query": task
                })
            )
        
        # Coordinate agent execution
        # This will be implemented in Phase 5.4 with actual agent invocations
        results = await self._execute_workflow(agents_to_invoke, task, context)
        
        # Synthesize final response
        final_answer = await self._synthesize_response(results, task)
        
        # Cache the complete response
        response = {
            "answer": final_answer,
            "agents_used": agents_to_invoke,
            "cache_hits": 0,
            "latency_ms": 0,  # Will track in Phase 5.4
            "cached": False
        }
        
        self.cache_response(task, response)
        
        return response
    
    async def _route_query(self, query: str, context: Optional[Dict]) -> List[str]:
        """
        Determine which specialized agents to invoke.
        
        TODO Phase 5.4: Implement using Azure OpenAI with routing prompt.
        
        Returns:
            List of agent names to invoke (e.g., ["market_data", "news_sentiment"])
        """
        # Placeholder - will implement with LLM routing
        return ["market_data"]
    
    async def _execute_workflow(
        self,
        agents: List[str],
        query: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        Execute workflow by invoking specified agents.
        
        TODO Phase 5.4: Implement parallel and sequential agent execution.
        
        Returns:
            Dict mapping agent names to their results
        """
        # Placeholder - will implement with actual agent invocations
        return {}
    
    async def _synthesize_response(
        self,
        agent_results: Dict[str, Any],
        original_query: str
    ) -> str:
        """
        Synthesize final response from agent results.
        
        TODO Phase 5.4: Call Synthesis Agent to combine results.
        
        Returns:
            Final natural language response
        """
        # Placeholder - will call Synthesis Agent
        return "Response will be synthesized in Phase 5.4"
