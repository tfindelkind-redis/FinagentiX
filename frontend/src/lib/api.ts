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

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
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
  },
  health: getHealth,
};

export default api;
