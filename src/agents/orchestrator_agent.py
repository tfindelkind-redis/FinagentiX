"""Core orchestrator that coordinates multi-agent workflows."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from src.agents.base_agent import BaseAgent
from src.agents.synthesis_agent import SynthesisAgent
from src.redis import SemanticRouter, ToolCache, WorkflowOutcomeStore

# Lazy import to avoid circular dependency with orchestration.workflows
# The workflows module imports from agents.plugins which imports agents/__init__.py
# which imports this module
if TYPE_CHECKING:
    from src.orchestration.workflows import (
        InvestmentAnalysisWorkflow,
        MarketResearchWorkflow,
        PortfolioReviewWorkflow,
        QuickQuoteWorkflow,
    )

_workflow_classes = None

def _get_workflow_classes():
    """Lazy load workflow classes to avoid circular imports."""
    global _workflow_classes
    if _workflow_classes is None:
        from src.orchestration.workflows import (
            InvestmentAnalysisWorkflow,
            MarketResearchWorkflow,
            PortfolioReviewWorkflow,
            QuickQuoteWorkflow,
        )
        _workflow_classes = {
            "InvestmentAnalysisWorkflow": InvestmentAnalysisWorkflow,
            "MarketResearchWorkflow": MarketResearchWorkflow,
            "PortfolioReviewWorkflow": PortfolioReviewWorkflow,
            "QuickQuoteWorkflow": QuickQuoteWorkflow,
        }
    return _workflow_classes


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
            tools=None,
        )

        self.logger = logging.getLogger(self.__class__.__name__)
        self.semantic_router = SemanticRouter() if self.config.enable_routing_cache else None
        self.tool_cache = ToolCache()
        self.synthesis_agent = SynthesisAgent()
        self._workflow_outcome_store: Optional[WorkflowOutcomeStore] = None
        self._workflow_registry: Optional[Dict[str, Dict[str, Any]]] = None
        self.workflow_aliases = {
            "TechnicalAnalysisWorkflow": "InvestmentAnalysisWorkflow",
            "RiskAssessmentWorkflow": "InvestmentAnalysisWorkflow",
        }
    
    @property
    def workflow_registry(self) -> Dict[str, Dict[str, Any]]:
        """Lazy-loaded workflow registry to avoid circular imports."""
        if self._workflow_registry is None:
            wf_classes = _get_workflow_classes()
            self._workflow_registry = {
                "InvestmentAnalysisWorkflow": {
                    "class": wf_classes["InvestmentAnalysisWorkflow"],
                    "pattern": "concurrent",
                    "agents": [
                        "market_data",
                        "technical_analysis",
                        "risk_analysis",
                        "news_sentiment",
                    ],
                    "requires_ticker": True,
                },
                "QuickQuoteWorkflow": {
                    "class": wf_classes["QuickQuoteWorkflow"],
                    "pattern": "sequential",
                    "agents": ["market_data"],
                    "requires_ticker": True,
                },
                "PortfolioReviewWorkflow": {
                    "class": wf_classes["PortfolioReviewWorkflow"],
                    "pattern": "sequential",
                    "agents": ["portfolio", "risk_analysis"],
                    "requires_ticker": False,
                },
                "MarketResearchWorkflow": {
                    "class": wf_classes["MarketResearchWorkflow"],
                    "pattern": "concurrent",
                    "agents": ["market_data", "news_sentiment", "technical_analysis"],
                    "requires_ticker": False,
                },
            }
        return self._workflow_registry
    
    @property
    def workflow_outcomes(self) -> WorkflowOutcomeStore:
        if self._workflow_outcome_store is None:
            self._workflow_outcome_store = WorkflowOutcomeStore(self.redis)
        return self._workflow_outcome_store

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
        context = context or {}

        cached_response = self.check_semantic_cache(task)
        if cached_response:
            return {
                "answer": cached_response["answer"],
                "agents_used": cached_response.get("agents_used", []),
                "cache_hits": 1,
                "latency_ms": cached_response.get("latency_ms", 0),
                "cached": True,
                "workflow": cached_response.get("workflow"),
                "raw_result": cached_response.get("raw_result", {}),
            }

        query_embedding = context.get("query_embedding")
        if query_embedding is None:
            query_embedding = await self._create_embedding(task)

        route = None
        if self.semantic_router:
            try:
                route = self.semantic_router.find_route(
                    query=task,
                    query_embedding=query_embedding,
                    top_k=min(self.config.vector_top_k, 5),
                )
            except Exception as router_error:  # pragma: no cover - defensive log
                self.logger.warning("Router lookup failed: %s", router_error)

        derived_ticker = context.get("ticker") or self._extract_ticker(task)
        selected_workflow_key, matched_via = self._select_workflow(route, derived_ticker)
        workflow_config = self.workflow_registry[selected_workflow_key]

        execution_kwargs: Dict[str, Any] = {
            "rag_context": context.get("rag_context"),
            "user_context": context.get("user_context"),
        }

        if params := context.get("params"):
            execution_kwargs.update(params)

        if workflow_config.get("requires_ticker"):
            if not derived_ticker:
                message = (
                    "Please provide a stock ticker (e.g., 'Analyze AAPL') so I can run a full analysis."
                )
                response_payload = {
                    "answer": message,
                    "workflow": selected_workflow_key,
                    "agents_used": [],
                    "cache_hits": 0,
                    "cached": False,
                    "raw_result": {"response": message},
                }
                self.cache_response(task, response_payload)
                return response_payload
            execution_kwargs["ticker"] = derived_ticker
        elif selected_workflow_key == "PortfolioReviewWorkflow":
            execution_kwargs.setdefault("portfolio_id", context.get("portfolio_id", "default"))
        elif selected_workflow_key == "MarketResearchWorkflow":
            execution_kwargs["query"] = task
            if tickers := context.get("tickers"):
                execution_kwargs["tickers"] = tickers

        outcome_key = self._build_outcome_key(selected_workflow_key, execution_kwargs, task)
        cached_outcome = None
        if outcome_key:
            cached_outcome = self.workflow_outcomes.fetch(selected_workflow_key, outcome_key)
        if cached_outcome:
            result = cached_outcome.get("result", {})
            synthesis_output = cached_outcome.get("synthesis")
            final_answer = cached_outcome.get("final_answer") or self._format_response(result)

            if query_embedding is not None and self.semantic_router:
                try:
                    record_route_id = (
                        route.get("route_id")
                        if route and route.get("route_id")
                        else selected_workflow_key
                    )
                    self.semantic_router.record_route(
                        query=task,
                        query_embedding=query_embedding,
                        route_id=record_route_id,
                        workflow=selected_workflow_key,
                        agents=workflow_config["agents"],
                        source=matched_via,
                    )
                except Exception as record_error:  # pragma: no cover - defensive log
                    self.logger.warning("Failed to record semantic route: %s", record_error)

            response_payload = {
                "answer": final_answer,
                "workflow": selected_workflow_key,
                "agents_used": workflow_config["agents"],
                "cache_hits": 1,
                "cached": True,
                "raw_result": result,
                "synthesis": synthesis_output,
                "cached_outcome": {
                    "timestamp": cached_outcome.get("timestamp"),
                    "metadata": cached_outcome.get("metadata", {}),
                },
            }
            self.cache_response(task, response_payload)
            return response_payload

        workflow_instance = workflow_config["class"](
            tool_cache=self.tool_cache,
            redis_client=self.redis,
        )

        try:
            result = await workflow_instance.execute(**execution_kwargs)
        except Exception as workflow_error:
            self.logger.exception("Workflow %s failed", selected_workflow_key)
            result = {
                "response": f"I encountered an error while running {selected_workflow_key}: {workflow_error}"
            }

        synthesis_output = await self._invoke_synthesis(
            task=task,
            workflow_result=result,
            fallback_ticker=execution_kwargs.get("ticker") or derived_ticker,
        )

        if query_embedding is not None and self.semantic_router:
            try:
                record_route_id = (
                    route.get("route_id")
                    if route and route.get("route_id")
                    else selected_workflow_key
                )
                self.semantic_router.record_route(
                    query=task,
                    query_embedding=query_embedding,
                    route_id=record_route_id,
                    workflow=selected_workflow_key,
                    agents=workflow_config["agents"],
                    source=matched_via,
                )
            except Exception as record_error:  # pragma: no cover - defensive log
                self.logger.warning("Failed to record semantic route: %s", record_error)

        final_answer = None
        if synthesis_output and synthesis_output.get("status") == "success":
            final_answer = synthesis_output.get("answer")

        if not final_answer:
            final_answer = self._format_response(result)
        response_payload = {
            "answer": final_answer,
            "workflow": selected_workflow_key,
            "agents_used": workflow_config["agents"],
            "cache_hits": 0,
            "cached": False,
            "raw_result": result,
            "synthesis": synthesis_output,
        }

        if outcome_key:
            ttl_override = getattr(self.config, "routing_cache_ttl", 0) or None
            metadata = {"matched_via": matched_via, "context": execution_kwargs.get("user_context")}
            self.workflow_outcomes.store(
                workflow=selected_workflow_key,
                key_payload=outcome_key,
                result=result,
                synthesis=synthesis_output,
                final_answer=final_answer,
                metadata=metadata,
                ttl_seconds=ttl_override,
            )

        self.cache_response(task, response_payload)
        return response_payload
    
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

    async def _create_embedding(self, query: str) -> Optional[List[float]]:
        """Generate embedding for routing decisions using Azure OpenAI."""
        try:
            response = await asyncio.to_thread(
                self.openai.embeddings.create,
                input=query,
                model=self.config.azure_openai.embedding_deployment,
            )
            return response.data[0].embedding if response and response.data else None
        except Exception as embedding_error:  # pragma: no cover - defensive log
            self.logger.warning("Embedding generation failed: %s", embedding_error)
            return None

    def _select_workflow(
        self,
        route: Optional[Dict[str, Any]],
        derived_ticker: Optional[str],
    ) -> Tuple[str, str]:
        """Determine workflow to execute with fallback logic."""
        workflow_key = route.get("workflow") if route else None
        if workflow_key in self.workflow_aliases:
            workflow_key = self.workflow_aliases[workflow_key]

        matched_via = route.get("matched_via") if route else "fallback"
        if not workflow_key or workflow_key not in self.workflow_registry:
            workflow_key = "InvestmentAnalysisWorkflow" if derived_ticker else "MarketResearchWorkflow"
            matched_via = matched_via or "fallback"

        return workflow_key, matched_via

    @staticmethod
    def _build_outcome_key(
        workflow_key: str,
        execution_kwargs: Dict[str, Any],
        task: str,
    ) -> Optional[Dict[str, Any]]:
        if workflow_key == "InvestmentAnalysisWorkflow":
            ticker = execution_kwargs.get("ticker")
            if ticker:
                return {"ticker": ticker.upper()}
        elif workflow_key == "PortfolioReviewWorkflow":
            portfolio_id = execution_kwargs.get("portfolio_id", "default")
            return {"portfolio_id": portfolio_id}
        elif workflow_key == "QuickQuoteWorkflow":
            ticker = execution_kwargs.get("ticker")
            if ticker:
                return {"ticker": ticker.upper()}
        elif workflow_key == "MarketResearchWorkflow":
            tickers = execution_kwargs.get("tickers")
            normalized_tickers = None
            if tickers:
                normalized_tickers = sorted({str(t).upper() for t in tickers})
            return {
                "query": task.strip().lower(),
                "tickers": normalized_tickers,
            }
        return None

    @staticmethod
    def _extract_ticker(query: str) -> Optional[str]:
        """Extract potential stock ticker from user query."""
        import re

        patterns = [
            r"\b([A-Z]{1,5})\b(?:\s+stock|\s+shares?)",
            r"(?:ticker|symbol)\s+([A-Z]{1,5})\b",
            r"\$([A-Z]{1,5})\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, query.upper())
            if match:
                return match.group(1)

        words = query.upper().split()
        for word in words:
            if 2 <= len(word) <= 5 and word.isalpha():
                if word in {"AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"}:
                    return word

        return None

    @staticmethod
    def _format_response(result: Dict[str, Any]) -> str:
        """Format workflow output into a user-facing string."""
        if not result:
            return "Unable to process query."

        if "response" in result:
            return result["response"]

        if "recommendation" in result:
            ticker = result.get("ticker", "")
            rec = result.get("recommendation", {})
            signals = ", ".join(rec.get("signals", [])) if rec.get("signals") else "N/A"
            return (
                f"Investment Analysis for {ticker}:\n\n"
                f"Recommendation: {rec.get('action', 'N/A')}\n"
                f"Confidence: {rec.get('confidence', 'N/A')}\n"
                f"Signals: {signals}\n\n"
                f"{rec.get('summary', '')}"
            ).strip()

        if "positions" in result:
            positions = result.get("positions", {})
            header = "Portfolio Review:\n\n"
            if positions.get("success"):
                total_value = positions.get("total_value", 0)
                count = len(positions.get("positions", []))
                return f"{header}Total Value: ${total_value:,.2f}\nPositions: {count}"
            return header + "Unable to retrieve portfolio details."

        return str(result)

    async def _invoke_synthesis(
        self,
        task: str,
        workflow_result: Dict[str, Any],
        fallback_ticker: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Call synthesis agent when workflow exposes agent results."""
        agent_results = workflow_result.get("agent_results")
        if not agent_results:
            return None

        context = {
            "agent_results": agent_results,
            "ticker": workflow_result.get("ticker") or fallback_ticker,
            "query": task,
        }

        try:
            return await self.synthesis_agent.run(task, context=context)
        except Exception as synth_error:  # pragma: no cover - defensive log
            self.logger.warning("Synthesis agent failed: %s", synth_error)
            return {
                "status": "error",
                "message": f"Synthesis agent error: {synth_error}",
            }
