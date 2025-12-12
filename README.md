# FinagentiX

**AI-Powered Financial Trading Assistant**

A production-grade multi-agent AI system that provides real-time financial market analysis, risk assessment, and trading recommendations.

## 🚀 Quick Start

**New to FinagentiX?** → [How It Works](HOW_IT_WORKS.md) - Simple step-by-step explanation

FinagentiX combines cutting-edge technologies to deliver intelligent trading insights:

- **30-70% LLM cost savings** through Redis semantic caching
- **Sub-millisecond feature serving** with Featureform + Redis
- **Real-time market analysis** with <2 second response times
- **137x cheaper than LLM on-cloud** for cached queries

> **Important:** This project requires **Azure Managed Redis** with Enterprise tier SKUs (NOT Azure Cache for Redis). Azure Managed Redis includes the Redis modules (RediSearch, RedisTimeSeries, RedisJSON, RedisBloom) needed for this architecture.

## 🏗️ Architecture

Built on the **Redis AI Vision** with five core layers:

1. **Semantic Routing & Caching** - Intelligent query routing and LLM response caching (30-70% cost savings)
2. **Contextual Memory** - User preferences, portfolio state, conversation history (~53% memory savings)
3. **Semantic Routing** - Direct workflow routing without LLM orchestrator
4. **Tool Cache** - Agent tool output caching for faster workflows
5. **RAG/Document Search** - Q&A on SEC filings (10-K, 10-Q), earnings, news via vector search (<10ms retrieval)

See [System Architecture](docs/architecture/ARCHITECTURE.md) for complete details.

## 🚀 Deployment

### Quick Deploy (Automated)

```bash
# Set environment and location
export AZURE_ENV_NAME=dev
export AZURE_LOCATION=westus3

# Full deployment (includes prompts for Featureform definitions)
./infra/scripts/deploy-full.sh
```

The deployment will:
1. Create resource group and foundation (VNet, DNS, Monitoring)
2. Deploy Storage Account with private endpoint
3. Deploy Redis Enterprise (takes ~7 minutes)
4. Deploy Azure OpenAI
5. Deploy Featureform Container App
6. Deploy Debug VM with public IP
7. **Prompt to apply Featureform definitions automatically**

### Manual Deployment Steps

```bash
# 1. Deploy infrastructure stages
export AZURE_ENV_NAME=dev
./infra/scripts/deploy.sh

# 2. Deploy Featureform
./infra/scripts/deploy-featureform.sh

# 3. Deploy Debug VM (for VNet access)
./infra/scripts/deploy-debug-vm.sh

# 4. Apply Featureform definitions (automated)
./infra/scripts/connect-and-apply.sh
```

### Cleanup

```bash
# Delete all resources
export AZURE_ENV_NAME=dev
./infra/scripts/cleanup.sh

# Skip confirmation prompt
export SKIP_CONFIRM=1
./infra/scripts/cleanup.sh
```

## 📚 Documentation

### Architecture
- **[System Architecture](docs/architecture/ARCHITECTURE.md)** - Complete system architecture and Redis AI Vision integration
- **[Redis Integration](docs/architecture/REDIS_INTEGRATION.md)** - Detailed Redis implementation patterns with code examples
- **[Data Pipeline](docs/architecture/DATA_PIPELINE.md)** - Data ingestion and storage architecture
- **[Data Pipeline Quick Reference](docs/architecture/DATA_PIPELINE_QUICKREF.md)** - Quick reference guide

### Infrastructure
- **[Infrastructure Overview](docs/infrastructure/INFRASTRUCTURE.md)** - Complete Azure infrastructure components and design
- **[Deployment Stages](docs/infrastructure/DEPLOYMENT_STAGES.md)** - Modular staged deployment (deploy independently or together)

## 🤖 AI Agents

- **Orchestrator Agent** - Coordinates multi-agent workflows
- **Market Data Agent** - Real-time price feeds and historical data
- **Technical Analysis Agent** - RSI, MACD, Bollinger Bands, patterns
- **Sentiment Agent** - News and social media sentiment analysis
- **Risk Assessment Agent** - VaR, portfolio risk, position sizing
- **Portfolio Management Agent** - Position tracking and rebalancing
- **News & Research Agent** - Document Q&A via RAG
- **Report Generation Agent** - Trading reports and summaries

## 💼 Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent Framework | Microsoft Agentic Framework |
| LLM | Azure OpenAI (GPT-4) |
| Feature Store | Featureform (Redis-backed) |
| Cache & Memory | Azure Managed Redis |
| Vector Search | RediSearch (HNSW) |
| Time-Series | RedisTimeSeries |
| API | FastAPI + WebSocket |
| Language | Python 3.11+ |

## 📊 Implementation Phases

- **Phase 1:** Foundation - Redis setup, semantic caching, contextual memory
- **Phase 2:** Agent Layer - Core agents and orchestration
- **Phase 3:** Featureform Integration - Feature store and serving
- **Phase 4:** RAG & Knowledge Base - Document indexing and Q&A
- **Phase 5:** Advanced Agents - Risk, portfolio, reporting
- **Phase 6:** Production & Optimization - Load testing, monitoring

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed phase breakdown.

## 🎯 Success Metrics

| Metric | Target |
|--------|--------|
| LLM Cost Reduction | 30-70% |
| Response Time | <2 seconds |
| Cache Hit Rate | >80% |
| Feature Serving | <1ms |
| Throughput | 1000+ req/sec |
| Uptime | >99.9% |

## 📚 Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Complete system architecture and implementation plan
- [SUMMARY.md](./SUMMARY.md) - Workshop and training materials

## 🔒 Security

- TLS 1.3 encryption (at-rest and in-transit)
- Azure AD integration
- RBAC for Redis access
- Audit logging for all actions
- SEC compliance for trading recommendations

---

**Status:** Phase 1 - Foundation Planning  
**Last Updated:** December 5, 2025
