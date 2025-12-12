/**
 * TypeScript types matching Pydantic models from backend
 * Auto-generated from src/api/models.py
 */

// ==================== Tool Invocation ====================

export interface ToolInvocation {
  tool_name: string;
  parameters: Record<string, any>;
  duration_ms: number;
  cache_hit: boolean;
  cache_similarity: number | null;
  result_size_bytes: number;
  status: 'success' | 'error' | 'timeout';
  error_message?: string;
}

// ==================== Agent Execution ====================

export interface AgentExecution {
  agent_name: string;
  agent_id: string;
  agent_index: number;
  start_time: string;
  end_time: string;
  duration_ms: number;
  status: 'success' | 'error' | 'timeout';
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  model_used: string;
  temperature: number;
  max_tokens: number;
  cost_usd: number;
  tools_invoked: ToolInvocation[];
  response_preview?: string;
  error_message?: string;
}

// ==================== Cache Layer Metrics ====================

export interface CacheLayerMetrics {
  layer_name: string;
  checked: boolean;
  hit: boolean;
  similarity: number;
  query_time_ms: number;
  cost_saved_usd: number;
  matched_query?: string;
}

// ==================== Cost Breakdown ====================

export interface CostBreakdown {
  embedding_api_calls: number;
  embedding_total_tokens: number;
  embedding_cost_usd: number;
  llm_api_calls: number;
  llm_input_tokens: number;
  llm_output_tokens: number;
  llm_total_tokens: number;
  llm_cost_usd: number;
  total_cost_usd: number;
  baseline_cost_usd: number;
  cost_savings_usd: number;
  cost_savings_percent: number;
  cost_per_agent: Record<string, number>;
}

// ==================== Performance Metrics ====================

export interface PerformanceMetrics {
  queue_time_ms: number;
  processing_time_ms: number;
  total_time_ms: number;
  azure_openai_avg_latency_ms: number;
  azure_openai_max_latency_ms: number;
  redis_avg_latency_ms: number;
  redis_max_latency_ms: number;
  network_total_requests: number;
  error_count: number;
  warning_count: number;
  retry_count: number;
  meets_latency_target: boolean;
  meets_cost_target: boolean;
  quality_score: number;
}

// ==================== Workflow Execution ====================

export interface WorkflowExecution {
  workflow_name: string;
  orchestration_pattern: 'sequential' | 'concurrent' | 'handoff' | 'cache_hit';
  routing_time_ms: number;
  agents_invoked_count: number;
  agents_available_count: number;
}

// ==================== Session Metrics ====================

export interface SessionMetrics {
  session_id: string;
  query_count: number;
  avg_latency_ms: number;
  total_cost_usd: number;
  cache_hit_rate: number;
}

// ==================== Timeline Event ====================

export interface TimelineEvent {
  id: string;
  type: string;
  name: string;
  start_time_ms: number;
  end_time_ms: number;
  duration_ms: number;
  status: string;
  metadata: Record<string, any>;
}

// ==================== Execution Timeline ====================

export interface ExecutionTimeline {
  total_duration_ms: number;
  events: TimelineEvent[];
}

// ==================== Enhanced Query Response ====================

export interface EnhancedQueryResponse {
  query: string;
  response: string;
  timestamp: string;
  query_id: string;
  workflow: WorkflowExecution;
  agents: AgentExecution[];
  cache_layers: CacheLayerMetrics[];
  overall_cache_hit: boolean;
  cost: CostBreakdown;
  performance: PerformanceMetrics;
  session: SessionMetrics;
  timeline: ExecutionTimeline;
}

// ==================== Legacy Query Response ====================

export interface QueryResponse {
  query: string;
  response: string;
  workflow: string | null;
  agents_used: string[];
  cache_hit: boolean;
  processing_time_ms: number;
  metadata: Record<string, any>;
}

// ==================== Query Request ====================

export interface QueryRequest {
  query: string;
  user_id?: string;
  ticker?: string;
  params?: Record<string, any>;
}

// ==================== Metrics Endpoints ====================

export interface PricingInfo {
  pricing: Record<string, {
    input_per_1k_tokens?: number;
    output_per_1k_tokens?: number;
    per_1k_tokens?: number;
    currency: string;
  }>;
  baseline_estimates: Record<string, {
    embedding_cost: number;
    router_cost: number;
    agent_cost: number;
    total_cost: number;
  }>;
  timestamp: string;
}

export interface CacheMetrics {
  cache_stats: {
    total_entries: number;
    total_hits: number;
    hit_rate_percent: number;
    tokens_saved: number;
    estimated_cost_savings_usd: number;
  };
  cache_config: {
    similarity_threshold: number;
    index_name: string;
  };
  timestamp: string;
}

export interface PerformanceMetricsResponse {
  latency: {
    avg_total_ms: number;
    p50_ms: number;
    p95_ms: number;
    p99_ms: number;
    target_ms: number;
    meets_target: boolean;
  };
  throughput: {
    queries_per_second: number;
    concurrent_users: number;
  };
  reliability: {
    success_rate_percent: number;
    error_rate_percent: number;
    timeout_rate_percent: number;
  };
  targets: {
    latency_target_ms: number;
    cost_target_per_query_usd: number;
    cache_hit_target_percent: number;
  };
  timestamp: string;
}

export interface MetricsSummary {
  overview: {
    total_queries_processed: number;
    cache_hit_rate_percent: number;
    avg_cost_per_query_usd: number;
    total_cost_savings_usd: number;
    avg_latency_ms: number;
  };
  cache: {
    total_entries: number;
    total_hits: number;
    hit_rate_percent: number;
  };
  cost: {
    total_spent_usd: number;
    total_saved_usd: number;
    savings_percent: number;
  };
  performance: {
    avg_latency_ms: number;
    meets_latency_target: boolean;
    success_rate_percent: number;
  };
  timestamp: string;
}
