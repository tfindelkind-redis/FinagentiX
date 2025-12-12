"""
Enhanced API Models for Comprehensive Metrics Tracking

This module defines Pydantic models for detailed execution metrics,
cost tracking, and performance analysis of the multi-agent system.
"""

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class ToolInvocation(BaseModel):
    """Details of a single tool/plugin invocation"""
    tool_name: str = Field(..., description="Name of the tool function")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Input parameters")
    duration_ms: float = Field(..., description="Execution duration in milliseconds")
    cache_hit: bool = Field(..., description="Whether result was cached")
    cache_similarity: Optional[float] = Field(None, description="Cache match similarity score (0-1)")
    result_size_bytes: int = Field(..., description="Size of tool result in bytes")
    status: Literal["success", "error", "timeout"] = Field(..., description="Execution outcome")
    error_message: Optional[str] = Field(None, description="Error details if failed")


class AgentExecution(BaseModel):
    """Detailed execution metrics for a single agent"""
    agent_name: str = Field(..., description="Human-readable agent name")
    agent_id: str = Field(..., description="Technical agent identifier")
    agent_index: int = Field(..., description="Position in execution sequence")
    start_time: datetime = Field(..., description="Agent invocation start time")
    end_time: datetime = Field(..., description="Agent completion time")
    duration_ms: float = Field(..., description="Agent execution duration")
    status: Literal["success", "error", "timeout"] = Field(..., description="Execution outcome")
    error_message: Optional[str] = Field(None, description="Error details if failed")
    retry_count: int = Field(0, description="Number of retries attempted")
    
    # Token usage
    input_tokens: int = Field(..., description="Tokens in agent prompt")
    output_tokens: int = Field(..., description="Tokens in agent response")
    total_tokens: int = Field(..., description="Total tokens consumed")
    
    # Model configuration
    model_used: str = Field(..., description="LLM model deployment name")
    temperature: float = Field(..., description="LLM temperature setting")
    max_tokens: int = Field(..., description="Max tokens configured")
    
    # Tool usage
    tools_invoked: List[ToolInvocation] = Field(default_factory=list, description="Tools called by agent")
    
    # Cost
    cost_usd: float = Field(..., description="Cost of this agent execution in USD")
    
    # Response content
    response: Optional[str] = Field(None, description="Agent response text")


class CacheLayerMetrics(BaseModel):
    """Metrics for a single cache layer"""
    layer_name: Literal["semantic_cache", "router_cache", "tool_cache"] = Field(..., description="Cache layer identifier")
    checked: bool = Field(..., description="Whether this cache layer was queried")
    hit: bool = Field(..., description="Cache hit status")
    similarity: Optional[float] = Field(None, description="Similarity score to cached query (0-1)")
    query_time_ms: float = Field(..., description="Time to query this cache layer")
    matched_query: Optional[str] = Field(None, description="Original cached query text (if hit)")
    cost_saved_usd: float = Field(0.0, description="Cost saved by this cache hit")


class CostBreakdown(BaseModel):
    """Detailed cost analysis"""
    # API costs
    embedding_api_calls: int = Field(..., description="Number of embedding API calls")
    embedding_total_tokens: int = Field(..., description="Total tokens embedded")
    embedding_cost_usd: float = Field(..., description="Cost of embeddings")
    
    llm_api_calls: int = Field(..., description="Number of LLM API calls")
    llm_input_tokens: int = Field(..., description="Total input tokens across calls")
    llm_output_tokens: int = Field(..., description="Total output tokens across calls")
    llm_total_tokens: int = Field(..., description="Total LLM tokens")
    llm_cost_usd: float = Field(..., description="Cost of LLM calls")
    
    # Total
    total_cost_usd: float = Field(..., description="Total query cost")
    baseline_cost_usd: float = Field(..., description="Estimated cost without caching")
    cost_savings_usd: float = Field(..., description="Absolute cost savings")
    cost_savings_percent: float = Field(..., description="Percentage cost reduction")
    
    # Per-agent breakdown
    cost_per_agent: Dict[str, float] = Field(default_factory=dict, description="Cost breakdown by agent")


class PerformanceMetrics(BaseModel):
    """Performance and quality metrics"""
    queue_time_ms: float = Field(..., description="Time waiting in request queue")
    processing_time_ms: float = Field(..., description="Actual processing time")
    total_time_ms: float = Field(..., description="End-to-end total time")
    
    # Network
    azure_openai_avg_latency_ms: float = Field(..., description="Average Azure OpenAI API latency")
    redis_avg_latency_ms: float = Field(..., description="Average Redis operation latency")
    network_total_requests: int = Field(..., description="Total external API requests")
    
    # Quality
    confidence_score: Optional[float] = Field(None, description="Agent confidence in response (0-1)")
    data_freshness_seconds: Optional[int] = Field(None, description="Age of most recent data used")
    error_count: int = Field(0, description="Number of errors encountered")
    warning_count: int = Field(0, description="Number of warnings generated")
    retry_count: int = Field(0, description="Total retries across all operations")
    
    # Targets comparison
    meets_latency_target: bool = Field(..., description="Whether latency < 2s target")
    meets_cost_target: bool = Field(..., description="Whether cost < $0.01 target")


class WorkflowExecution(BaseModel):
    """Workflow orchestration details"""
    workflow_name: str = Field(..., description="Identified workflow type")
    orchestration_pattern: Literal["sequential", "concurrent", "handoff"] = Field(..., description="Execution pattern used")
    routing_time_ms: float = Field(..., description="Time spent determining workflow")
    agents_invoked_count: int = Field(..., description="Number of agents used")
    agents_available_count: int = Field(..., description="Total agents available")
    parallel_efficiency: Optional[float] = Field(None, description="Concurrent execution efficiency %")
    handoff_count: Optional[int] = Field(None, description="Number of agent handoffs")


class SessionMetrics(BaseModel):
    """Current session statistics"""
    session_id: str = Field(..., description="Session identifier")
    query_count: int = Field(..., description="Queries in this session")
    avg_latency_ms: float = Field(..., description="Average latency this session")
    total_cost_usd: float = Field(..., description="Total session cost")
    cache_hit_rate: float = Field(..., description="Session cache hit rate %")


class TimelineEvent(BaseModel):
    """Single event in execution timeline"""
    id: str = Field(..., description="Event identifier")
    type: str = Field(..., description="Event type")
    name: str = Field(..., description="Event name")
    start_time_ms: float = Field(..., description="Start time relative to query start (ms)")
    end_time_ms: float = Field(..., description="End time relative to query start (ms)")
    duration_ms: float = Field(..., description="Event duration")
    status: str = Field(..., description="Event status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event data")


class ExecutionTimeline(BaseModel):
    """Complete execution timeline for visualization"""
    total_duration_ms: float = Field(..., description="Total query execution time")
    events: List[TimelineEvent] = Field(default_factory=list, description="Timeline events")


class EnhancedQueryResponse(BaseModel):
    """Comprehensive query response with full execution metrics"""
    
    # Basic response
    query: str = Field(..., description="Original user query")
    response: str = Field(..., description="Generated response text")
    timestamp: datetime = Field(..., description="Query completion timestamp")
    query_id: str = Field(..., description="Unique query identifier")
    
    # Workflow execution
    workflow: WorkflowExecution = Field(..., description="Workflow orchestration details")
    
    # Agent execution details
    agents: List[AgentExecution] = Field(..., description="Per-agent execution metrics")
    
    # Caching metrics
    cache_layers: List[CacheLayerMetrics] = Field(..., description="Multi-layer cache performance")
    overall_cache_hit: bool = Field(..., description="Whether any cache layer hit")
    
    # Cost analysis
    cost: CostBreakdown = Field(..., description="Detailed cost breakdown")
    
    # Performance metrics
    performance: PerformanceMetrics = Field(..., description="Performance and quality metrics")
    
    # Session context
    session: SessionMetrics = Field(..., description="Current session statistics")
    
    # Execution timeline
    timeline: ExecutionTimeline = Field(..., description="Visual timeline data")
    
    # Historical comparison
    percentiles: Dict[str, float] = Field(
        default_factory=dict,
        description="P50, P95, P99 latency percentiles for comparison"
    )


# Legacy response model for backward compatibility
class QueryResponse(BaseModel):
    """Legacy query response model (backward compatibility)"""
    query: str
    response: str
    workflow: Optional[str] = None
    agents_used: List[str] = Field(default_factory=list)
    cache_hit: bool = False
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
