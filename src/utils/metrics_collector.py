"""
Metrics Collection System for Execution Tracking

This module provides comprehensive metrics collection during query execution,
tracking timing, token usage, costs, and execution flow for visualization
and analysis.
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.utils.cost_tracking import get_cost_calculator


class MetricsCollector:
    """Collects detailed execution metrics during query processing"""
    
    def __init__(self, query: str, session_id: str, user_id: str = "default"):
        """
        Initialize metrics collector
        
        Args:
            query: User query being processed
            session_id: Session identifier
            user_id: User identifier
        """
        self.query = query
        self.session_id = session_id
        self.user_id = user_id
        self.query_id = str(uuid.uuid4())
        
        self.start_time = time.time()
        self.start_timestamp = datetime.now()
        
        self.events: List[Dict[str, Any]] = []
        self.agent_executions: List[Dict[str, Any]] = []
        self.cache_checks: List[Dict[str, Any]] = []
        self.tool_invocations: List[Dict[str, Any]] = []
        
        # Cost tracking
        self.cost_calculator = get_cost_calculator()
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.embedding_tokens = 0
        self.llm_api_calls = 0
        self.embedding_api_calls = 0
        
        # Performance tracking
        self.error_count = 0
        self.warning_count = 0
        self.retry_count = 0
        
        # Network tracking
        self.network_requests = 0
        self.azure_openai_latencies: List[float] = []
        self.redis_latencies: List[float] = []
    
    def start_event(
        self,
        event_type: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start tracking an event
        
        Args:
            event_type: Type of event (cache_check, router, agent, tool, synthesis)
            name: Human-readable event name
            metadata: Additional event data
            
        Returns:
            Event ID for later reference
        """
        event_id = f"{event_type}_{len(self.events)}"
        event = {
            "id": event_id,
            "type": event_type,
            "name": name,
            "start_time": time.time(),
            "start_timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.events.append(event)
        return event_id
    
    def end_event(
        self,
        event_id: str,
        status: str = "success",
        result: Any = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Complete an event with timing and result
        
        Args:
            event_id: Event ID from start_event
            status: Event outcome (success, error, timeout, miss)
            result: Event result data
            metadata: Additional metadata to add
            
        Returns:
            Duration of the event in milliseconds
        """
        event = next((e for e in self.events if e["id"] == event_id), None)
        if event:
            event["end_time"] = time.time()
            event["end_timestamp"] = datetime.now().isoformat()
            event["duration_ms"] = (event["end_time"] - event["start_time"]) * 1000
            event["status"] = status
            
            if metadata:
                event["metadata"].update(metadata)
            
            # Count tokens if result is text
            if isinstance(result, str):
                tokens = self.cost_calculator.count_tokens(result)
                event["metadata"]["output_tokens"] = tokens
            
            return event["duration_ms"]
        
        return 0.0  # Return 0 if event not found
    
    def record_agent_execution(
        self,
        agent_name: str,
        agent_id: str,
        duration_ms: float,
        input_tokens: int,
        output_tokens: int,
        model: str,
        cost: float,
        status: str = "success",
        response: Optional[str] = None,
        error: Optional[str] = None,
        tools_used: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Record complete agent execution metrics
        
        Args:
            agent_name: Human-readable agent name
            agent_id: Technical agent identifier
            duration_ms: Execution duration
            input_tokens: Input token count
            output_tokens: Output token count
            model: Model used
            cost: Execution cost in USD
            status: Execution status
            response: Agent response text
            error: Error message if failed
            tools_used: List of tools invoked
        """
        self.agent_executions.append({
            "agent_name": agent_name,
            "agent_id": agent_id,
            "agent_index": len(self.agent_executions),
            "duration_ms": duration_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "model_used": model,
            "cost_usd": cost,
            "status": status,
            "response": response,
            "error_message": error,
            "tools_invoked": tools_used or [],
            "timestamp": datetime.now().isoformat()
        })
        
        # Update totals
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.llm_api_calls += 1
        
        if status == "error":
            self.error_count += 1
    
    def record_cache_check(
        self,
        layer_name: str,
        hit: bool,
        similarity: Optional[float] = None,
        query_time_ms: float = 0,
        matched_query: Optional[str] = None,
        cost_saved: float = 0
    ):
        """
        Record cache layer check
        
        Args:
            layer_name: Cache layer identifier
            hit: Whether cache hit
            similarity: Similarity score (0-1)
            query_time_ms: Time to query cache
            matched_query: Original cached query
            cost_saved: Cost saved by this hit
        """
        self.cache_checks.append({
            "layer_name": layer_name,
            "checked": True,
            "hit": hit,
            "similarity": similarity,
            "query_time_ms": query_time_ms,
            "matched_query": matched_query,
            "cost_saved_usd": cost_saved
        })
    
    def record_tool_invocation(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        duration_ms: float,
        cache_hit: bool,
        cache_similarity: Optional[float] = None,
        result_size: int = 0,
        status: str = "success",
        error: Optional[str] = None
    ):
        """
        Record tool/plugin invocation
        
        Args:
            tool_name: Tool function name
            parameters: Tool input parameters
            duration_ms: Execution duration
            cache_hit: Whether result was cached
            cache_similarity: Cache match score
            result_size: Result size in bytes
            status: Execution status
            error: Error message if failed
        """
        self.tool_invocations.append({
            "tool_name": tool_name,
            "parameters": parameters,
            "duration_ms": duration_ms,
            "cache_hit": cache_hit,
            "cache_similarity": cache_similarity,
            "result_size_bytes": result_size,
            "status": status,
            "error_message": error
        })
    
    def record_embedding(self, tokens: int):
        """
        Record embedding API call
        
        Args:
            tokens: Number of tokens embedded
        """
        self.embedding_tokens += tokens
        self.embedding_api_calls += 1
    
    def record_network_request(self, service: str, latency_ms: float):
        """
        Record external network request
        
        Args:
            service: Service name (azure_openai, redis, etc.)
            latency_ms: Request latency
        """
        self.network_requests += 1
        
        if service == "azure_openai":
            self.azure_openai_latencies.append(latency_ms)
        elif service == "redis":
            self.redis_latencies.append(latency_ms)
    
    def add_error(self, message: str):
        """Record error"""
        self.error_count += 1
    
    def add_warning(self, message: str):
        """Record warning"""
        self.warning_count += 1
    
    def add_retry(self):
        """Record retry attempt"""
        self.retry_count += 1
    
    def get_agent_count(self) -> int:
        """
        Get number of agents executed
        
        Returns:
            Count of agent executions
        """
        return len(self.agent_executions)
    
    def get_timeline_data(self) -> Dict[str, Any]:
        """
        Generate timeline data for frontend visualization
        
        Returns:
            Timeline data with events
        """
        if not self.events:
            return {"total_duration_ms": 0, "events": []}
        
        total_duration = (time.time() - self.start_time) * 1000
        
        timeline_events = []
        for event in self.events:
            if "end_time" in event:
                timeline_events.append({
                    "id": event["id"],
                    "type": event["type"],
                    "name": event["name"],
                    "start_time_ms": (event["start_time"] - self.start_time) * 1000,
                    "end_time_ms": (event["end_time"] - self.start_time) * 1000,
                    "duration_ms": event["duration_ms"],
                    "status": event.get("status", "success"),
                    "metadata": event.get("metadata", {})
                })
        
        return {
            "total_duration_ms": total_duration,
            "events": timeline_events
        }
    
    def calculate_costs(
        self,
        workflow_name: str,
        semantic_cache_hit: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive cost breakdown
        
        Args:
            workflow_name: Workflow being executed
            semantic_cache_hit: Whether semantic cache hit
            
        Returns:
            Cost breakdown dictionary
        """
        # Calculate actual costs
        embedding_cost = self.cost_calculator.calculate_embedding_cost(self.embedding_tokens)
        llm_cost = self.cost_calculator.calculate_llm_cost(
            self.total_input_tokens,
            self.total_output_tokens
        )
        total_cost = embedding_cost + llm_cost
        
        # Estimate baseline (without caching)
        baseline = self.cost_calculator.estimate_baseline_cost(workflow_name)
        baseline_cost = baseline["total_cost"]
        
        # Calculate savings
        savings = baseline_cost - total_cost
        savings_percent = (savings / baseline_cost * 100) if baseline_cost > 0 else 0
        
        # Per-agent costs
        cost_per_agent = {
            agent["agent_name"]: agent["cost_usd"]
            for agent in self.agent_executions
        }
        
        return {
            "embedding_api_calls": self.embedding_api_calls,
            "embedding_total_tokens": self.embedding_tokens,
            "embedding_cost_usd": embedding_cost,
            "llm_api_calls": self.llm_api_calls,
            "llm_input_tokens": self.total_input_tokens,
            "llm_output_tokens": self.total_output_tokens,
            "llm_total_tokens": self.total_input_tokens + self.total_output_tokens,
            "llm_cost_usd": llm_cost,
            "total_cost_usd": total_cost,
            "baseline_cost_usd": baseline_cost,
            "cost_savings_usd": savings,
            "cost_savings_percent": round(savings_percent, 1),
            "cost_per_agent": cost_per_agent
        }
    
    def get_performance_metrics(self, total_time_ms: float) -> Dict[str, Any]:
        """
        Get performance metrics
        
        Args:
            total_time_ms: Total query execution time
            
        Returns:
            Performance metrics dictionary
        """
        # Calculate averages
        avg_openai_latency = (
            sum(self.azure_openai_latencies) / len(self.azure_openai_latencies)
            if self.azure_openai_latencies else 0
        )
        avg_redis_latency = (
            sum(self.redis_latencies) / len(self.redis_latencies)
            if self.redis_latencies else 0
        )
        
        # Queue time is first event start time (if any)
        queue_time = 0
        if self.events:
            first_event = min(self.events, key=lambda e: e["start_time"])
            queue_time = (first_event["start_time"] - self.start_time) * 1000
        
        processing_time = total_time_ms - queue_time
        
        return {
            "queue_time_ms": round(queue_time, 2),
            "processing_time_ms": round(processing_time, 2),
            "total_time_ms": round(total_time_ms, 2),
            "azure_openai_avg_latency_ms": round(avg_openai_latency, 2),
            "redis_avg_latency_ms": round(avg_redis_latency, 2),
            "network_total_requests": self.network_requests,
            "confidence_score": None,  # To be filled by agent logic
            "data_freshness_seconds": None,  # To be filled by data sources
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "retry_count": self.retry_count,
            "meets_latency_target": total_time_ms < 2000,  # < 2s
            "meets_cost_target": True  # Will be set based on actual cost
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get complete metrics summary
        
        Returns:
            Complete metrics data
        """
        total_duration = (time.time() - self.start_time) * 1000
        
        return {
            "query_id": self.query_id,
            "query": self.query,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "start_timestamp": self.start_timestamp.isoformat(),
            "end_timestamp": datetime.now().isoformat(),
            "duration_ms": total_duration,
            "events": self.events,
            "agent_executions": self.agent_executions,
            "cache_checks": self.cache_checks,
            "tool_invocations": self.tool_invocations,
            "timeline": self.get_timeline_data()
        }
