# Quick Reference - Enhanced Metrics API

## 🚀 New Endpoints

### 1. Enhanced Query Endpoint (Recommended)
```bash
POST http://localhost:8000/api/query/enhanced
```

**Request:**
```json
{
  "query": "Should I invest in TSLA?",
  "user_id": "user_123",
  "ticker": "TSLA"  // optional
}
```

**Response:** Returns `EnhancedQueryResponse` with 60+ metrics including:
- Agent execution details (per agent)
- Cost breakdown with savings
- Performance metrics
- Cache layer performance
- Execution timeline
- Session statistics

---

### 2. Metrics Endpoints

#### Get Current Pricing
```bash
GET http://localhost:8000/api/metrics/pricing
```
Returns Azure OpenAI pricing and baseline workflow costs.

#### Get Cache Metrics
```bash
GET http://localhost:8000/api/metrics/cache
```
Returns cache hit rate, tokens saved, cost savings.

#### Get Performance Metrics
```bash
GET http://localhost:8000/api/metrics/performance
```
Returns latency stats, success rates, performance targets.

#### Get Dashboard Summary
```bash
GET http://localhost:8000/api/metrics/summary
```
Returns comprehensive overview combining all metrics.

---

## 📊 Response Structure

### EnhancedQueryResponse

```typescript
interface EnhancedQueryResponse {
  // Basic fields
  query: string;
  response: string;
  timestamp: string;
  query_id: string;
  
  // Workflow details
  workflow: {
    workflow_name: string;
    orchestration_pattern: "sequential" | "concurrent" | "handoff";
    routing_time_ms: number;
    agents_invoked_count: number;
    agents_available_count: number;
  };
  
  // Agent executions (array)
  agents: Array<{
    agent_name: string;
    agent_id: string;
    agent_index: number;
    duration_ms: number;
    status: "success" | "error" | "timeout";
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    model_used: string;
    cost_usd: number;
    tools_invoked: Array<{...}>;
  }>;
  
  // Cache layers (array)
  cache_layers: Array<{
    layer_name: string;
    checked: boolean;
    hit: boolean;
    similarity: number;
    query_time_ms: number;
    cost_saved_usd: number;
    matched_query?: string;
  }>;
  
  // Overall cache status
  overall_cache_hit: boolean;
  
  // Cost breakdown
  cost: {
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
  };
  
  // Performance metrics
  performance: {
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
  };
  
  // Session metrics
  session: {
    session_id: string;
    query_count: number;
    avg_latency_ms: number;
    total_cost_usd: number;
    cache_hit_rate: number;
  };
  
  // Execution timeline
  timeline: {
    total_duration_ms: number;
    events: Array<{
      id: string;
      type: string;
      name: string;
      start_time_ms: number;
      end_time_ms: number;
      duration_ms: number;
      status: string;
      metadata: Record<string, any>;
    }>;
  };
}
```

---

## 🎯 Usage Examples

### Frontend Data Fetching

```typescript
// React component example
import { useQuery } from '@tanstack/react-query';

interface QueryRequest {
  query: string;
  user_id: string;
  ticker?: string;
}

async function executeQuery(request: QueryRequest) {
  const response = await fetch('http://localhost:8000/api/query/enhanced', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });
  
  if (!response.ok) throw new Error('Query failed');
  return response.json();
}

function QueryComponent() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['query', query],
    queryFn: () => executeQuery({
      query: 'Should I buy AAPL?',
      user_id: 'user_123'
    })
  });
  
  if (isLoading) return <Loading />;
  if (error) return <Error message={error.message} />;
  
  return (
    <div>
      <Response text={data.response} />
      <CostBreakdown cost={data.cost} />
      <Timeline events={data.timeline.events} />
      <AgentList agents={data.agents} />
    </div>
  );
}
```

### Fetching Metrics

```typescript
// Get cache metrics
async function getCacheMetrics() {
  const response = await fetch('http://localhost:8000/api/metrics/cache');
  return response.json();
}

// Get performance metrics
async function getPerformanceMetrics() {
  const response = await fetch('http://localhost:8000/api/metrics/performance');
  return response.json();
}

// Get dashboard summary
async function getDashboardSummary() {
  const response = await fetch('http://localhost:8000/api/metrics/summary');
  return response.json();
}
```

---

## 📈 Visualization Examples

### Cost Comparison Chart

```typescript
import { BarChart, Bar, XAxis, YAxis, Legend, Tooltip } from 'recharts';

function CostComparisonChart({ cost }: { cost: CostBreakdown }) {
  const data = [
    {
      name: 'Baseline',
      cost: cost.baseline_cost_usd
    },
    {
      name: 'Actual',
      cost: cost.total_cost_usd
    },
    {
      name: 'Savings',
      cost: cost.cost_savings_usd,
      fill: '#10b981'  // Green for savings
    }
  ];
  
  return (
    <BarChart width={400} height={300} data={data}>
      <XAxis dataKey="name" />
      <YAxis />
      <Tooltip formatter={(value) => `$${value.toFixed(4)}`} />
      <Bar dataKey="cost" fill="#3b82f6" />
    </BarChart>
  );
}
```

### Execution Timeline

```typescript
import { LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';

function ExecutionTimeline({ timeline }: { timeline: ExecutionTimeline }) {
  const data = timeline.events.map(event => ({
    name: event.name,
    start: event.start_time_ms,
    end: event.end_time_ms,
    duration: event.duration_ms
  }));
  
  return (
    <div>
      <h3>Execution Timeline ({timeline.total_duration_ms.toFixed(2)}ms)</h3>
      {timeline.events.map((event, idx) => (
        <div key={idx} className="timeline-event">
          <div className="event-bar" style={{
            marginLeft: `${event.start_time_ms / timeline.total_duration_ms * 100}%`,
            width: `${event.duration_ms / timeline.total_duration_ms * 100}%`,
            backgroundColor: event.status === 'success' ? '#10b981' : '#ef4444'
          }}>
            {event.name} ({event.duration_ms.toFixed(1)}ms)
          </div>
        </div>
      ))}
    </div>
  );
}
```

### Agent Execution Table

```typescript
import { Table } from '@/components/ui/table';

function AgentExecutionTable({ agents }: { agents: AgentExecution[] }) {
  return (
    <Table>
      <thead>
        <tr>
          <th>Agent</th>
          <th>Duration</th>
          <th>Tokens</th>
          <th>Cost</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {agents.map((agent, idx) => (
          <tr key={idx}>
            <td>{agent.agent_name}</td>
            <td>{agent.duration_ms.toFixed(2)}ms</td>
            <td>{agent.total_tokens}</td>
            <td>${agent.cost_usd.toFixed(4)}</td>
            <td>
              <Badge color={agent.status === 'success' ? 'green' : 'red'}>
                {agent.status}
              </Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
```

---

## 🔧 Backend Integration

### Using MetricsCollector in Custom Workflows

```python
from src.utils.metrics_collector import MetricsCollector

async def my_custom_workflow(query: str):
    # Initialize metrics collector
    metrics = MetricsCollector(
        query=query,
        session_id="session_123",
        user_id="user_456"
    )
    
    # Start workflow tracking
    workflow_event = metrics.start_event("workflow", "Custom Workflow")
    
    # Track agent execution
    agent_event = metrics.start_event("agent_execution", "My Agent")
    response = await execute_my_agent(query)
    
    # Record agent metrics
    metrics.record_agent_execution(
        agent_name="My Agent",
        agent_id="my_agent_v1",
        duration_ms=350,
        input_tokens=200,
        output_tokens=450,
        model="gpt-4o",
        cost=0.0025,
        status="success",
        response=response
    )
    
    metrics.end_event(agent_event, status="success")
    metrics.end_event(workflow_event, status="success")
    
    # Get comprehensive metrics
    timeline = metrics.get_timeline_data()
    costs = metrics.calculate_costs("CustomWorkflow")
    performance = metrics.get_performance_metrics(timeline['total_duration_ms'])
    
    return {
        "response": response,
        "metrics": {
            "timeline": timeline,
            "costs": costs,
            "performance": performance
        }
    }
```

---

## 🎨 Color Coding Standards

### Cost Indicators
- **Green (#10b981)**: Cost savings, efficient execution
- **Yellow (#f59e0b)**: Near target cost
- **Red (#ef4444)**: Above target cost

### Performance Indicators
- **Green (#10b981)**: < 1500ms (excellent)
- **Yellow (#f59e0b)**: 1500-2000ms (good)
- **Red (#ef4444)**: > 2000ms (needs optimization)

### Cache Hit Indicators
- **Green (#10b981)**: Cache hit (>92% similarity)
- **Yellow (#f59e0b)**: Near miss (85-92% similarity)
- **Gray (#6b7280)**: Cache miss (<85% similarity)

### Status Indicators
- **Green (#10b981)**: Success
- **Yellow (#f59e0b)**: Warning
- **Red (#ef4444)**: Error
- **Blue (#3b82f6)**: In Progress

---

## 📝 Notes

### Legacy Endpoint
The original `/api/query` endpoint still works and returns the simple `QueryResponse` for backward compatibility.

### Session Tracking
Session metrics are tracked per `session_id`. For multi-user applications, use unique session IDs per user session.

### Cost Accuracy
All costs are calculated using tiktoken for token-accurate pricing. Costs are in USD based on Azure OpenAI pricing as of January 2025.

### Performance Targets
- **Latency Target:** < 2000ms total time
- **Cost Target:** < $0.02 per query
- **Cache Hit Target:** > 60% hit rate

---

**Last Updated:** December 11, 2025  
**API Version:** 1.0.0  
**Phase:** 1 (Backend Complete)
