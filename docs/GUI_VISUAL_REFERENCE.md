# Quick Visual Reference - Metrics Dashboard

**Quick reference for UI components and data flows**

---

## 🎨 Component Hierarchy

```
App
│
├── DashboardLayout
│   │
│   ├── Header
│   │   ├── Logo
│   │   ├── SessionInfo
│   │   └── ActionButtons (Export, Settings)
│   │
│   ├── MainContent (Split Pane)
│   │   │
│   │   ├── ChatPanel (Left 40%)
│   │   │   ├── ChatInput
│   │   │   ├── MessageList
│   │   │   │   └── Message[]
│   │   │   │       ├── UserMessage
│   │   │   │       └── BotMessage
│   │   │   │           └── MetricsPreview
│   │   │   └── QuickStats
│   │   │
│   │   └── MetricsPanel (Right 60%)
│   │       ├── OverviewMetrics (Sticky)
│   │       ├── ExecutionTimeline
│   │       ├── AgentTable
│   │       │   └── ExpandableRow[]
│   │       │       └── ToolInvocationsList
│   │       ├── CostBreakdown
│   │       │   ├── StackedBarChart
│   │       │   └── SavingsIndicator
│   │       ├── CachePerformance
│   │       │   └── CacheLayerHeatmap
│   │       ├── PerformanceMetrics
│   │       │   └── TargetComparison
│   │       └── HistoricalTrends
│   │           ├── CostTrendChart
│   │           ├── AgentUsageChart
│   │           └── PerformanceHeatmap
│   │
│   └── Footer
│       └── StatusBar
```

---

## 📊 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  USER                                                       │
│  Enters Query: "Should I invest in TSLA?"                   │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (React)                                           │
│  1. ChatInput captures query                                │
│  2. useSubmitQuery mutation called                          │
│  3. POST /api/query with request body                       │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  API LAYER (FastAPI)                                        │
│  1. Initialize MetricsCollector                             │
│  2. Start timer                                             │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  SEMANTIC CACHE CHECK                                       │
│  ┌──────────────────────────────────────┐                  │
│  │ metrics.start_event("cache_check")   │                  │
│  │ embedding = embed_query(query)       │ → 34ms           │
│  │ similar = search_cache(embedding)    │ → 12ms           │
│  │ metrics.end_event()                  │                  │
│  └──────────────────────────────────────┘                  │
│                                                              │
│  Cache HIT? → YES → Return cached response + metrics        │
│            ↓ NO                                              │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  ROUTER AGENT                                               │
│  ┌──────────────────────────────────────┐                  │
│  │ metrics.start_event("router")        │                  │
│  │ route = find_route(query)            │ → 150ms          │
│  │ workflow = route["workflow"]         │                  │
│  │ agents = route["agents"]             │                  │
│  │ metrics.end_event()                  │                  │
│  └──────────────────────────────────────┘                  │
│                                                              │
│  Result: InvestmentAnalysisWorkflow                         │
│  Agents: [market_data, risk, sentiment, synthesis]          │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR (Sequential Pattern)                          │
│                                                              │
│  FOR EACH agent IN agents:                                  │
│    ┌────────────────────────────────────┐                  │
│    │ metrics.start_event("agent", name) │                  │
│    │                                    │                  │
│    │ 1. Build prompt with context      │                  │
│    │    input_tokens = count(prompt)   │                  │
│    │                                    │                  │
│    │ 2. Invoke tools (if needed)       │                  │
│    │    FOR tool IN agent.tools:       │                  │
│    │      ├─ Check tool cache          │                  │
│    │      ├─ Execute if miss           │                  │
│    │      └─ Track duration            │                  │
│    │                                    │                  │
│    │ 3. Call Azure OpenAI              │                  │
│    │    response = llm.chat(...)       │                  │
│    │    output_tokens = count(response)│                  │
│    │                                    │                  │
│    │ 4. Calculate cost                 │                  │
│    │    cost = calc_cost(input, output)│                  │
│    │                                    │                  │
│    │ metrics.end_event(agent_metrics)  │                  │
│    └────────────────────────────────────┘                  │
│                                                              │
│  Agent 1: Market Data      → 380ms, 757 tokens, $0.0023    │
│  Agent 2: Risk Analysis    → 340ms, 678 tokens, $0.0019    │
│  Agent 3: News Sentiment   → 290ms, 543 tokens, $0.0016    │
│  Agent 4: Synthesis        → 360ms, 1004 tokens, $0.0024   │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  COST CALCULATOR                                            │
│  ┌────────────────────────────────────────────────────────┐│
│  │ embedding_cost = 1200 tokens × $0.001 / 1k = $0.0012  ││
│  │ llm_cost = (1450 input × $0.005 / 1k) +               ││
│  │            (2050 output × $0.015 / 1k) = $0.0070      ││
│  │ total_cost = $0.0082                                  ││
│  │                                                        ││
│  │ baseline_cost = estimate_without_cache() = $0.0615    ││
│  │ savings = $0.0615 - $0.0082 = $0.0533 (87%)           ││
│  └────────────────────────────────────────────────────────┘│
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  METRICS AGGREGATION                                        │
│  ┌────────────────────────────────────────────────────────┐│
│  │ Build EnhancedQueryResponse:                          ││
│  │                                                        ││
│  │ - workflow: WorkflowExecution(...)                    ││
│  │ - agents: [AgentExecution(...), ...]                  ││
│  │ - cache_layers: [CacheLayerMetrics(...), ...]         ││
│  │ - cost: CostBreakdown(...)                            ││
│  │ - performance: PerformanceMetrics(...)                ││
│  │ - session: SessionMetrics(...)                        ││
│  │ - timeline: metrics.get_timeline_data()               ││
│  └────────────────────────────────────────────────────────┘│
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  STORAGE (Redis)                                            │
│  ┌────────────────────────────────────────────────────────┐│
│  │ 1. Store query metrics (TTL: 7 days)                  ││
│  │    Key: metrics:query:{query_id}                      ││
│  │                                                        ││
│  │ 2. Add to session set                                 ││
│  │    Key: metrics:session:{session_id}                  ││
│  │                                                        ││
│  │ 3. Update time series                                 ││
│  │    Key: metrics:timeseries:latency                    ││
│  │    Key: metrics:timeseries:cost                       ││
│  │                                                        ││
│  │ 4. Cache response (semantic cache)                    ││
│  │    embedding → query → response                       ││
│  └────────────────────────────────────────────────────────┘│
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  RESPONSE TO FRONTEND                                       │
│  {                                                          │
│    "query": "Should I invest in TSLA?",                     │
│    "response": "Based on analysis...",                      │
│    "timestamp": "2025-01-15T10:32:42.684Z",                 │
│    "workflow": {...},                                       │
│    "agents": [4 agent objects with full metrics],           │
│    "cache_layers": [3 cache layer objects],                 │
│    "cost": {                                                │
│      "total_cost_usd": 0.0082,                              │
│      "savings_percent": 87,                                 │
│      ...                                                    │
│    },                                                       │
│    "performance": {...},                                    │
│    "session": {...}                                         │
│  }                                                          │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND RENDERING                                         │
│                                                              │
│  1. React Query caches response                             │
│  2. Update MessageList with new message                     │
│  3. Update QuickStats (session metrics)                     │
│  4. When user clicks "Details":                             │
│     ├─ Render OverviewMetrics                               │
│     ├─ Render ExecutionTimeline (timeline data)             │
│     ├─ Render AgentTable (agents array)                     │
│     ├─ Render CostBreakdown (cost object)                   │
│     ├─ Render CachePerformance (cache_layers)               │
│     └─ Render PerformanceMetrics (performance object)       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔢 Metrics Calculation Reference

### LLM Cost Formula
```
Input Cost  = (input_tokens / 1000) × $0.005
Output Cost = (output_tokens / 1000) × $0.015
Total Cost  = Input Cost + Output Cost

Example:
  Input:  1450 tokens → (1450 / 1000) × $0.005 = $0.00725
  Output: 2050 tokens → (2050 / 1000) × $0.015 = $0.03075
  Total:  $0.00725 + $0.03075 = $0.038
```

### Embedding Cost Formula
```
Cost = (tokens / 1000) × $0.001

Example:
  1200 tokens → (1200 / 1000) × $0.001 = $0.0012
```

### Cache Savings Formula
```
Baseline = estimate_baseline_cost(workflow)
Actual   = sum(agent_costs) + embedding_cost
Savings  = Baseline - Actual
Percent  = (Savings / Baseline) × 100

Example:
  Baseline: $0.0615 (4 agents without caching)
  Actual:   $0.0082 (2 cache hits, 2 agents executed)
  Savings:  $0.0533
  Percent:  87%
```

### Parallel Efficiency Formula
```
Max Duration = max(agent.duration for agent in agents)
Sum Duration = sum(agent.duration for agent in agents)
Efficiency   = (Max Duration / Sum Duration) × 100

Example:
  Agent 1: 380ms
  Agent 2: 340ms (parallel with Agent 1)
  Max: 380ms
  Sum: 720ms
  Efficiency: (380 / 720) × 100 = 52.8%
  
  (Lower is better for concurrent, 100% for sequential)
```

---

## 📋 State Management Flow

### Global State (Zustand)
```typescript
interface DashboardStore {
  // Session
  sessionId: string;
  sessionMetrics: SessionMetrics;
  
  // Messages
  messages: Message[];
  activeMessageId: string | null;
  
  // Settings
  showMetrics: boolean;
  metricsLayout: 'side' | 'bottom' | 'fullscreen';
  
  // Actions
  addMessage: (message: Message) => void;
  selectMessage: (id: string) => void;
  updateSession: (metrics: SessionMetrics) => void;
}
```

### React Query Cache
```typescript
// Query keys structure
['messages', sessionId]              // Message list
['metrics', queryId]                 // Single query metrics
['session', sessionId]               // Session aggregates
['historical', dateRange]            // Historical trends
['comparison', [queryId1, queryId2]] // Side-by-side comparison
```

### Local Component State
```typescript
// ExecutionTimeline component
const [hoveredEvent, setHoveredEvent] = useState<string | null>(null);
const [zoomLevel, setZoomLevel] = useState<number>(1);

// AgentTable component
const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
const [sortConfig, setSortConfig] = useState({ key: 'duration', direction: 'desc' });

// CostBreakdown component
const [showDetails, setShowDetails] = useState<boolean>(false);
```

---

## 🎨 Color Palette Reference

### Primary Colors
```css
--primary-50:  #eff6ff;   /* Very light blue */
--primary-100: #dbeafe;
--primary-200: #bfdbfe;
--primary-300: #93c5fd;
--primary-400: #60a5fa;
--primary-500: #3b82f6;   /* Main blue */
--primary-600: #2563eb;
--primary-700: #1d4ed8;
--primary-800: #1e40af;
--primary-900: #1e3a8a;
```

### Status Colors
```css
/* Success/Hit */
--success-light: #d1fae5;
--success:       #10b981;
--success-dark:  #047857;

/* Error/Miss */
--error-light:   #fee2e2;
--error:         #ef4444;
--error-dark:    #b91c1c;

/* Warning/Partial */
--warning-light: #fef3c7;
--warning:       #f59e0b;
--warning-dark:  #d97706;

/* Info */
--info-light:    #dbeafe;
--info:          #3b82f6;
--info-dark:     #1d4ed8;
```

### Cost Indicators
```css
/* Very Low: < $0.005 */
--cost-very-low: #10b981;

/* Low/Target: $0.005 - $0.01 */
--cost-low: #3b82f6;

/* Medium: $0.01 - $0.02 */
--cost-medium: #f59e0b;

/* High: > $0.02 */
--cost-high: #ef4444;
```

### Performance Indicators
```css
/* Excellent: < 1s */
--perf-excellent: #10b981;

/* Good: 1-2s */
--perf-good: #3b82f6;

/* Fair: 2-3s */
--perf-fair: #f59e0b;

/* Poor: > 3s */
--perf-poor: #ef4444;
```

---

## 📐 Responsive Breakpoints

```css
/* Mobile */
@media (max-width: 767px) {
  /* Stacked layout */
  .dashboard-layout {
    flex-direction: column;
  }
  
  .chat-panel,
  .metrics-panel {
    width: 100%;
  }
  
  /* Collapsible metrics */
  .metrics-panel {
    max-height: 400px;
    overflow-y: auto;
  }
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1199px) {
  /* Tabbed interface */
  .main-content {
    display: flex;
    position: relative;
  }
  
  .chat-panel,
  .metrics-panel {
    width: 100%;
    position: absolute;
  }
  
  /* Toggle between panels */
  .chat-panel.active {
    z-index: 10;
  }
}

/* Desktop */
@media (min-width: 1200px) {
  /* Side-by-side */
  .dashboard-layout {
    display: grid;
    grid-template-columns: 40% 60%;
  }
}

/* Large Desktop */
@media (min-width: 1920px) {
  /* More space for metrics */
  .dashboard-layout {
    grid-template-columns: 35% 65%;
  }
}
```

---

## 🔍 Sample API Requests/Responses

### Submit Query
```http
POST /api/query
Content-Type: application/json

{
  "query": "Should I invest in TSLA?",
  "user_id": "user_123",
  "session_id": "session_abc",
  "params": {}
}
```

### Response (Abbreviated)
```json
{
  "query": "Should I invest in TSLA?",
  "response": "Based on comprehensive analysis...",
  "timestamp": "2025-01-15T10:32:42.684Z",
  
  "workflow": {
    "workflow_name": "InvestmentAnalysisWorkflow",
    "orchestration_pattern": "sequential",
    "routing_time_ms": 150,
    "agents_invoked_count": 4
  },
  
  "agents": [
    {
      "agent_name": "Market Data Agent",
      "duration_ms": 380,
      "input_tokens": 245,
      "output_tokens": 512,
      "cost_usd": 0.0023,
      "status": "success"
    }
  ],
  
  "cost": {
    "total_cost_usd": 0.0082,
    "baseline_cost_usd": 0.0615,
    "cost_savings_percent": 87
  },
  
  "performance": {
    "total_time_ms": 1450,
    "meets_latency_target": true,
    "meets_cost_target": true
  }
}
```

### Get Session Metrics
```http
GET /api/metrics/session/session_abc
```

```json
{
  "session_id": "session_abc",
  "query_count": 47,
  "avg_latency_ms": 1203,
  "total_cost_usd": 0.3854,
  "cache_hit_rate": 68.1
}
```

---

## 📊 Chart Configuration Examples

### Execution Timeline (Recharts)
```typescript
<BarChart
  width={800}
  height={400}
  data={timelineData}
  layout="vertical"
>
  <XAxis type="number" domain={[0, totalDuration]} />
  <YAxis type="category" dataKey="name" />
  <Tooltip />
  <Bar dataKey="duration">
    {data.map((entry, index) => (
      <Cell key={`cell-${index}`} fill={getColor(entry.type)} />
    ))}
  </Bar>
</BarChart>
```

### Cost Breakdown (Stacked Bar)
```typescript
<BarChart width={600} height={300} data={costData}>
  <XAxis dataKey="scenario" />
  <YAxis />
  <Tooltip formatter={(value) => `$${value.toFixed(4)}`} />
  <Legend />
  <Bar dataKey="embedding" stackId="a" fill="#3b82f6" />
  <Bar dataKey="llm" stackId="a" fill="#10b981" />
</BarChart>
```

### Historical Trend (Line Chart)
```typescript
<LineChart width={800} height={400} data={historicalData}>
  <XAxis dataKey="timestamp" />
  <YAxis />
  <Tooltip />
  <Legend />
  <Line type="monotone" dataKey="cost" stroke="#ef4444" />
  <Line type="monotone" dataKey="latency" stroke="#3b82f6" />
</LineChart>
```

---

**This quick reference provides the essential visual and technical details for implementing the metrics dashboard.**
