# Stage 5 Deployment Plan: Multi-Agent System

**Framework**: Microsoft Agent Framework (successor to AutoGen)  
**Deployment Target**: Azure Container Apps (serverless, scale-to-zero)  
**API Layer**: FastAPI with WebSocket support  
**Phase Duration**: 5-7 days  

---

## 🎯 Overview

Deploy a production-ready multi-agent system using **Microsoft Agent Framework** that orchestrates 7+ specialized AI agents for financial analysis. The system will leverage Redis for semantic caching, vector search, and feature storage, delivering 85% cost reduction through intelligent caching.

### Why Microsoft Agent Framework?

1. **Official Microsoft Framework** - Built for production, not experimental
2. **Azure-Native** - First-class Azure OpenAI integration
3. **Durable Agents** - Built-in state management with Azure Functions
4. **Streaming Support** - Real-time responses via Responses API
5. **Tool Integration** - Native support for function calling
6. **Production Ready** - Non-breaking changes guarantee

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Request                            │
│                     (FastAPI REST/WebSocket)                    │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                           │
│              (Workflow Coordinator + Router)                    │
│   - Semantic routing with Redis cache                          │
│   - Workflow planning and execution                            │
└────────┬────────┬────────┬────────┬────────┬──────────┬────────┘
         ↓        ↓        ↓        ↓        ↓          ↓
┌────────────┐┌──────────┐┌──────────┐┌──────────┐┌──────────┐┌──────────┐
│  Market    ││  News    ││   Risk   ││Fundamental││  Router  ││Synthesis │
│  Data      ││Sentiment ││Assessment││ Analysis  ││  Agent   ││  Agent   │
│  Agent     ││  Agent   ││  Agent   ││  Agent    ││          ││          │
└─────┬──────┘└─────┬────┘└─────┬────┘└─────┬─────┘└────┬─────┘└────┬─────┘
      │             │            │            │            │           │
      └─────────────┴────────────┴────────────┴────────────┴───────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                     Redis Enterprise                            │
│  - Vector Search (HNSW)    - Semantic Cache                     │
│  - Time Series Data        - Feature Store                      │
│  - Tool Output Cache       - Session State                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Phase Breakdown

### **Phase 5.1: Setup Agent Framework Infrastructure** (Day 1)

**Goal**: Install Microsoft Agent Framework and configure Azure integration

#### Tasks:
1. Install Agent Framework packages
2. Configure Azure OpenAI client with DefaultAzureCredential
3. Set up development environment
4. Create base agent structure

#### Files to Create:
- `requirements-agents.txt` - Agent-specific dependencies
- `src/agents/__init__.py` - Package initialization
- `src/agents/config.py` - Agent configuration
- `src/agents/base_agent.py` - Base agent class

#### Script:
```bash
# scripts/setup_agent_framework.sh
```

**Deliverable**: Working Agent Framework environment with Azure OpenAI connection

---

### **Phase 5.2: Create Core Agent Definitions** (Day 2)

**Goal**: Define all 7+ specialized agents with instructions and capabilities

#### Agents to Create:

1. **Orchestrator Agent** (`orchestrator_agent.py`)
   - Coordinates workflow execution
   - Manages agent handoffs
   - Implements sequential/parallel patterns

2. **Market Data Agent** (`market_data_agent.py`)
   - Retrieves stock prices from Redis TimeSeries
   - Calculates technical indicators
   - Tools: get_stock_price, calculate_moving_average, get_volume

3. **News Sentiment Agent** (`news_sentiment_agent.py`)
   - Searches news via Redis vector search
   - Analyzes sentiment
   - Tools: search_news, get_sentiment

4. **Risk Assessment Agent** (`risk_agent.py`)
   - Calculates volatility and risk metrics
   - Retrieves from feature store
   - Tools: calculate_volatility, get_risk_metrics

5. **Fundamental Analysis Agent** (`fundamental_agent.py`)
   - Searches SEC filings via Redis vectors
   - Analyzes financial statements
   - Tools: search_sec_filings, analyze_financials

6. **Router Agent** (`router_agent.py`)
   - Semantic routing with Redis cache
   - Query pattern matching
   - Tools: route_query, get_workflow

7. **Synthesis Agent** (`synthesis_agent.py`)
   - Combines agent outputs
   - Generates final response
   - Tools: synthesize_results

#### Files:
```
src/agents/
├── __init__.py
├── base_agent.py
├── orchestrator_agent.py
├── market_data_agent.py
├── news_sentiment_agent.py
├── risk_agent.py
├── fundamental_agent.py
├── router_agent.py
└── synthesis_agent.py
```

**Deliverable**: 7 fully-defined agents with instructions and tool definitions

---

### **Phase 5.3: Implement Redis Tools & Integrations** (Day 3)

**Goal**: Create tool functions that agents can call to access Redis data

#### Tools to Implement:

**Vector Search Tools**:
- `search_sec_filings(ticker, query, top_k=5)` - RAG for SEC docs
- `search_news(ticker, query, top_k=5)` - RAG for news
- `search_similar_queries(query)` - Semantic cache lookup

**Time Series Tools**:
- `get_stock_price(ticker, start_date, end_date)` - Historical prices
- `get_trading_volume(ticker, start_date, end_date)` - Volume data

**Feature Store Tools**:
- `get_technical_indicators(ticker)` - Moving averages, RSI, etc.
- `get_risk_metrics(ticker)` - Volatility, beta, Sharpe ratio
- `calculate_moving_average(ticker, period)` - Dynamic calculation

**Caching Tools**:
- `cache_tool_output(tool_name, params, output)` - Store tool result
- `get_cached_tool_output(tool_name, params)` - Retrieve cached result
- `cache_query_response(query, response)` - Semantic cache storage

**Routing Tools**:
- `get_workflow_route(query_pattern)` - Cached routing decision
- `store_workflow_route(pattern, workflow)` - Update routing cache

#### Files:
```
src/tools/
├── __init__.py
├── vector_tools.py
├── timeseries_tools.py
├── feature_tools.py
├── cache_tools.py
└── routing_tools.py
```

**Deliverable**: 15+ tool functions that agents can invoke

---

### **Phase 5.4: Build Agent Orchestration Logic** (Day 4)

**Goal**: Implement workflow patterns and agent coordination

#### Orchestration Patterns:

1. **Sequential Pattern** - Agents run in order
   ```python
   market_data → news_sentiment → risk → synthesis
   ```

2. **Parallel Pattern** - Agents run simultaneously
   ```python
   [market_data, news_sentiment, risk, fundamental] → synthesis
   ```

3. **Conditional Pattern** - Dynamic routing based on query
   ```python
   router → if (investment_query) → investment_workflow
            else if (risk_query) → risk_workflow
   ```

4. **Handoff Pattern** - Specialized agents take over
   ```python
   orchestrator → market_agent (if needs price data)
   orchestrator → fundamental_agent (if needs SEC data)
   ```

#### Workflow Implementation:

**Investment Analysis Workflow**:
```python
# workflows/investment_workflow.py
async def run_investment_analysis(ticker: str, query: str):
    # Parallel execution
    market_task = market_agent.run(ticker)
    news_task = news_agent.run(ticker)
    risk_task = risk_agent.run(ticker)
    fundamental_task = fundamental_agent.run(ticker)
    
    # Wait for all
    results = await asyncio.gather(
        market_task, news_task, risk_task, fundamental_task
    )
    
    # Synthesize
    final_answer = await synthesis_agent.run(results)
    return final_answer
```

#### Files:
```
src/workflows/
├── __init__.py
├── investment_workflow.py
├── risk_workflow.py
├── comparison_workflow.py
└── orchestrator.py
```

**Deliverable**: 3 workflow patterns with orchestration logic

---

### **Phase 5.5: Deploy to Azure Container Apps** (Day 5)

**Goal**: Containerize and deploy agents to Azure with auto-scaling

#### Deployment Steps:

1. **Create Dockerfile**:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY src/ ./src/
   CMD ["python", "-m", "src.main"]
   ```

2. **Build Container Image**:
   ```bash
   docker build -t finagentix-agents:latest .
   docker tag finagentix-agents:latest $ACR_NAME.azurecr.io/finagentix-agents:latest
   docker push $ACR_NAME.azurecr.io/finagentix-agents:latest
   ```

3. **Deploy to Container Apps**:
   ```bash
   az containerapp create \
     --name finagentix-agents \
     --resource-group finagentix-dev-rg \
     --environment finagentix-env \
     --image $ACR_NAME.azurecr.io/finagentix-agents:latest \
     --target-port 8000 \
     --ingress external \
     --min-replicas 0 \
     --max-replicas 10 \
     --cpu 1.0 \
     --memory 2.0Gi
   ```

#### Bicep Template:
```bicep
# infra/stages/stage5-agents.bicep
```

#### Files:
- `Dockerfile`
- `infra/stages/stage5-agents.bicep`
- `scripts/deploy_agents.sh`

**Deliverable**: Agents deployed to Azure Container Apps with auto-scaling

---

### **Phase 5.6: Create FastAPI REST API Layer** (Day 6)

**Goal**: Build REST API with WebSocket support for real-time streaming

#### API Endpoints:

**REST Endpoints**:
- `POST /api/query` - Submit query, get full response
- `GET /api/health` - Health check
- `GET /api/agents` - List available agents
- `GET /api/workflows` - List workflows

**WebSocket Endpoint**:
- `WS /ws/stream` - Real-time streaming responses

#### FastAPI Implementation:

```python
# src/api/main.py
from fastapi import FastAPI, WebSocket
from fastapi.responses import StreamingResponse

app = FastAPI(title="FinagentiX Agent API")

@app.post("/api/query")
async def query(request: QueryRequest):
    # Check semantic cache first
    cached = await check_semantic_cache(request.query)
    if cached:
        return cached
    
    # Route to workflow
    workflow = await router_agent.route(request.query)
    
    # Execute workflow
    result = await orchestrator.execute(workflow, request)
    
    # Cache response
    await cache_response(request.query, result)
    
    return result

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    query = await websocket.receive_text()
    
    # Stream agent responses
    async for chunk in orchestrator.stream(query):
        await websocket.send_json(chunk)
```

#### Files:
```
src/api/
├── __init__.py
├── main.py
├── models.py
├── routes.py
└── websocket.py
```

**Deliverable**: FastAPI REST API with streaming WebSocket support

---

### **Phase 5.7: Testing & Validation** (Day 7)

**Goal**: End-to-end testing of agent system

#### Tests:

1. **Unit Tests** - Individual agent behavior
2. **Integration Tests** - Multi-agent workflows
3. **Performance Tests** - Latency and throughput
4. **Cache Tests** - Semantic cache hit rate
5. **Load Tests** - Concurrent requests

#### Test Scenarios:

```python
# tests/test_workflows.py
async def test_investment_workflow():
    result = await orchestrator.run(
        "Should I invest in AAPL?"
    )
    assert "AAPL" in result.text
    assert result.agents_used == ["router", "market", "news", "risk", "synthesis"]
    assert result.cache_hit == False  # First run
    
    # Second run should hit cache
    result2 = await orchestrator.run(
        "Should I invest in AAPL?"
    )
    assert result2.cache_hit == True
```

**Deliverable**: Full test suite with 85%+ coverage

---

## 📦 Deliverables Summary

### Code Structure:
```
FinagentiX/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py
│   │   ├── orchestrator_agent.py
│   │   ├── market_data_agent.py
│   │   ├── news_sentiment_agent.py
│   │   ├── risk_agent.py
│   │   ├── fundamental_agent.py
│   │   ├── router_agent.py
│   │   └── synthesis_agent.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── vector_tools.py
│   │   ├── timeseries_tools.py
│   │   ├── feature_tools.py
│   │   ├── cache_tools.py
│   │   └── routing_tools.py
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── investment_workflow.py
│   │   ├── risk_workflow.py
│   │   └── orchestrator.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── models.py
│   │   └── websocket.py
│   └── main.py
├── tests/
│   ├── test_agents.py
│   ├── test_tools.py
│   ├── test_workflows.py
│   └── test_api.py
├── infra/
│   └── stages/
│       └── stage5-agents.bicep
├── scripts/
│   ├── setup_agent_framework.sh
│   ├── deploy_agents.sh
│   └── test_agents.sh
├── Dockerfile
├── requirements-agents.txt
└── docs/
    └── STAGE5_PLAN.md
```

---

## 🚀 Deployment Commands

### Setup (Day 1):
```bash
# Install Agent Framework
./scripts/setup_agent_framework.sh

# Verify installation
python -c "from agent_framework import ChatAgent; print('✅ Agent Framework installed')"
```

### Deploy (Day 5):
```bash
# Build and deploy
./scripts/deploy_agents.sh

# Verify deployment
curl https://finagentix-agents.azurecontainerapps.io/api/health
```

### Test (Day 7):
```bash
# Run tests
./scripts/test_agents.sh

# Load test
./scripts/load_test_agents.sh
```

---

## 💰 Cost Optimization

### Container Apps Pricing:
- **Scale-to-zero**: $0 when idle
- **Running**: ~$0.00002/vCPU-second = ~$50/month at 10% utilization
- **Storage**: Negligible (stateless, uses Redis)

### Expected Monthly Costs:
- **Container Apps**: $50/month (scale-to-zero)
- **Redis Enterprise**: $471/month (B5 tier)
- **Azure OpenAI**: $2,550/month (85% cache savings)
- **Container Registry**: $5/month (Basic tier)
- **Total**: **$3,076/month** vs $17,471 without caching = **82% savings**

---

## 📊 Success Metrics

### Performance:
- Query latency: <2 seconds (end-to-end)
- Cache hit rate: >85%
- Agent response time: <500ms per agent
- WebSocket streaming: <100ms chunks

### Reliability:
- Uptime: 99.9%
- Error rate: <0.1%
- Auto-scaling: 0-10 instances

### Cost:
- LLM cost reduction: 85%
- Infrastructure cost: <$100/month
- Total monthly cost: <$3,100

---

## 🔄 Next Steps

After Stage 5 completion:
1. **Stage 6**: Production hardening (monitoring, alerts, CI/CD)
2. **Stage 7**: Frontend UI (React dashboard)
3. **Stage 8**: Advanced features (portfolio tracking, alerts)

---

**Status**: Ready to begin Phase 5.1 (Setup Agent Framework)  
**Est. Completion**: 7 days from start  
**Blocker**: None - all dependencies ready
