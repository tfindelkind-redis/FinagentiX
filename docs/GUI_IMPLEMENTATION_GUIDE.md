# GUI Implementation Guide - Technical Details

**Companion Document to**: GUI_DESIGN_SPECIFICATION.md  
**Purpose**: Detailed implementation guidance and code examples

---

## 🎨 Detailed Component Specifications

### 1. Execution Timeline Visualization

#### Data Structure
```typescript
interface TimelineEvent {
  id: string;
  type: 'cache_check' | 'router' | 'agent' | 'tool' | 'synthesis';
  name: string;
  startTime: number;  // milliseconds from query start
  endTime: number;
  duration: number;
  status: 'success' | 'error' | 'running';
  metadata?: {
    tokens?: { input: number; output: number };
    cost?: number;
    cacheHit?: boolean;
  };
}

interface TimelineData {
  totalDuration: number;
  events: TimelineEvent[];
  concurrentGroups?: TimelineEvent[][];  // For concurrent execution
}
```

#### Recharts Implementation Example
```tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';

const ExecutionTimeline: React.FC<{ data: TimelineData }> = ({ data }) => {
  const colorMap = {
    cache_check: '#3b82f6',
    router: '#8b5cf6',
    agent: '#10b981',
    tool: '#f59e0b',
    synthesis: '#ec4899'
  };

  // Transform data for horizontal bars
  const chartData = data.events.map(event => ({
    name: event.name,
    start: event.startTime,
    duration: event.duration,
    type: event.type,
    status: event.status
  }));

  return (
    <div className="timeline-container">
      <BarChart
        width={800}
        height={400}
        data={chartData}
        layout="vertical"
        margin={{ left: 120 }}
      >
        <XAxis type="number" domain={[0, data.totalDuration]} unit="ms" />
        <YAxis type="category" dataKey="name" width={100} />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="duration" stackId="a">
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={colorMap[entry.type]} />
          ))}
        </Bar>
      </BarChart>
    </div>
  );
};

const CustomTooltip: React.FC<any> = ({ active, payload }) => {
  if (!active || !payload?.[0]) return null;
  
  const data = payload[0].payload;
  return (
    <div className="bg-white p-3 border rounded shadow-lg">
      <p className="font-semibold">{data.name}</p>
      <p className="text-sm">Duration: {data.duration}ms</p>
      <p className="text-sm">Start: {data.start}ms</p>
      <p className="text-sm">Status: {data.status}</p>
    </div>
  );
};
```

### 2. Cost Comparison Visualization

#### Stacked Bar Chart for Cost Breakdown
```tsx
import { BarChart, Bar, XAxis, YAxis, Legend, Tooltip } from 'recharts';

const CostComparison: React.FC<{ cost: CostBreakdown }> = ({ cost }) => {
  const data = [
    {
      scenario: 'With Cache',
      embedding: cost.embedding_cost_usd,
      llm: cost.llm_cost_usd,
      total: cost.total_cost_usd
    },
    {
      scenario: 'Without Cache',
      embedding: cost.embedding_cost_usd * 1.5,  // Estimated
      llm: cost.baseline_cost_usd - (cost.embedding_cost_usd * 1.5),
      total: cost.baseline_cost_usd
    }
  ];

  return (
    <div className="cost-comparison">
      <BarChart width={600} height={300} data={data}>
        <XAxis dataKey="scenario" />
        <YAxis />
        <Tooltip formatter={(value) => `$${value.toFixed(4)}`} />
        <Legend />
        <Bar dataKey="embedding" stackId="a" fill="#3b82f6" name="Embeddings" />
        <Bar dataKey="llm" stackId="a" fill="#10b981" name="LLM Calls" />
      </BarChart>
      
      <div className="savings-indicator mt-4">
        <p className="text-2xl font-bold text-green-600">
          ↓ {cost.cost_savings_percent}% Savings
        </p>
        <p className="text-gray-600">
          ${cost.cost_savings_usd.toFixed(4)} saved
        </p>
      </div>
    </div>
  );
};
```

### 3. Agent Execution Table with Expandable Rows

```tsx
import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface AgentTableProps {
  agents: AgentExecution[];
}

const AgentTable: React.FC<AgentTableProps> = ({ agents }) => {
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  const toggleRow = (index: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedRows(newExpanded);
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="w-8"></th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Agent
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Duration
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Tokens
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Cost
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {agents.map((agent, index) => (
            <>
              <tr key={index} className="hover:bg-gray-50 cursor-pointer">
                <td className="px-2" onClick={() => toggleRow(index)}>
                  {agent.tools_invoked.length > 0 && (
                    expandedRows.has(index) ? <ChevronDown size={16} /> : <ChevronRight size={16} />
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {agent.agent_name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <StatusBadge status={agent.status} />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {agent.duration_ms.toFixed(0)}ms
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {agent.input_tokens} / {agent.output_tokens}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  ${agent.cost_usd.toFixed(4)}
                </td>
              </tr>
              {expandedRows.has(index) && agent.tools_invoked.length > 0 && (
                <tr>
                  <td colSpan={6} className="bg-gray-50 px-12 py-4">
                    <div className="text-sm">
                      <h4 className="font-semibold mb-2">Tool Invocations:</h4>
                      <div className="space-y-2">
                        {agent.tools_invoked.map((tool, toolIndex) => (
                          <div key={toolIndex} className="flex items-center justify-between border-l-2 border-blue-500 pl-3">
                            <span className="font-mono text-xs">{tool.tool_name}</span>
                            <span className="text-xs text-gray-600">{tool.duration_ms.toFixed(0)}ms</span>
                            <span className="text-xs">
                              {tool.cache_hit ? (
                                <span className="text-green-600">✓ Cached</span>
                              ) : (
                                <span className="text-gray-500">Executed</span>
                              )}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const styles = {
    success: 'bg-green-100 text-green-800',
    error: 'bg-red-100 text-red-800',
    timeout: 'bg-yellow-100 text-yellow-800'
  };

  return (
    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${styles[status]}`}>
      {status === 'success' ? '✓' : status === 'error' ? '✗' : '⏱'}
    </span>
  );
};
```

### 4. Cache Performance Heatmap

```tsx
import { useMemo } from 'react';

interface CacheHeatmapProps {
  cacheData: {
    layer_name: string;
    hit: boolean;
    similarity: number | null;
    query_time_ms: number;
  }[];
}

const CachePerformanceHeatmap: React.FC<CacheHeatmapProps> = ({ cacheData }) => {
  const getSimilarityColor = (similarity: number | null, hit: boolean) => {
    if (!hit) return 'bg-red-100';
    if (similarity === null) return 'bg-gray-100';
    if (similarity >= 0.95) return 'bg-green-500';
    if (similarity >= 0.90) return 'bg-green-400';
    if (similarity >= 0.85) return 'bg-green-300';
    if (similarity >= 0.80) return 'bg-yellow-300';
    return 'bg-orange-300';
  };

  return (
    <div className="cache-heatmap">
      <div className="grid grid-cols-3 gap-4">
        {cacheData.map((layer, index) => (
          <div
            key={index}
            className={`p-4 rounded-lg ${getSimilarityColor(layer.similarity, layer.hit)} transition-colors`}
          >
            <h4 className="font-semibold text-sm mb-2">
              {layer.layer_name.replace('_', ' ').toUpperCase()}
            </h4>
            <div className="space-y-1 text-xs">
              <p>Status: {layer.hit ? '✓ HIT' : '✗ MISS'}</p>
              {layer.similarity && (
                <p>Similarity: {(layer.similarity * 100).toFixed(1)}%</p>
              )}
              <p>Query Time: {layer.query_time_ms.toFixed(1)}ms</p>
            </div>
          </div>
        ))}
      </div>
      
      <div className="mt-4 text-xs text-gray-600">
        <p className="font-semibold mb-1">Legend:</p>
        <div className="flex gap-2 flex-wrap">
          <span className="px-2 py-1 bg-green-500 rounded">≥95%</span>
          <span className="px-2 py-1 bg-green-400 rounded">90-95%</span>
          <span className="px-2 py-1 bg-green-300 rounded">85-90%</span>
          <span className="px-2 py-1 bg-yellow-300 rounded">80-85%</span>
          <span className="px-2 py-1 bg-orange-300 rounded">&lt;80%</span>
          <span className="px-2 py-1 bg-red-100 rounded">Miss</span>
        </div>
      </div>
    </div>
  );
};
```

---

## 🔌 Backend Implementation Examples

### 1. Enhanced Metrics Collection in Orchestrator

```python
# src/agents/orchestrator_agent.py

import time
import tiktoken
from typing import Dict, Any, List
from datetime import datetime

class MetricsCollector:
    """Collects detailed execution metrics during query processing"""
    
    def __init__(self):
        self.start_time = time.time()
        self.events: List[Dict[str, Any]] = []
        self.token_counter = tiktoken.encoding_for_model("gpt-4o")
        
    def start_event(self, event_type: str, name: str, metadata: Dict = None) -> str:
        """Start tracking an event"""
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
    
    def end_event(self, event_id: str, status: str = "success", result: Any = None):
        """Complete an event with timing and result"""
        event = next((e for e in self.events if e["id"] == event_id), None)
        if event:
            event["end_time"] = time.time()
            event["end_timestamp"] = datetime.now().isoformat()
            event["duration_ms"] = (event["end_time"] - event["start_time"]) * 1000
            event["status"] = status
            
            # Count tokens if result is text
            if isinstance(result, str):
                event["metadata"]["output_tokens"] = len(self.token_counter.encode(result))
    
    def get_timeline_data(self) -> Dict[str, Any]:
        """Generate timeline data for frontend"""
        if not self.events:
            return {"total_duration": 0, "events": []}
        
        total_duration = (time.time() - self.start_time) * 1000
        
        timeline_events = []
        for event in self.events:
            if "end_time" in event:
                timeline_events.append({
                    "id": event["id"],
                    "type": event["type"],
                    "name": event["name"],
                    "startTime": (event["start_time"] - self.start_time) * 1000,
                    "endTime": (event["end_time"] - self.start_time) * 1000,
                    "duration": event["duration_ms"],
                    "status": event.get("status", "success"),
                    "metadata": event.get("metadata", {})
                })
        
        return {
            "total_duration": total_duration,
            "events": timeline_events
        }

# Usage in orchestrator
async def execute_query_with_metrics(query: str) -> EnhancedQueryResponse:
    metrics = MetricsCollector()
    
    # Track semantic cache check
    cache_event = metrics.start_event("cache_check", "Semantic Cache Lookup")
    cached = await semantic_cache.get(query)
    metrics.end_event(cache_event, "success" if cached else "miss")
    
    if cached:
        # Return cached response with metrics
        return EnhancedQueryResponse(
            query=query,
            response=cached["response"],
            # ... populate from cached data
        )
    
    # Track router
    router_event = metrics.start_event("router", "Workflow Router")
    route = await semantic_router.find_route(query)
    metrics.end_event(router_event, "success", result=str(route))
    
    # Track each agent
    agent_executions = []
    for agent in route["agents"]:
        agent_event = metrics.start_event("agent", agent.name)
        
        # Execute agent with token tracking
        result = await execute_agent_with_tracking(agent, query)
        
        agent_executions.append(result)
        metrics.end_event(agent_event, result.status, result.response)
    
    # Calculate costs
    cost_breakdown = calculate_total_cost(agent_executions)
    
    # Build response
    return EnhancedQueryResponse(
        query=query,
        response=synthesize_response(agent_executions),
        workflow=WorkflowExecution(...),
        agents=agent_executions,
        cache_layers=get_cache_metrics(),
        cost=cost_breakdown,
        performance=PerformanceMetrics(
            total_time_ms=metrics.get_timeline_data()["total_duration"],
            # ... other metrics
        ),
        timeline=metrics.get_timeline_data()
    )
```

### 2. Token Counting and Cost Calculation

```python
# src/utils/cost_tracking.py

import tiktoken
from typing import Dict, Any, List
from dataclasses import dataclass

# Azure OpenAI Pricing (as of January 2025)
PRICING = {
    "gpt-4o": {
        "input_per_1k": 0.0050,
        "output_per_1k": 0.0150
    },
    "gpt-4o-mini": {
        "input_per_1k": 0.00015,
        "output_per_1k": 0.0006
    },
    "text-embedding-3-large": {
        "per_1k": 0.0010
    }
}

@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    
class CostCalculator:
    """Accurate cost calculation with token counting"""
    
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self.encoding = tiktoken.encoding_for_model(model)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))
    
    def count_messages(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in chat messages format"""
        tokens = 0
        for message in messages:
            tokens += 3  # Message formatting overhead
            tokens += self.count_tokens(message.get("content", ""))
            tokens += self.count_tokens(message.get("role", ""))
            if "name" in message:
                tokens += self.count_tokens(message["name"])
        tokens += 3  # Assistant reply priming
        return tokens
    
    def calculate_llm_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for LLM API call"""
        pricing = PRICING.get(self.model, PRICING["gpt-4o"])
        
        input_cost = (input_tokens / 1000) * pricing["input_per_1k"]
        output_cost = (output_tokens / 1000) * pricing["output_per_1k"]
        
        return round(input_cost + output_cost, 6)
    
    @staticmethod
    def calculate_embedding_cost(tokens: int) -> float:
        """Calculate cost for embedding API call"""
        pricing = PRICING["text-embedding-3-large"]
        return round((tokens / 1000) * pricing["per_1k"], 6)
    
    def estimate_baseline_cost(self, workflow_name: str) -> Dict[str, float]:
        """Estimate cost without caching based on workflow type"""
        WORKFLOW_ESTIMATES = {
            "InvestmentAnalysisWorkflow": {
                "embedding_tokens": 500,
                "router_input": 300,
                "router_output": 50,
                "agents": [
                    {"input": 800, "output": 1200},  # Market Data
                    {"input": 700, "output": 1000},  # Risk Analysis
                    {"input": 600, "output": 900},   # News Sentiment
                    {"input": 900, "output": 1300},  # Synthesis
                ]
            },
            "QuickQuoteWorkflow": {
                "embedding_tokens": 300,
                "router_input": 200,
                "router_output": 30,
                "agents": [
                    {"input": 400, "output": 600},   # Market Data
                    {"input": 300, "output": 400},   # Quick Analysis
                ]
            }
        }
        
        estimates = WORKFLOW_ESTIMATES.get(workflow_name, WORKFLOW_ESTIMATES["InvestmentAnalysisWorkflow"])
        
        # Calculate costs
        embedding_cost = self.calculate_embedding_cost(estimates["embedding_tokens"])
        router_cost = self.calculate_llm_cost(
            estimates["router_input"],
            estimates["router_output"]
        )
        
        agent_costs = []
        for agent in estimates["agents"]:
            agent_costs.append(
                self.calculate_llm_cost(agent["input"], agent["output"])
            )
        
        total_agent_cost = sum(agent_costs)
        total_cost = embedding_cost + router_cost + total_agent_cost
        
        return {
            "embedding_cost": embedding_cost,
            "router_cost": router_cost,
            "agent_cost": total_agent_cost,
            "total_cost": total_cost,
            "per_agent_costs": agent_costs
        }

# Usage
cost_calc = CostCalculator(model="gpt-4o")

# Count tokens from actual API call
input_tokens = cost_calc.count_messages(chat_history)
output_tokens = cost_calc.count_tokens(response_text)

# Calculate actual cost
actual_cost = cost_calc.calculate_llm_cost(input_tokens, output_tokens)

# Calculate savings
baseline = cost_calc.estimate_baseline_cost("InvestmentAnalysisWorkflow")
savings = baseline["total_cost"] - actual_cost
savings_percent = (savings / baseline["total_cost"]) * 100
```

### 3. Metrics Storage in Redis

```python
# src/redis/metrics_storage.py

import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
import redis

class MetricsStorage:
    """Store and retrieve execution metrics in Redis"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.prefix = "metrics"
    
    def store_query_metrics(
        self,
        query_id: str,
        session_id: str,
        metrics: Dict[str, Any],
        ttl_days: int = 7
    ):
        """Store query execution metrics"""
        key = f"{self.prefix}:query:{query_id}"
        
        # Store as hash
        self.redis.hset(key, mapping={
            "query_id": query_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "metrics_json": json.dumps(metrics)
        })
        
        # Set expiration
        self.redis.expire(key, ttl_days * 86400)
        
        # Add to session set
        session_key = f"{self.prefix}:session:{session_id}"
        self.redis.sadd(session_key, query_id)
        self.redis.expire(session_key, ttl_days * 86400)
        
        # Add to time series for historical trends
        ts_key = f"{self.prefix}:timeseries:latency"
        self.redis.zadd(
            ts_key,
            {query_id: metrics["performance"]["total_time_ms"]}
        )
    
    def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get aggregated metrics for a session"""
        session_key = f"{self.prefix}:session:{session_id}"
        query_ids = self.redis.smembers(session_key)
        
        if not query_ids:
            return {"query_count": 0}
        
        total_latency = 0
        total_cost = 0
        cache_hits = 0
        
        for query_id in query_ids:
            query_key = f"{self.prefix}:query:{query_id.decode()}"
            metrics_json = self.redis.hget(query_key, "metrics_json")
            
            if metrics_json:
                metrics = json.loads(metrics_json)
                total_latency += metrics["performance"]["total_time_ms"]
                total_cost += metrics["cost"]["total_cost_usd"]
                if metrics["cache_layers"][0]["hit"]:  # Semantic cache
                    cache_hits += 1
        
        query_count = len(query_ids)
        
        return {
            "session_id": session_id,
            "query_count": query_count,
            "avg_latency_ms": total_latency / query_count,
            "total_cost_usd": total_cost,
            "cache_hit_rate": (cache_hits / query_count) * 100
        }
    
    def get_historical_trends(
        self,
        start_date: datetime,
        end_date: datetime,
        metric: str = "latency"
    ) -> List[Dict[str, Any]]:
        """Get historical trend data"""
        # Simplified implementation - in production, use RedisTimeSeries
        ts_key = f"{self.prefix}:timeseries:{metric}"
        
        # Get all query IDs in time range
        # (In production, use proper time-based filtering)
        all_data = self.redis.zrange(ts_key, 0, -1, withscores=True)
        
        return [
            {"timestamp": datetime.now() - timedelta(hours=i), "value": score}
            for i, (query_id, score) in enumerate(all_data[:100])
        ]
```

---

## 🚀 Deployment Configuration

### Backend CORS Setup

```python
# src/api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="FinagentiX API")

# CORS configuration
if os.getenv("ENVIRONMENT") == "production":
    allowed_origins = [
        "https://finagentix.app",
        "https://www.finagentix.app"
    ]
else:
    allowed_origins = [
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)

# Serve static files in production
if os.getenv("SERVE_STATIC") == "true":
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
```

### Frontend Environment Configuration

```typescript
// frontend/src/config/api.ts

const getApiBaseUrl = (): string => {
  // Check environment
  if (import.meta.env.MODE === 'production') {
    return import.meta.env.VITE_API_URL || '/api';
  }
  
  // Development
  return import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
};

export const API_CONFIG = {
  baseURL: getApiBaseUrl(),
  timeout: 30000,  // 30 seconds
  retryAttempts: 3,
  retryDelay: 1000
};

// .env.development
// VITE_API_URL=http://localhost:8000

// .env.production
// VITE_API_URL=https://api.finagentix.app
```

---

## 📊 Performance Optimization Techniques

### 1. React Query for Efficient Data Fetching

```typescript
// frontend/src/hooks/useQueryMetrics.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/utils/api-client';

export const useQueryMetrics = (queryId: string) => {
  return useQuery({
    queryKey: ['metrics', queryId],
    queryFn: () => apiClient.get(`/metrics/query/${queryId}`),
    staleTime: 5 * 60 * 1000,  // 5 minutes
    cacheTime: 10 * 60 * 1000,  // 10 minutes
  });
};

export const useSubmitQuery = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (query: string) => apiClient.post('/query', { query }),
    onSuccess: (data) => {
      // Invalidate session metrics to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['session'] });
      
      // Add to query cache
      queryClient.setQueryData(['metrics', data.query_id], data);
    }
  });
};

export const useSessionMetrics = (sessionId: string) => {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => apiClient.get(`/metrics/session/${sessionId}`),
    refetchInterval: 10000,  // Refetch every 10 seconds
  });
};
```

### 2. Virtual Scrolling for Large Datasets

```typescript
// frontend/src/components/Chat/MessageList.tsx

import { useVirtualizer } from '@tanstack/react-virtual';
import { useRef } from 'react';

const MessageList: React.FC<{ messages: Message[] }> = ({ messages }) => {
  const parentRef = useRef<HTMLDivElement>(null);
  
  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 100,  // Estimated message height
    overscan: 5  // Render 5 extra items above/below viewport
  });
  
  return (
    <div ref={parentRef} className="h-full overflow-auto">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative'
        }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div
            key={virtualRow.index}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              transform: `translateY(${virtualRow.start}px)`
            }}
          >
            <Message message={messages[virtualRow.index]} />
          </div>
        ))}
      </div>
    </div>
  );
};
```

### 3. Memoization for Expensive Calculations

```typescript
// frontend/src/utils/metrics-calculator.ts

import { useMemo } from 'react';

export const useCalculatedMetrics = (response: EnhancedQueryResponse) => {
  return useMemo(() => {
    // Calculate derived metrics
    const totalTokens = response.agents.reduce(
      (sum, agent) => sum + agent.total_tokens,
      0
    );
    
    const avgAgentDuration = response.agents.reduce(
      (sum, agent) => sum + agent.duration_ms,
      0
    ) / response.agents.length;
    
    const parallelEfficiency = calculateParallelEfficiency(response);
    
    return {
      totalTokens,
      avgAgentDuration,
      parallelEfficiency,
      tokensPerDollar: totalTokens / response.cost.total_cost_usd
    };
  }, [response]);  // Only recalculate when response changes
};

const calculateParallelEfficiency = (response: EnhancedQueryResponse): number => {
  if (response.workflow.orchestration_pattern !== 'concurrent') {
    return 100;
  }
  
  const maxAgentDuration = Math.max(...response.agents.map(a => a.duration_ms));
  const sumAgentDurations = response.agents.reduce((sum, a) => sum + a.duration_ms, 0);
  
  return (maxAgentDuration / sumAgentDurations) * 100;
};
```

---

## 🧪 Testing Examples

### Backend Tests

```python
# tests/test_cost_tracking.py

import pytest
from src.utils.cost_tracking import CostCalculator

def test_llm_cost_calculation():
    """Test LLM cost calculation accuracy"""
    calc = CostCalculator(model="gpt-4o")
    
    # 1000 input, 500 output tokens
    cost = calc.calculate_llm_cost(input_tokens=1000, output_tokens=500)
    
    # Expected: (1000/1000 * 0.005) + (500/1000 * 0.015) = 0.005 + 0.0075 = 0.0125
    assert cost == 0.0125
    
def test_embedding_cost_calculation():
    """Test embedding cost calculation"""
    calc = CostCalculator()
    
    # 1200 tokens
    cost = calc.calculate_embedding_cost(tokens=1200)
    
    # Expected: 1200/1000 * 0.001 = 0.0012
    assert cost == 0.0012

def test_baseline_cost_estimation():
    """Test baseline cost estimation for workflow"""
    calc = CostCalculator()
    
    baseline = calc.estimate_baseline_cost("InvestmentAnalysisWorkflow")
    
    assert "embedding_cost" in baseline
    assert "router_cost" in baseline
    assert "agent_cost" in baseline
    assert "total_cost" in baseline
    assert baseline["total_cost"] > 0
```

### Frontend Tests

```typescript
// tests/components/CostBreakdown.test.tsx

import { render, screen } from '@testing-library/react';
import { CostBreakdown } from '@/components/Metrics/CostBreakdown';

describe('CostBreakdown', () => {
  const mockCost = {
    embedding_api_calls: 1,
    embedding_total_tokens: 1200,
    embedding_cost_usd: 0.0012,
    llm_api_calls: 4,
    llm_input_tokens: 1450,
    llm_output_tokens: 2050,
    llm_total_tokens: 3500,
    llm_cost_usd: 0.007,
    total_cost_usd: 0.0082,
    baseline_cost_usd: 0.0615,
    cost_savings_usd: 0.0533,
    cost_savings_percent: 87,
    cost_per_agent: {
      market_data: 0.0023,
      risk_analysis: 0.0019
    }
  };

  it('displays cost savings percentage correctly', () => {
    render(<CostBreakdown cost={mockCost} />);
    
    expect(screen.getByText(/87%/)).toBeInTheDocument();
  });

  it('displays total cost with correct formatting', () => {
    render(<CostBreakdown cost={mockCost} />);
    
    expect(screen.getByText(/\$0\.0082/)).toBeInTheDocument();
  });

  it('shows savings amount', () => {
    render(<CostBreakdown cost={mockCost} />);
    
    expect(screen.getByText(/\$0\.0533/)).toBeInTheDocument();
  });
});
```

---

## 📝 Conclusion

This implementation guide provides:
- ✅ Detailed component code examples
- ✅ Backend metrics collection patterns
- ✅ Cost calculation formulas with real pricing
- ✅ Performance optimization techniques
- ✅ Deployment configurations
- ✅ Testing strategies

Combined with the main GUI_DESIGN_SPECIFICATION.md, you now have a complete blueprint for implementing the metrics dashboard.

**Next Step**: Begin Phase 1 backend enhancements to start collecting these metrics!
