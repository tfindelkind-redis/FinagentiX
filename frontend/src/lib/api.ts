/**
 * API Client for FinagentiX Backend
 * Provides type-safe methods for all API endpoints
 */

import type {
  QueryRequest,
  EnhancedQueryResponse,
  QueryResponse,
  PricingInfo,
  CacheMetrics,
  PerformanceMetricsResponse,
  MetricsSummary,
  CacheOperationResult,
} from '@/types/api';
import { getAuthToken } from '@/contexts/AuthContext';

const runtimeBaseUrl =
  typeof window !== 'undefined' ? window.__ENV__?.PUBLIC_API_BASE_URL : undefined;

const API_BASE_URL = runtimeBaseUrl || import.meta.env.VITE_API_URL || 'http://localhost:8000';

class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

/**
 * Get authorization headers if token exists
 */
function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken();
  if (token) {
    return { 'Authorization': `Bearer ${token}` };
  }
  return {};
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new APIError(
      error.detail || `HTTP ${response.status}: ${response.statusText}`,
      response.status,
      error
    );
  }

  return response.json();
}

// ==================== Query Endpoints ====================

export async function executeQuery(request: QueryRequest): Promise<QueryResponse> {
  return fetchJSON<QueryResponse>('/api/query', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function executeQueryEnhanced(
  request: QueryRequest
): Promise<EnhancedQueryResponse> {
  return fetchJSON<EnhancedQueryResponse>('/api/query/enhanced', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// Streaming query types
export interface AgentSpec {
  id: string;
  name: string;
  icon: string;
}

export interface StreamEvent {
  type: 'status' | 'agents_init' | 'agent_start' | 'agent_done' | 'agent_data' | 'recommendation' | 'llm_start' | 'llm_chunk' | 'llm_done' | 'cache_hit' | 'error' | 'done';
  content?: string;
  message?: string;
  response?: string;
  ticker?: string | null;
  query_id?: string;
  agents?: AgentSpec[];
  agent_id?: string;
  index?: number;
  agents_used?: string[];
  processing_time_ms?: number;
  confidence_score?: number;
  recommendation?: string | null;
  market_data?: Record<string, unknown>;
  technical_analysis?: Record<string, unknown>;
  risk_analysis?: Record<string, unknown>;
  sentiment_analysis?: Record<string, unknown>;
  data?: Record<string, unknown>;
}

export type StreamCallback = (event: StreamEvent) => void;

export async function executeQueryStream(
  request: QueryRequest,
  onEvent: StreamCallback
): Promise<void> {
  const token = localStorage.getItem('auth_token');
  
  const response = await fetch(`${API_BASE_URL}/api/query/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    
    // Process complete SSE messages
    const lines = buffer.split('\n');
    buffer = lines.pop() || ''; // Keep incomplete line in buffer

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          onEvent(data as StreamEvent);
        } catch (e) {
          console.error('Failed to parse SSE data:', line);
        }
      }
    }
  }
}

// ==================== Metrics Endpoints ====================

export async function getPricingInfo(): Promise<PricingInfo> {
  return fetchJSON<PricingInfo>('/api/metrics/pricing');
}

export async function getCacheMetrics(): Promise<CacheMetrics> {
  return fetchJSON<CacheMetrics>('/api/metrics/cache');
}

export async function getPerformanceMetrics(): Promise<PerformanceMetricsResponse> {
  return fetchJSON<PerformanceMetricsResponse>('/api/metrics/performance');
}

export async function getMetricsSummary(): Promise<MetricsSummary> {
  return fetchJSON<MetricsSummary>('/api/metrics/summary');
}

// ==================== Cache Management ====================

export async function clearSemanticCache(pattern?: string): Promise<CacheOperationResult> {
  const body = pattern ? { pattern } : {};
  return fetchJSON<CacheOperationResult>('/api/cache/semantic/clear', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function clearToolCache(toolName?: string): Promise<CacheOperationResult> {
  const body = toolName ? { tool_name: toolName } : {};
  return fetchJSON<CacheOperationResult>('/api/cache/tool/clear', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function clearRouterCache(pattern?: string): Promise<CacheOperationResult> {
  const body = pattern ? { pattern } : {};
  return fetchJSON<CacheOperationResult>('/api/cache/router/clear', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

// ==================== Health Endpoint ====================

export async function getHealth(): Promise<{
  status: string;
  version: string;
  timestamp: string;
  services: Record<string, string>;
}> {
  return fetchJSON('/health');
}

// Export API client instance
export const api = {
  query: {
    execute: executeQuery,
    executeEnhanced: executeQueryEnhanced,
  },
  metrics: {
    pricing: getPricingInfo,
    cache: getCacheMetrics,
    performance: getPerformanceMetrics,
    summary: getMetricsSummary,
  },
  cache: {
    clearSemantic: clearSemanticCache,
    clearTool: clearToolCache,
    clearRouter: clearRouterCache,
  },
  health: getHealth,
};

export default api;
