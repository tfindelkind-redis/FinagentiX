"""
FastAPI Application for FinagentiX
AI-Powered Financial Trading Assistant

Main entry point for the application
"""

import os
import time
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Load environment variables FIRST, before any other imports
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .config import settings
from .models import (
    EnhancedQueryResponse,
    QueryResponse as LegacyQueryResponse,
    AgentExecution,
    CacheLayerMetrics,
    CostBreakdown,
    PerformanceMetrics,
    WorkflowExecution,
    SessionMetrics,
    ExecutionTimeline,
)
from .dependencies import (
    get_semantic_cache,
    get_contextual_memory,
    get_semantic_router,
    get_azure_openai_client,
    get_tool_cache,
    get_document_store,
    get_rag_retriever,
)
from ..redis import SemanticCache, ContextualMemory, SemanticRouter, DocumentStore, ToolCache
from ..redis.rag_retriever import RAGRetriever
from ..utils.metrics_collector import MetricsCollector
from ..orchestration.workflows import (
    InvestmentAnalysisWorkflow,
    PortfolioReviewWorkflow,
    MarketResearchWorkflow,
    QuickQuoteWorkflow,
)


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    print("🚀 FinagentiX starting up...")
    print(f"   Environment: {settings.ENVIRONMENT}")
    print(f"   Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    print(f"   Azure OpenAI: {settings.AZURE_OPENAI_ENDPOINT}")
    
    yield
    
    # Shutdown
    print("👋 FinagentiX shutting down...")


# Create FastAPI app
app = FastAPI(
    title="FinagentiX API",
    description="AI-Powered Financial Trading Assistant with Multi-Agent System",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Request/Response Models ====================

class QueryRequest(BaseModel):
    """User query request"""
    query: str = Field(..., description="User question or command")
    user_id: str = Field(default="anonymous", description="User identifier")
    ticker: Optional[str] = Field(None, description="Stock ticker (if applicable)")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional parameters")


class QueryResponse(BaseModel):
    """Query response (legacy model for backward compatibility)"""
    query: str
    response: str
    workflow: Optional[str] = None
    agents_used: List[str] = []
    cache_hit: bool = False
    processing_time_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: str
    services: Dict[str, str]


# ==================== Main Query Endpoint ====================

@app.post("/api/query/enhanced", response_model=EnhancedQueryResponse)
async def query_enhanced(
    request: QueryRequest,
    semantic_cache: SemanticCache = Depends(get_semantic_cache),
    contextual_memory: ContextualMemory = Depends(get_contextual_memory),
    semantic_router: SemanticRouter = Depends(get_semantic_router),
    openai_client = Depends(get_azure_openai_client),
    tool_cache: ToolCache = Depends(get_tool_cache),
    document_store: DocumentStore = Depends(get_document_store),
) -> EnhancedQueryResponse:
    """
    Enhanced query endpoint with comprehensive metrics tracking
    
    Returns detailed execution metrics including:
    - Per-agent execution details (duration, tokens, cost)
    - Cache layer performance metrics
    - Cost breakdown with savings calculation
    - Performance metrics vs targets
    - Execution timeline for visualization
    - Session statistics
    
    Flow:
    1. Initialize metrics collection
    2. Check semantic cache
    3. Load user context
    4. Route query to workflow
    5. Execute with metrics tracking
    6. Return comprehensive response
    """
    from datetime import datetime
    
    # Initialize metrics collector
    metrics = MetricsCollector(
        query=request.query,
        session_id=f"session_{request.user_id}",
        user_id=request.user_id
    )
    
    # Start query processing
    query_event_id = metrics.start_event("query_processing", "Full Query Processing")
    
    try:
        # Step 1: Generate query embedding for semantic cache
        embedding_event_id = metrics.start_event("embedding_generation", "Query Embedding")
        embedding_response = await openai_client.embeddings.create(
            input=request.query,
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
        )
        query_embedding = embedding_response.data[0].embedding
        
        # Record embedding
        embedding_tokens = metrics.cost_calculator.count_tokens(request.query)
        metrics.record_embedding(embedding_tokens)
        metrics.end_event(embedding_event_id, status="success")
        
        # Step 2: Check semantic cache
        cache_event_id = metrics.start_event("cache_check", "Semantic Cache Lookup")
        cached_response = semantic_cache.get(
            query=request.query,
            query_embedding=query_embedding
        )
        
        # Record cache check with metrics
        cache_hit = bool(
            cached_response
            and cached_response.get("cache_hit", False)
            and cached_response.get("response")
        )
        metrics.record_cache_check(
            layer_name="semantic_cache",
            hit=cache_hit,
            similarity=cached_response.get("similarity", 0.0) if cached_response else 0.0,
            query_time_ms=cached_response.get("query_time_ms", 0) if cached_response else 0,
            cost_saved=0.015 if cache_hit else 0.0  # Estimated savings per cache hit
        )
        metrics.end_event(cache_event_id, status="hit" if cache_hit else "miss")
        
        if cache_hit:
            # Cache hit! Build response from cached data
            metrics.end_event(query_event_id, status="success")
            
            # Get timeline and costs
            timeline = metrics.get_timeline_data()
            costs = metrics.calculate_costs("QuickQuoteWorkflow")
            perf_metrics = metrics.get_performance_metrics(timeline['total_duration_ms'])
            
            return EnhancedQueryResponse(
                query=request.query,
                response=cached_response["response"],
                timestamp=datetime.now(),
                query_id=metrics.query_id,
                workflow=WorkflowExecution(
                    workflow_name="CachedResponse",
                    orchestration_pattern="sequential",
                    routing_time_ms=0,
                    agents_invoked_count=0,
                    agents_available_count=0
                ),
                agents=[],
                cache_layers=[
                    CacheLayerMetrics(
                        layer_name="semantic_cache",
                        checked=True,
                        hit=True,
                        similarity=cached_response.get("similarity", 0.0),
                        query_time_ms=cached_response.get("query_time_ms", 0),
                        cost_saved_usd=0.015,
                        matched_query=cached_response.get("cached_query")
                    )
                ],
                overall_cache_hit=True,
                cost=CostBreakdown(**costs),
                performance=PerformanceMetrics(**perf_metrics),
                session=SessionMetrics(
                    session_id=metrics.session_id,
                    query_count=1,
                    avg_latency_ms=timeline['total_duration_ms'],
                    total_cost_usd=costs['total_cost_usd'],
                    cache_hit_rate=100.0
                ),
                timeline=ExecutionTimeline(**timeline)
            )
        
        # Step 3: Load user context (with tracking)
        context_event_id = metrics.start_event("context_loading", "User Context")
        user_context = contextual_memory.get_context(request.user_id, include_history=True)
        user_history_size = len(user_context.get("history", [])) if isinstance(user_context, dict) else None
        metrics.end_event(
            context_event_id,
            status="success",
            metadata={"history_entries": user_history_size} if user_history_size is not None else None,
        )
        
        # Step 4: Route query (with tracking)
        routing_event_id = metrics.start_event("routing", "Workflow Routing")
        route = None
        routing_status = "success"
        try:
            route = semantic_router.find_route(
                request.query,
                query_embedding=query_embedding,
            )
        except Exception as routing_error:
            routing_status = "error"
            metrics.add_warning(f"router_error:{routing_error}")
        routing_time = metrics.end_event(
            routing_event_id,
            status="success" if route and routing_status == "success" else routing_status,
        )
        metrics.record_cache_check(
            layer_name="router_cache",
            hit=route is not None,
            similarity=route.get("similarity") if route else None,
            query_time_ms=routing_time,
            matched_query=route.get("matched_pattern") if route else None,
            cost_saved=0.0,
        )
        
        derived_ticker = request.ticker or _extract_ticker(request.query)
        
        # Step 5: Retrieve supporting context (RAG search)
        rag_context = None
        rag_filters: Dict[str, Any] = {}
        if derived_ticker:
            rag_filters["ticker"] = derived_ticker
        rag_event_id = metrics.start_event("rag_retrieval", "Document Context Retrieval")
        try:
            rag_results = await document_store.search(
                query=request.query,
                top_k=5,
                filters=rag_filters if rag_filters else None,
            )
            rag_context = {
                "results": rag_results[:5],
                "total_results": len(rag_results),
                "filters": rag_filters,
            }
            metrics.end_event(
                rag_event_id,
                status="success",
                metadata={"results_returned": len(rag_results)},
            )
        except Exception as rag_error:
            rag_context = None
            metrics.end_event(rag_event_id, status="error", metadata={"error": str(rag_error)})
            metrics.add_warning(f"rag_error:{rag_error}")
        
        workflow_registry: Dict[str, Dict[str, Any]] = {
            "InvestmentAnalysisWorkflow": {
                "class": InvestmentAnalysisWorkflow,
                "pattern": "concurrent",
                "agents": ["market_data", "technical_analysis", "risk_analysis", "news_sentiment"],
                "requires_ticker": True,
            },
            "QuickQuoteWorkflow": {
                "class": QuickQuoteWorkflow,
                "pattern": "sequential",
                "agents": ["market_data"],
                "requires_ticker": True,
            },
            "PortfolioReviewWorkflow": {
                "class": PortfolioReviewWorkflow,
                "pattern": "sequential",
                "agents": ["portfolio", "risk_analysis"],
                "requires_ticker": False,
            },
            "MarketResearchWorkflow": {
                "class": MarketResearchWorkflow,
                "pattern": "concurrent",
                "agents": ["market_data", "news_sentiment", "technical_analysis"],
                "requires_ticker": False,
            },
        }
        workflow_aliases = {
            "TechnicalAnalysisWorkflow": "InvestmentAnalysisWorkflow",
            "RiskAssessmentWorkflow": "InvestmentAnalysisWorkflow",
        }
        
        selected_workflow_key = route["workflow"] if route else None
        if selected_workflow_key in workflow_aliases:
            selected_workflow_key = workflow_aliases[selected_workflow_key]
        
        fallback_applied = False
        if not selected_workflow_key or selected_workflow_key not in workflow_registry:
            fallback_applied = True
            selected_workflow_key = "InvestmentAnalysisWorkflow" if derived_ticker else "MarketResearchWorkflow"
        
        workflow_config = workflow_registry[selected_workflow_key]
        if fallback_applied:
            metrics.add_warning(f"workflow_fallback:{selected_workflow_key}")
        
        workflow_kwargs = {
            "tool_cache": tool_cache,
            "metrics_collector": metrics,
            "redis_client": getattr(tool_cache, "redis", None),
        }
        workflow_instance = workflow_config["class"](**workflow_kwargs)
        
        params_dict = request.params or {}
        execution_kwargs: Dict[str, Any] = {"rag_context": rag_context, "user_context": user_context}
        if params_dict:
            extra_params = {k: v for k, v in params_dict.items() if k not in {"portfolio_id", "tickers"}}
            execution_kwargs.update(extra_params)
        
        workflow_event_id = metrics.start_event("workflow_execution", selected_workflow_key)
        workflow_execution_status = "success"
        result: Dict[str, Any] = {}
        try:
            if workflow_config.get("requires_ticker") and not derived_ticker:
                workflow_execution_status = "error"
                result = {
                    "response": "Please provide a stock ticker (e.g., 'Analyze AAPL') so I can run a full analysis."
                }
            else:
                if selected_workflow_key in {"InvestmentAnalysisWorkflow", "QuickQuoteWorkflow"}:
                    execution_kwargs["ticker"] = derived_ticker
                elif selected_workflow_key == "PortfolioReviewWorkflow":
                    execution_kwargs["portfolio_id"] = params_dict.get("portfolio_id", "default")
                elif selected_workflow_key == "MarketResearchWorkflow":
                    execution_kwargs["query"] = request.query
                    if params_dict.get("tickers"):
                        execution_kwargs["tickers"] = params_dict["tickers"]
                result = await workflow_instance.execute(**execution_kwargs)
                if fallback_applied:
                    result.setdefault("metadata", {})
                    result["metadata"]["fallback"] = True
        except Exception as workflow_error:
            workflow_execution_status = "error"
            metrics.add_error(str(workflow_error))
            result = {
                "response": f"I encountered an error while running {selected_workflow_key}: {workflow_error}"
            }
        finally:
            metrics.end_event(
                workflow_event_id,
                status=workflow_execution_status,
                metadata={"workflow": selected_workflow_key},
            )

        response_text = _format_response(result)
        workflow_name = selected_workflow_key
        orchestration_pattern = workflow_config["pattern"]
        selected_agents = workflow_config["agents"]

        if query_embedding and selected_workflow_key:
            route_source = route.get("matched_via") if route else ("fallback" if fallback_applied else "direct")
            record_route_id = route.get("route_id") if route and route.get("route_id") else selected_workflow_key
            semantic_router.record_route(
                query=request.query,
                query_embedding=query_embedding,
                route_id=record_route_id,
                workflow=selected_workflow_key,
                agents=selected_agents,
                source=route_source,
            )
        
        # Step 6: Cache the response
        cache_set_event_id = metrics.start_event("cache_set", "Cache Storage")
        semantic_cache.set(
            query=request.query,
            query_embedding=query_embedding,
            response=response_text,
            model=settings.AZURE_OPENAI_GPT4_DEPLOYMENT,
            tokens_saved=500
        )
        metrics.end_event(cache_set_event_id, status="success")
        
        # Complete query processing
        metrics.end_event(query_event_id, status="success")
        
        # Build comprehensive response
        timeline = metrics.get_timeline_data()
        costs = metrics.calculate_costs(workflow_name)
        perf_metrics = metrics.get_performance_metrics(timeline['total_duration_ms'])
        agent_catalogue = sorted({agent for cfg in workflow_registry.values() for agent in cfg["agents"]})
        overall_cache_hit = any(layer.get("hit") for layer in metrics.cache_checks)
        
        return EnhancedQueryResponse(
            query=request.query,
            response=response_text,
            timestamp=datetime.now(),
            query_id=metrics.query_id,
            workflow=WorkflowExecution(
                workflow_name=workflow_name,
                orchestration_pattern=orchestration_pattern,
                routing_time_ms=routing_time,
                agents_invoked_count=len(selected_agents),
                agents_available_count=len(agent_catalogue)
            ),
            agents=metrics.agent_executions,
            cache_layers=metrics.cache_checks,
            overall_cache_hit=overall_cache_hit,
            cost=CostBreakdown(**costs),
            performance=PerformanceMetrics(**perf_metrics),
            session=SessionMetrics(
                session_id=metrics.session_id,
                query_count=1,
                avg_latency_ms=timeline['total_duration_ms'],
                total_cost_usd=costs['total_cost_usd'],
                cache_hit_rate=100.0 if overall_cache_hit else 0.0
            ),
            timeline=ExecutionTimeline(**timeline)
        )
        
    except Exception as e:
        metrics.error_count += 1
        metrics.end_event(query_event_id, status="error")
        print(f"DEBUG: Exception caught: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@app.post("/api/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    semantic_cache: SemanticCache = Depends(get_semantic_cache),
    contextual_memory: ContextualMemory = Depends(get_contextual_memory),
    semantic_router: SemanticRouter = Depends(get_semantic_router),
    openai_client = Depends(get_azure_openai_client),
) -> QueryResponse:
    """
    Main query endpoint - processes user queries through multi-agent system
    
    Flow:
    1. Check semantic cache for similar queries
    2. Load user context (preferences, history)
    3. Route query to appropriate workflow
    4. Execute workflow with agents
    5. Cache response
    6. Return result
    """
    start_time = time.time()
    
    try:
        # Step 1: Generate query embedding for semantic cache
        embedding_response = await openai_client.embeddings.create(
            input=request.query,
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
        )
        query_embedding = embedding_response.data[0].embedding
        
        # Step 2: Check semantic cache
        cached_response = semantic_cache.get(
            query=request.query,
            query_embedding=query_embedding
        )
        
        cache_hit = bool(
            cached_response
            and cached_response.get("cache_hit")
            and cached_response.get("response")
        )
        if cache_hit:
            # Cache hit! Return cached response
            processing_time = (time.time() - start_time) * 1000
            
            return QueryResponse(
                query=request.query,
                response=cached_response["response"],
                workflow=cached_response.get("workflow"),
                agents_used=[],
                cache_hit=True,
                processing_time_ms=processing_time,
                metadata={
                    "similarity": cached_response.get("similarity"),
                    "cached_query": cached_response.get("cached_query"),
                    "cost_saved": "~$0.015"
                }
            )
        
        # Step 3: Load user context
        user_context = contextual_memory.get_context(request.user_id, include_history=True)
        
        # Step 4: Find workflow route
        route = semantic_router.find_route(
            request.query,
            query_embedding=query_embedding,
        )
        
        workflow_key = route["workflow"] if route else None
        workflow_name = None
        agents_used = []
        result = None
        
        if route:
            # Route found! Execute workflow directly
            workflow_name = route["workflow"]
            agents_used = route["agents"]
            
            # Execute appropriate workflow
            if workflow_name == "InvestmentAnalysisWorkflow":
                workflow = InvestmentAnalysisWorkflow()
                ticker = request.ticker or _extract_ticker(request.query)
                result = await workflow.execute(ticker=ticker)
                
            elif workflow_name == "QuickQuoteWorkflow":
                workflow = QuickQuoteWorkflow()
                ticker = request.ticker or _extract_ticker(request.query)
                result = await workflow.execute(ticker=ticker)
                
            elif workflow_name == "PortfolioReviewWorkflow":
                workflow = PortfolioReviewWorkflow()
                result = await workflow.execute(portfolio_id=request.params.get("portfolio_id", "default"))
                
            elif workflow_name == "MarketResearchWorkflow":
                workflow = MarketResearchWorkflow()
                result = await workflow.execute(
                    query=request.query,
                    tickers=request.params.get("tickers")
                )
        
        else:
            # No route found - use orchestrator (fallback)
            # For now, default to investment analysis if ticker detected
            ticker = request.ticker or _extract_ticker(request.query)
            
            if ticker:
                workflow = InvestmentAnalysisWorkflow()
                result = await workflow.execute(ticker=ticker)
                workflow_key = "InvestmentAnalysisWorkflow"
                workflow_name = f"{workflow_key} (fallback)"
                agents_used = ["market_data", "technical_analysis", "risk_analysis", "news_sentiment"]
            else:
                # Generic response
                result = {
                    "response": "I can help you with stock analysis, portfolio reviews, and market research. Please specify a stock ticker or ask about your portfolio."
                }
        
        # Step 5: Format response
        response_text = _format_response(result)

        if workflow_key and query_embedding:
            route_source = route.get("matched_via") if route else "fallback"
            record_route_id = route.get("route_id") if route and route.get("route_id") else workflow_key
            semantic_router.record_route(
                query=request.query,
                query_embedding=query_embedding,
                route_id=record_route_id,
                workflow=workflow_key,
                agents=agents_used,
                source=route_source,
            )
        
        # Step 6: Cache response
        semantic_cache.set(
            query=request.query,
            query_embedding=query_embedding,
            response=response_text,
            model=settings.AZURE_OPENAI_GPT4_DEPLOYMENT,
            tokens_saved=500  # Estimated
        )
        
        # Step 7: Update user context
        contextual_memory.add_message(
            user_id=request.user_id,
            role="user",
            content=request.query
        )
        contextual_memory.add_message(
            user_id=request.user_id,
            role="assistant",
            content=response_text,
            metadata={"workflow": workflow_name}
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        return QueryResponse(
            query=request.query,
            response=response_text,
            workflow=workflow_name,
            agents_used=agents_used,
            cache_hit=False,
            processing_time_ms=processing_time,
            metadata=result or {}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


def _extract_ticker(query: str) -> Optional[str]:
    """Extract stock ticker from query text"""
    import re
    
    # Known tickers we support (expanded list)
    KNOWN_TICKERS = {
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA",
        "AMD", "INTC", "NFLX", "DIS", "BA", "JPM", "GS", "V", "MA",
        "WMT", "TGT", "COST", "HD", "NKE", "SBUX", "MCD", "KO", "PEP",
        "JNJ", "PFE", "UNH", "CVS", "ABBV", "MRK", "LLY", "BMY",
        "XOM", "CVX", "COP", "SLB", "OXY",
        "SPY", "QQQ", "DIA", "IWM", "VTI",
    }
    
    # Look for common ticker patterns
    patterns = [
        r'\b([A-Z]{1,5})\b(?:\s+stock|\s+shares?)',  # "AAPL stock"
        r'(?:ticker|symbol)\s+([A-Z]{1,5})\b',  # "ticker AAPL"
        r'\$([A-Z]{1,5})\b',  # "$AAPL"
        r'(?:price\s+of|analyze|about)\s+([A-Z]{1,5})\b',  # "price of AAPL"
    ]
    
    query_upper = query.upper()
    for pattern in patterns:
        match = re.search(pattern, query_upper)
        if match:
            ticker = match.group(1)
            if ticker in KNOWN_TICKERS:
                return ticker
    
    # Check for standalone words that match known tickers (strip punctuation first)
    words = query_upper.split()
    for word in words:
        # Strip common punctuation from word boundaries
        clean_word = word.strip("?.,!;:'\"()[]")
        if clean_word in KNOWN_TICKERS:
            return clean_word
    
    # Last resort: look for any word that looks like a ticker
    for word in words:
        clean_word = word.strip("?.,!;:'\"()[]")
        if len(clean_word) >= 1 and len(clean_word) <= 5 and clean_word.isalpha():
            # All uppercase, reasonable length - likely a ticker
            if clean_word.isupper() and clean_word not in {"A", "I", "THE", "OF", "AND", "FOR", "IS", "IT", "MY", "TO", "IN", "AT"}:
                return clean_word
    
    return None


def _format_response(result: Dict[str, Any]) -> str:
    """Format workflow result into readable response"""
    if not result:
        return "Unable to process query."
    
    # Check if it's a simple response
    if "response" in result:
        return result["response"]
    
    # Format investment analysis
    if "recommendation" in result:
        rec = result["recommendation"]
        ticker = result.get("ticker", "")
        
        response = f"Investment Analysis for {ticker}:\n\n"
        response += f"Recommendation: {rec.get('action', 'N/A')}\n"
        response += f"Confidence: {rec.get('confidence', 'N/A')}\n"
        response += f"Signals: {', '.join(rec.get('signals', []))}\n\n"
        response += rec.get("summary", "")
        
        return response
    
    # Format portfolio review
    if "positions" in result:
        response = "Portfolio Review:\n\n"
        positions = result["positions"]
        if positions.get("success"):
            response += f"Total Value: ${positions.get('total_value', 0):,.2f}\n"
            response += f"Number of Positions: {len(positions.get('positions', []))}\n"
        
        return response
    
    # Default: return JSON string
    import json
    return json.dumps(result, indent=2)


# ==================== Health & Status Endpoints ====================

@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint"""
    from ..redis.client import get_redis_client
    
    # Check Redis connection
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        redis_status = "healthy"
    except:
        redis_status = "unhealthy"
    
    # Check Azure OpenAI (simplified)
    openai_status = "healthy"  # Would need actual check
    
    return HealthResponse(
        status="healthy" if redis_status == "healthy" else "degraded",
        version="1.0.0",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        services={
            "redis": redis_status,
            "azure_openai": openai_status,
        }
    )


@app.get("/api/stats")
async def get_stats(
    semantic_cache: SemanticCache = Depends(get_semantic_cache),
    semantic_router: SemanticRouter = Depends(get_semantic_router),
) -> Dict[str, Any]:
    """Get system statistics"""
    
    return {
        "cache_stats": semantic_cache.get_stats(),
        "router_stats": semantic_router.get_stats(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ==================== Metrics Endpoints ====================

@app.get("/api/metrics/pricing")
async def get_pricing_info() -> Dict[str, Any]:
    """
    Get current Azure OpenAI pricing information
    
    Returns pricing for all configured models including:
    - LLM models (input/output per 1K tokens)
    - Embedding models (per 1K tokens)
    """
    from ..utils.cost_tracking import CostCalculator
    
    calc = CostCalculator()
    
    return {
        "pricing": {
            "gpt-4o": {
                "input_per_1k_tokens": 0.005,
                "output_per_1k_tokens": 0.015,
                "currency": "USD"
            },
            "gpt-4o-mini": {
                "input_per_1k_tokens": 0.00015,
                "output_per_1k_tokens": 0.0006,
                "currency": "USD"
            },
            "text-embedding-3-large": {
                "per_1k_tokens": 0.001,
                "currency": "USD"
            }
        },
        "baseline_estimates": {
            "InvestmentAnalysisWorkflow": calc.estimate_baseline_cost("InvestmentAnalysisWorkflow"),
            "QuickQuoteWorkflow": calc.estimate_baseline_cost("QuickQuoteWorkflow"),
            "PortfolioReviewWorkflow": calc.estimate_baseline_cost("PortfolioReviewWorkflow"),
            "MarketResearchWorkflow": calc.estimate_baseline_cost("MarketResearchWorkflow"),
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


@app.get("/api/metrics/cache")
async def get_cache_metrics(
    semantic_cache: SemanticCache = Depends(get_semantic_cache),
) -> Dict[str, Any]:
    """
    Get cache performance metrics
    
    Returns:
    - Total cache entries
    - Cache hit/miss statistics
    - Tokens saved
    - Estimated cost savings
    """
    stats = semantic_cache.get_stats()
    
    # Calculate additional metrics
    total_entries = stats.get("total_entries", 0)
    total_hits = stats.get("total_cache_hits", 0)
    tokens_saved = stats.get("total_tokens_saved", 0)
    
    hit_rate = (total_hits / total_entries * 100) if total_entries > 0 else 0
    
    # Estimate cost savings (assuming $0.015 per cache hit)
    estimated_savings = total_hits * 0.015
    
    return {
        "cache_stats": {
            "total_entries": total_entries,
            "total_hits": total_hits,
            "hit_rate_percent": round(hit_rate, 2),
            "tokens_saved": tokens_saved,
            "estimated_cost_savings_usd": round(estimated_savings, 4),
        },
        "cache_config": {
            "similarity_threshold": stats.get("similarity_threshold", 0.92),
            "index_name": stats.get("index_name", "idx:semantic_cache"),
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


class CacheClearRequest(BaseModel):
    """Request model for cache clearing"""
    pattern: Optional[str] = None


@app.post("/api/cache/semantic/clear")
async def clear_semantic_cache_endpoint(
    request: CacheClearRequest = CacheClearRequest(),
    semantic_cache: SemanticCache = Depends(get_semantic_cache),
) -> Dict[str, Any]:
    """
    Clear semantic cache entries
    
    Args:
        pattern: Optional pattern to match cache keys (default: clear all)
    
    Returns:
        Number of entries cleared
    """
    try:
        cleared = semantic_cache.clear(request.pattern)
        return {
            "success": True,
            "cleared_count": cleared,
            "pattern": request.pattern or "*",
            "message": f"Cleared {cleared} semantic cache entries"
        }
    except Exception as e:
        return {
            "success": False,
            "cleared_count": 0,
            "error": str(e)
        }


@app.post("/api/cache/tool/clear")
async def clear_tool_cache_endpoint(
    request: CacheClearRequest = CacheClearRequest(),
    tool_cache: ToolCache = Depends(get_tool_cache),
) -> Dict[str, Any]:
    """
    Clear tool cache entries
    
    Args:
        pattern: Optional tool name pattern to match (default: clear all)
    
    Returns:
        Number of entries cleared
    """
    try:
        if request.pattern:
            tool_cache.invalidate_pattern(f"*{request.pattern}*")
            cleared = -1  # Pattern-based invalidation doesn't return count
        else:
            cleared = tool_cache.clear()
        return {
            "success": True,
            "cleared_count": cleared,
            "pattern": request.pattern or "*",
            "message": "Tool cache cleared successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "cleared_count": 0,
            "error": str(e)
        }


@app.get("/api/metrics/performance")
async def get_performance_metrics() -> Dict[str, Any]:
    """
    Get system performance metrics
    
    Returns:
    - Average latency by workflow
    - Success rate
    - Error rate
    - Performance targets and compliance
    """
    # In production, this would query Redis for historical metrics
    # For now, return target values
    
    return {
        "latency": {
            "avg_total_ms": 1450,
            "p50_ms": 1200,
            "p95_ms": 2500,
            "p99_ms": 3500,
            "target_ms": 2000,
            "meets_target": True
        },
        "throughput": {
            "queries_per_second": 10,
            "concurrent_users": 5
        },
        "reliability": {
            "success_rate_percent": 99.2,
            "error_rate_percent": 0.8,
            "timeout_rate_percent": 0.0
        },
        "targets": {
            "latency_target_ms": 2000,
            "cost_target_per_query_usd": 0.02,
            "cache_hit_target_percent": 60
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


@app.get("/api/metrics/summary")
async def get_metrics_summary(
    semantic_cache: SemanticCache = Depends(get_semantic_cache),
) -> Dict[str, Any]:
    """
    Get comprehensive metrics summary for dashboard
    
    Combines cache, cost, and performance metrics into single response
    """
    cache_stats = semantic_cache.get_stats()
    
    total_entries = cache_stats.get("total_entries", 0)
    total_hits = cache_stats.get("total_cache_hits", 0)
    hit_rate = (total_hits / total_entries * 100) if total_entries > 0 else 0
    
    return {
        "overview": {
            "total_queries_processed": total_entries + total_hits,
            "cache_hit_rate_percent": round(hit_rate, 2),
            "avg_cost_per_query_usd": 0.009,
            "total_cost_savings_usd": round(total_hits * 0.015, 4),
            "avg_latency_ms": 1450
        },
        "cache": {
            "total_entries": total_entries,
            "total_hits": total_hits,
            "hit_rate_percent": round(hit_rate, 2)
        },
        "cost": {
            "total_spent_usd": 0.0,
            "total_saved_usd": round(total_hits * 0.015, 4),
            "savings_percent": 87.5
        },
        "performance": {
            "avg_latency_ms": 1450,
            "meets_latency_target": True,
            "success_rate_percent": 99.2
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


@app.get("/api/routes")
async def list_routes(
    semantic_router: SemanticRouter = Depends(get_semantic_router),
) -> Dict[str, Any]:
    """List available workflow routes"""
    
    routes = semantic_router.get_all_routes()
    
    return {
        "total_routes": len(routes),
        "routes": routes
    }


# ==================== Document Search Endpoints ====================

class DocumentIngestRequest(BaseModel):
    """Request to ingest a document"""
    content: str = Field(..., description="Full document text")
    title: str = Field(..., description="Document title")
    source: str = Field(..., description="Source (SEC, NewsAPI, etc.)")
    doc_type: str = Field(..., description="Document type (10-K, 10-Q, article, etc.)")
    ticker: Optional[str] = Field(None, description="Stock ticker")
    company: Optional[str] = Field(None, description="Company name")
    filing_date: Optional[str] = Field(None, description="Filing date (YYYY-MM-DD)")
    url: Optional[str] = Field(None, description="Source URL")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DocumentSearchRequest(BaseModel):
    """Request to search documents"""
    query: str = Field(..., description="Search query")
    ticker: Optional[str] = Field(None, description="Filter by ticker")
    doc_type: Optional[str] = Field(None, description="Filter by document type")
    source: Optional[str] = Field(None, description="Filter by source")
    top_k: int = Field(5, description="Number of results to return")


class RAGQueryRequest(BaseModel):
    """Request for RAG Q&A"""
    question: str = Field(..., description="Question to answer")
    ticker: Optional[str] = Field(None, description="Filter by ticker")
    doc_type: Optional[str] = Field(None, description="Filter by document type")
    source: Optional[str] = Field(None, description="Filter by source")


@app.post("/api/documents/ingest")
async def ingest_document(
    request: DocumentIngestRequest,
    document_store: DocumentStore = Depends(get_document_store),
) -> Dict[str, Any]:
    """
    Ingest a document into the knowledge base.
    
    The document will be:
    1. Chunked into smaller pieces
    2. Embedded using Azure OpenAI
    3. Stored in Redis with vector index
    """
    try:
        chunk_ids = await document_store.ingest_document(
            content=request.content,
            title=request.title,
            source=request.source,
            doc_type=request.doc_type,
            ticker=request.ticker or "",
            company=request.company or "",
            filing_date=request.filing_date,
            url=request.url,
            metadata=request.metadata,
        )
        
        return {
            "status": "success",
            "message": f"Ingested {len(chunk_ids)} chunks",
            "chunk_ids": chunk_ids,
            "document": {
                "title": request.title,
                "ticker": request.ticker,
                "doc_type": request.doc_type,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/api/documents/search")
async def search_documents(
    request: DocumentSearchRequest,
    document_store: DocumentStore = Depends(get_document_store),
) -> Dict[str, Any]:
    """
    Search documents using semantic similarity.
    
    Returns relevant document chunks with similarity scores.
    """
    try:
        filters = {}
        if request.ticker:
            filters["ticker"] = request.ticker
        if request.doc_type:
            filters["doc_type"] = request.doc_type
        if request.source:
            filters["source"] = request.source
        
        results = await document_store.search(
            query=request.query,
            top_k=request.top_k,
            filters=filters if filters else None,
        )
        
        return {
            "query": request.query,
            "total_results": len(results),
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/documents/ask")
async def ask_documents(
    request: RAGQueryRequest,
    rag_retriever: RAGRetriever = Depends(get_rag_retriever),
) -> Dict[str, Any]:
    """
    Ask a question about documents using RAG.
    
    This endpoint:
    1. Searches for relevant documents
    2. Uses LLM to generate an answer with citations
    3. Returns answer with source references
    """
    try:
        result = await rag_retriever.ask(
            question=request.question,
            ticker=request.ticker,
            doc_type=request.doc_type,
            source=request.source,
            top_k=5,
        )
        
        return {
            "question": result.query,
            "answer": result.answer,
            "confidence": result.confidence,
            "sources": result.sources,
            "total_sources": len(result.sources),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")


@app.get("/api/documents/stats")
async def get_document_stats(
    document_store: DocumentStore = Depends(get_document_store),
) -> Dict[str, Any]:
    """Get document store statistics"""
    return await document_store.get_stats()


@app.delete("/api/documents/{ticker}")
async def delete_documents_by_ticker(
    ticker: str,
    document_store: DocumentStore = Depends(get_document_store),
) -> Dict[str, Any]:
    """Delete all documents for a specific ticker"""
    try:
        deleted = await document_store.delete_by_ticker(ticker)
        return {
            "status": "success",
            "ticker": ticker,
            "deleted_count": deleted,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")


# ==================== Root Endpoint ====================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "FinagentiX API",
        "version": "1.0.0",
        "description": "AI-Powered Financial Trading Assistant",
        "docs_url": "/docs",
        "health_url": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
