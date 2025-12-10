# Microsoft Agent Framework Migration Plan

**Document Version:** 1.0  
**Date:** December 10, 2024  
**Status:** Planning Phase

---

## Executive Summary

This document outlines the migration strategy for FinagentiX from custom agent implementations to **Microsoft Agent Framework** (specifically using Semantic Kernel Python SDK, as Microsoft Agent Framework Python is under development).

### Key Decision: Use Semantic Kernel Python SDK

**Microsoft Agent Framework** is currently available in C# (preview). For Python, we'll use **Semantic Kernel** which provides:
- Agent orchestration patterns (Concurrent, Sequential, Handoff, Group Chat, Magentic)
- Integration with Azure OpenAI
- Built-in observability with OpenTelemetry
- Microsoft's recommended approach for Python agentic applications

**Official Documentation:**
- [Semantic Kernel Agent Framework](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/)
- [Agent Orchestration Patterns](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/)
- [Microsoft Agent Framework Overview](https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview)

---

## Current State Analysis

### What We Have Today

**Custom Agent Implementation (`src/agents/`):**
```python
# Current: Custom BaseAgent with manual OpenAI calls
class BaseAgent(ABC):
    def __init__(self, name, instructions, tools):
        self.name = name
        self.instructions = instructions
        self._openai_client = AzureOpenAI(...)
    
    @abstractmethod
    async def run(self, task, context):
        pass
```

**Agents Implemented:**
- `base_agent.py` - Custom base class
- `orchestrator_agent.py` - Manual orchestration logic
- `market_data_agent.py` - Market data queries
- `news_sentiment_agent.py` - News analysis
- `fundamental_analysis_agent.py` - Financial analysis
- `risk_assessment_agent.py` - Risk metrics
- `router_agent.py` - Query routing
- `synthesis_agent.py` - Response generation

**Missing:**
- ❌ Semantic Kernel agent framework integration
- ❌ Microsoft Agent Framework orchestration patterns
- ❌ Agent-to-Agent (A2A) protocol
- ❌ Model Context Protocol (MCP) for tools
- ❌ OpenTelemetry observability
- ❌ Structured input/output handling
- ❌ Deterministic multi-agent workflows

---

## Target State: Semantic Kernel Implementation

### New Architecture Pattern

```python
# Target: Semantic Kernel ChatCompletionAgent
from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.agents import SequentialOrchestration, ConcurrentOrchestration
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

# Create kernel with Azure OpenAI
kernel = Kernel()
kernel.add_service(
    AzureChatCompletion(
        deployment_name="gpt-4",
        endpoint=endpoint,
        api_key=api_key
    )
)

# Define agents using Semantic Kernel
market_agent = ChatCompletionAgent(
    service_id="azure_openai",
    kernel=kernel,
    name="MarketDataAgent",
    instructions="You analyze market data and technical indicators..."
)

# Orchestrate with built-in patterns
orchestration = SequentialOrchestration(
    members=[market_agent, sentiment_agent, risk_agent]
)
```

---

## Migration Strategy

### Phase 1: Foundation (Week 1)

**Goal:** Set up Semantic Kernel infrastructure and migrate one agent

**Tasks:**
1. ✅ **Install Semantic Kernel Python SDK**
   ```bash
   pip install semantic-kernel[azure]
   ```

2. ✅ **Create Semantic Kernel configuration**
   - Update `src/agents/config.py` to include Kernel setup
   - Configure Azure OpenAI service connection
   - Set up Redis for semantic caching

3. ✅ **Migrate Market Data Agent**
   - Convert `market_data_agent.py` to use `ChatCompletionAgent`
   - Implement tools using Semantic Kernel plugins
   - Add semantic caching for queries

4. ✅ **Implement Basic Orchestration**
   - Create simple sequential workflow
   - Test end-to-end execution
   - Validate Redis integration

**Deliverables:**
- Working Semantic Kernel setup
- One migrated agent (Market Data)
- Basic orchestration example
- Integration tests

---

### Phase 2: Agent Migration (Weeks 2-3)

**Goal:** Migrate all specialized agents to Semantic Kernel

**Agent Migration Order:**

1. **Market Data Agent** ✅ (Phase 1)
   - Pattern: ChatCompletionAgent with TimeSeries tools
   - Tools: Get stock prices, calculate indicators, query Redis TimeSeries

2. **News Sentiment Agent**
   - Pattern: ChatCompletionAgent with vector search
   - Tools: Search news embeddings, analyze sentiment, cache results

3. **Fundamental Analysis Agent**
   - Pattern: ChatCompletionAgent with RAG
   - Tools: Search SEC filings, analyze financials, extract ratios

4. **Risk Assessment Agent**
   - Pattern: ChatCompletionAgent with Featureform integration
   - Tools: Calculate VaR, fetch risk metrics, check thresholds

5. **Technical Analysis Agent**
   - Pattern: ChatCompletionAgent with indicators
   - Tools: Calculate patterns, identify signals, trend analysis

6. **Portfolio Management Agent**
   - Pattern: ChatCompletionAgent with state management
   - Tools: Track positions, rebalance, optimize allocation

7. **Report Generation Agent**
   - Pattern: ChatCompletionAgent with structured output
   - Tools: Format reports, generate summaries, create visualizations

**Migration Template for Each Agent:**

```python
# Step 1: Define agent instructions
instructions = """
You are the [Agent Name] for FinagentiX.
Your role: [Specific responsibilities]
You have access to: [List tools]
Always: [Best practices]
"""

# Step 2: Create Semantic Kernel plugins for tools
from semantic_kernel.functions import kernel_function

class MarketDataPlugin:
    @kernel_function(
        name="get_stock_price",
        description="Get current or historical stock price"
    )
    async def get_stock_price(self, ticker: str, date: str = None) -> dict:
        # Tool implementation with Redis caching
        pass

# Step 3: Create agent with plugins
agent = ChatCompletionAgent(
    service_id="azure_openai",
    kernel=kernel,
    name="MarketDataAgent",
    instructions=instructions,
    plugins=[MarketDataPlugin()]
)

# Step 4: Add semantic caching wrapper
async def run_with_cache(agent, task):
    # Check semantic cache
    cached = check_semantic_cache(task)
    if cached:
        return cached
    
    # Run agent
    result = await agent.invoke(task)
    
    # Store in cache
    store_in_cache(task, result)
    return result
```

**Deliverables:**
- All 7 agents migrated to Semantic Kernel
- Tool plugins implemented for each agent
- Semantic caching integrated
- Unit tests for each agent

---

### Phase 3: Orchestration Patterns (Week 4)

**Goal:** Implement Microsoft-recommended orchestration patterns

#### 3.1 Sequential Orchestration

**Use Case:** Investment analysis workflow (market → fundamentals → risk → recommendation)

```python
from semantic_kernel.agents import SequentialOrchestration

# Define workflow
investment_workflow = SequentialOrchestration(
    members=[
        market_data_agent,      # Step 1: Get market data
        fundamental_agent,      # Step 2: Analyze financials
        risk_assessment_agent,  # Step 3: Calculate risk
        synthesis_agent         # Step 4: Generate recommendation
    ]
)

# Execute
result = await investment_workflow.invoke(
    task="Should I invest in AAPL?",
    runtime=runtime
)
```

#### 3.2 Concurrent Orchestration

**Use Case:** Parallel data gathering (market data + news + SEC filings simultaneously)

```python
from semantic_kernel.agents import ConcurrentOrchestration

# Run agents in parallel
parallel_analysis = ConcurrentOrchestration(
    members=[
        market_data_agent,
        news_sentiment_agent,
        fundamental_agent
    ]
)

# All agents execute simultaneously
results = await parallel_analysis.invoke(
    task="Gather all data for AAPL",
    runtime=runtime
)
```

#### 3.3 Handoff Orchestration

**Use Case:** Dynamic routing based on query type

```python
from semantic_kernel.agents import HandoffOrchestration

# Define handoff rules
handoffs = {
    "market": market_data_agent,
    "news": news_sentiment_agent,
    "risk": risk_assessment_agent,
    "general": synthesis_agent
}

# Agent decides who handles the query
dynamic_workflow = HandoffOrchestration(
    manager=router_agent,
    handoff_map=handoffs
)
```

#### 3.4 Group Chat Orchestration

**Use Case:** Collaborative analysis with multiple perspectives

```python
from semantic_kernel.agents import GroupChatOrchestration

# All agents collaborate
group_analysis = GroupChatOrchestration(
    members=[
        market_data_agent,
        news_sentiment_agent,
        fundamental_agent,
        risk_assessment_agent
    ],
    manager=orchestrator_agent  # Coordinates discussion
)
```

#### 3.5 Magentic Orchestration

**Use Case:** Complex, multi-step tasks with adaptive planning

```python
from semantic_kernel.agents import MagenticOrchestration

# Manager dynamically selects agents
adaptive_workflow = MagenticOrchestration(
    manager=orchestrator_agent,  # AI manager
    members=[
        market_data_agent,
        news_sentiment_agent,
        fundamental_agent,
        risk_assessment_agent,
        technical_analysis_agent,
        portfolio_agent,
        report_agent
    ]
)

# Manager adapts workflow based on task complexity
result = await adaptive_workflow.invoke(
    task="Analyze AAPL for Q4 2024 earnings impact on portfolio",
    runtime=runtime
)
```

**Deliverables:**
- All 5 orchestration patterns implemented
- Routing logic for query type detection
- Manager agent for Magentic pattern
- Integration tests for each pattern

---

### Phase 4: Advanced Features (Week 5)

**Goal:** Add enterprise-grade features

#### 4.1 OpenTelemetry Observability

```python
from opentelemetry import trace
from semantic_kernel.connectors.telemetry import ApplicationInsightsTelemetry

# Configure tracing
tracer = trace.get_tracer("finagentix.agents")

# Add to kernel
kernel.add_telemetry(ApplicationInsightsTelemetry(
    connection_string=app_insights_connection
))

# Automatic tracing for all agent calls
with tracer.start_as_current_span("investment_analysis"):
    result = await orchestration.invoke(task)
```

#### 4.2 Structured Input/Output

```python
from pydantic import BaseModel

# Define structured input
class InvestmentQuery(BaseModel):
    ticker: str
    analysis_type: str
    risk_tolerance: str

# Define structured output
class InvestmentRecommendation(BaseModel):
    action: str  # BUY, SELL, HOLD
    confidence: float
    reasoning: list[str]
    risk_level: str

# Use in orchestration
result = await orchestration.invoke(
    task=InvestmentQuery(
        ticker="AAPL",
        analysis_type="comprehensive",
        risk_tolerance="moderate"
    ),
    output_type=InvestmentRecommendation
)
```

#### 4.3 Human-in-the-Loop

```python
from semantic_kernel.agents import DurableOrchestration

# Orchestration can pause for human approval
async def investment_approval_workflow(context):
    # Step 1: AI analysis
    analysis = await market_agent.invoke(task)
    
    # Step 2: Pause for human review
    human_input = await context.wait_for_approval(analysis)
    
    # Step 3: Continue based on approval
    if human_input.approved:
        return await execute_trade(analysis)
    else:
        return {"status": "rejected", "reason": human_input.feedback}
```

#### 4.4 Model Context Protocol (MCP)

```python
# Tools implement MCP for interoperability
from semantic_kernel.connectors.mcp import MCPToolPlugin

# Redis tools exposed via MCP
redis_mcp_tools = MCPToolPlugin(
    server_url="mcp://redis-tools",
    tools=["timeseries_query", "vector_search", "cache_get"]
)

kernel.add_plugin(redis_mcp_tools)
```

**Deliverables:**
- OpenTelemetry integration with Application Insights
- Structured data handling for all agents
- Human approval workflows for high-stakes decisions
- MCP-compliant tool implementations

---

### Phase 5: Deployment & Production (Week 6)

**Goal:** Deploy to Azure Container Apps with full observability

#### 5.1 Container Apps Deployment

```yaml
# infra/stages/stage5-agent-runtime.bicep
resource agentRuntime 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'agents-${resourceToken}'
  properties:
    configuration:
      ingress: {
        external: true
        targetPort: 8000
      }
    template:
      containers: [
        {
          name: 'agent-api'
          image: 'acr${resourceToken}.azurecr.io/finagentix-agents:latest'
          env: [
            { name: 'REDIS_HOST', value: redisHost }
            { name: 'AZURE_OPENAI_ENDPOINT', value: openaiEndpoint }
            { name: 'FEATUREFORM_URL', value: featureformUrl }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
      }
    }
}
```

#### 5.2 FastAPI Integration

```python
# src/api/main.py
from fastapi import FastAPI
from semantic_kernel.agents.runtime import InProcessRuntime

app = FastAPI()
runtime = InProcessRuntime()
runtime.start()

@app.post("/analyze")
async def analyze(query: InvestmentQuery):
    result = await investment_workflow.invoke(
        task=query,
        runtime=runtime
    )
    return result.get(timeout=30)
```

#### 5.3 Monitoring Dashboard

```python
# Application Insights custom metrics
from opencensus.ext.azure import metrics_exporter

exporter = metrics_exporter.new_metrics_exporter(
    connection_string=app_insights_connection
)

# Track agent performance
exporter.track_metric("agent.latency", latency_ms)
exporter.track_metric("agent.cache_hit_rate", cache_hit_rate)
exporter.track_metric("agent.cost_savings", cost_saved)
```

**Deliverables:**
- Azure Container Apps deployment
- FastAPI REST API
- Application Insights monitoring
- Load testing results (1000+ req/sec)
- Cost analysis and optimization

---

## Migration Checklist

### Pre-Migration
- [ ] Review Microsoft Agent Framework documentation
- [ ] Install Semantic Kernel Python SDK
- [ ] Update requirements.txt with semantic-kernel[azure]
- [ ] Create migration branch in Git

### Phase 1: Foundation
- [ ] Configure Semantic Kernel Kernel
- [ ] Set up Azure OpenAI service connection
- [ ] Migrate Market Data Agent
- [ ] Implement basic sequential orchestration
- [ ] Create integration tests

### Phase 2: Agent Migration
- [ ] Migrate News Sentiment Agent
- [ ] Migrate Fundamental Analysis Agent
- [ ] Migrate Risk Assessment Agent
- [ ] Migrate Technical Analysis Agent
- [ ] Migrate Portfolio Management Agent
- [ ] Migrate Report Generation Agent
- [ ] Update Orchestrator Agent for Semantic Kernel

### Phase 3: Orchestration
- [ ] Implement Sequential Orchestration
- [ ] Implement Concurrent Orchestration
- [ ] Implement Handoff Orchestration
- [ ] Implement Group Chat Orchestration
- [ ] Implement Magentic Orchestration
- [ ] Add routing logic for query classification

### Phase 4: Advanced Features
- [ ] Integrate OpenTelemetry
- [ ] Add structured input/output
- [ ] Implement human-in-the-loop patterns
- [ ] Add MCP tool interfaces
- [ ] Configure Application Insights

### Phase 5: Deployment
- [ ] Create Container Apps Bicep templates
- [ ] Build FastAPI REST API
- [ ] Deploy to Azure Container Apps
- [ ] Configure monitoring and alerts
- [ ] Load testing and optimization
- [ ] Update documentation

### Post-Migration
- [ ] Remove legacy custom agent code
- [ ] Archive old implementations
- [ ] Update README with new architecture
- [ ] Train team on Semantic Kernel patterns
- [ ] Create runbooks for operations

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Semantic Kernel API changes | Medium | Pin to stable version, monitor releases |
| Performance regression | High | Benchmark before/after, optimize caching |
| Redis integration issues | Medium | Keep existing Redis patterns, add SK caching |
| Azure OpenAI rate limits | High | Implement exponential backoff, use semantic cache |

### Business Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Extended migration timeline | Medium | Phased rollout, feature flags for gradual migration |
| User experience disruption | High | Maintain backward compatibility during migration |
| Cost increase | Medium | Monitor costs closely, optimize agent calls |

---

## Success Metrics

### Technical Metrics
- ✅ **Response Time:** < 2 seconds (P95)
- ✅ **Cache Hit Rate:** > 80%
- ✅ **LLM Cost Reduction:** 30-70% via semantic caching
- ✅ **Throughput:** 1000+ req/sec
- ✅ **Error Rate:** < 0.1%

### Business Metrics
- ✅ **Agent Accuracy:** > 95% for financial analysis
- ✅ **User Satisfaction:** > 4.5/5
- ✅ **Query Resolution Rate:** > 90% without human intervention
- ✅ **Cost per Query:** < $0.01

---

## Resources

### Official Documentation
- [Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/)
- [Semantic Kernel Agent Framework](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/)
- [Agent Orchestration Patterns](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/)
- [Azure Architecture: Multi-Agent Workflow Automation](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/idea/multiple-agent-workflow-automation)

### Code Samples
- [Semantic Kernel Python Samples](https://github.com/microsoft/semantic-kernel/tree/main/python/samples/getting_started_with_agents)
- [Agent Framework Samples](https://github.com/microsoft/agent-framework/tree/main/workflow-samples)

### Training Materials
- [Build AI Agents with Microsoft Agent Framework](https://learn.microsoft.com/en-us/training/)
- [Semantic Kernel for Python Developers](https://learn.microsoft.com/en-us/semantic-kernel/)

---

## Next Steps

1. **Immediate (This Week):**
   - Review and approve migration plan
   - Install Semantic Kernel SDK
   - Create development branch
   - Start Phase 1 implementation

2. **Short-term (Next 2 Weeks):**
   - Complete Phase 1 (Foundation)
   - Begin Phase 2 (Agent Migration)
   - Set up monitoring infrastructure

3. **Medium-term (Next Month):**
   - Complete all agent migrations
   - Implement orchestration patterns
   - Deploy to Container Apps staging environment

4. **Long-term (Next Quarter):**
   - Production deployment
   - Performance optimization
   - Advanced features (MCP, structured data)
   - Team training and documentation

---

**Document Owner:** FinagentiX Development Team  
**Last Updated:** December 10, 2024  
**Next Review:** January 10, 2025
