# Staged Infrastructure Deployment for FinagentiX

## 🎯 Overview

This document defines a **modular, staged deployment architecture** where each stage can be deployed independently or all together. This allows:

- **Cost optimization** - Deploy only what you need during development
- **Reusability** - Reuse foundation stages (Redis, OpenAI) for other projects
- **Flexibility** - Add/remove stages without affecting others
- **Incremental development** - Deploy data pipeline first, add agents later

---

## 📦 Deployment Stages

### Stage 0: Foundation (Networking & Shared Resources)

**Purpose:** Core networking and shared infrastructure

**Resources:**
- Resource Group
- Virtual Network (VNet) with subnets
- Private DNS Zones
- Network Security Groups (NSG)
- Log Analytics Workspace
- Application Insights

**Cost:** ~$10-30/month (mostly logging)

**Deploy Command:**
```bash
azd deploy stage-foundation
```

**Bicep Module:** `infra/stages/stage0-foundation.bicep`

**Why separate?**
- Networking is shared by all stages
- Other projects can use the same VNet
- Logging infrastructure is reusable

**Dependencies:** None

---

### Stage 1: Data Platform (Redis + Storage)

**Purpose:** Core data storage infrastructure

**Resources:**
- **Azure Managed Redis** (E5 or E10)
  - ⚠️ **NOT** "Azure Cache for Redis"
  - ✅ Enterprise tier SKUs include RediSearch, RedisTimeSeries, RedisJSON, RedisBloom
  - Service: `Microsoft.Cache/redisEnterprise`
- Azure Storage Account (for document archives)
- Private Endpoints for Redis
- Private Endpoints for Storage

**Cost:** ~$225-450/month (Redis E5/E10) + ~$1/month (Storage)

**Deploy Command:**
```bash
azd deploy stage-data-platform
```

**Bicep Module:** `infra/stages/stage1-data-platform.bicep`

**Why separate?**
- **Reusable for other projects** - Any project needing Redis + Storage
- Redis is the most expensive component (~90% of total cost)
- Can pause Redis when not developing
- Storage is cheap, keep it running

**Dependencies:** Stage 0 (Foundation)

**What it enables:**
- Direct Redis access for development/testing
- Store documents in Azure Blob
- No compute costs yet

---

### Stage 2: AI Services (Azure OpenAI)

**Purpose:** LLM and embeddings generation

**Resources:**
- Azure OpenAI Service
- GPT-4 model deployment
- text-embedding-3-large deployment
- Private Endpoint for OpenAI

**Cost:** ~$50-200/month (usage-based)

**Deploy Command:**
```bash
azd deploy stage-ai-services
```

**Bicep Module:** `infra/stages/stage2-ai-services.bicep`

**Why separate?**
- **Reusable for other AI projects** - Not specific to FinagentiX
- Can share one OpenAI instance across multiple projects
- Usage-based billing (only pay when called)
- Some projects might not need AI (just Redis)

**Dependencies:** Stage 0 (Foundation)

**What it enables:**
- Generate embeddings for documents
- LLM completions for agents
- Sentiment analysis

---

### Stage 3: Data Ingestion Pipeline

**Purpose:** One-time batch data load infrastructure

**Resources:**
- Azure Container Registry (ACR)
- Container App: Data Ingestion Service
- Managed Identity for Container App
- Environment variables configuration

**Cost:** ~$5/month (ACR) + ~$0-10/month (Container App, scales to 0)

**Deploy Command:**
```bash
azd deploy stage-data-ingestion
```

**Bicep Module:** `infra/stages/stage3-data-ingestion.bicep`

**Why separate?**
- **Run once, then delete** - Save costs after data load
- Independent lifecycle from agents
- Can re-deploy just this stage to re-run ingestion
- No need to keep running after data is loaded

**Dependencies:** 
- Stage 0 (Foundation)
- Stage 1 (Data Platform - Redis + Storage)
- Stage 2 (AI Services - for embeddings)

**What it enables:**
- Run batch data ingestion (yfinance, NewsAPI, SEC EDGAR)
- Generate embeddings for documents
- Populate Redis with historical data
- Store raw documents in Azure Blob

**Lifecycle:**
1. Deploy stage
2. Run ingestion job (1-2 hours + 2-3 days for news)
3. Verify data in Redis
4. **Delete stage** to save costs
5. Re-deploy later if you need to refresh data

---

### Stage 4: Agent Runtime (Production Agents)

**Purpose:** Run AI agents and serve API

**Resources:**
- Container App: Agent API Service (FastAPI)
- Auto-scaling configuration (1-10 replicas)
- HTTPS ingress with custom domain (optional)
- Managed Identity for Container App

**Cost:** ~$20-50/month (depends on usage, scales to 0)

**Deploy Command:**
```bash
azd deploy stage-agent-runtime
```

**Bicep Module:** `infra/stages/stage4-agent-runtime.bicep`

**Why separate?**
- **Deploy only when agents are ready** - Not needed during data pipeline dev
- Independent scaling from data ingestion
- Can update agent code without touching data platform
- Can delete when not actively using agents (dev/demo)

**Dependencies:**
- Stage 0 (Foundation)
- Stage 1 (Data Platform - Redis with data)
- Stage 2 (AI Services - for agent reasoning)

**What it enables:**
- REST API for agent interactions
- WebSocket for real-time updates
- Microsoft Agentic Framework execution
- Featureform feature serving

**When to deploy:**
- After data ingestion is complete (Stage 3)
- When you want to test agents
- For production use

---

## 🚀 Deployment Scenarios

### Scenario 1: Full Development Environment

Deploy everything for complete system:

```bash
# Deploy all stages at once
azd deploy --all

# Or deploy sequentially
azd deploy stage-foundation
azd deploy stage-data-platform
azd deploy stage-ai-services
azd deploy stage-data-ingestion
azd deploy stage-agent-runtime
```

**Total Cost:** ~$320-750/month (depending on Redis tier)

---

### Scenario 2: Data Pipeline Only (Initial Development)

Just load data, no agents yet:

```bash
# Deploy minimal for data ingestion
azd deploy stage-foundation       # Networking
azd deploy stage-data-platform    # Redis + Storage
azd deploy stage-ai-services      # OpenAI (for embeddings)
azd deploy stage-data-ingestion   # Ingestion service

# After data is loaded, delete ingestion service
azd down stage-data-ingestion
```

**Cost during ingestion:** ~$285-510/month  
**Cost after ingestion:** ~$275-500/month (no ingestion service)

---

### Scenario 3: Reuse Redis for Other Projects

Use the same Redis instance for multiple projects:

```bash
# Deploy foundation + data platform once
azd deploy stage-foundation
azd deploy stage-data-platform

# Project A: FinagentiX agents
azd deploy stage-ai-services --project finagentix
azd deploy stage-agent-runtime --project finagentix

# Project B: Different app using same Redis
azd deploy stage-agent-runtime --project other-app
```

**Shared cost:** Redis + Networking (~$235-460/month)  
**Per-project cost:** OpenAI + Container Apps (~$70-150/month each)

---

### Scenario 4: Cost-Optimized Development

Minimize costs during development:

```bash
# Deploy minimal stack
azd deploy stage-foundation       # Always needed
azd deploy stage-data-platform    # Use E5 Redis ($225/month)

# Only deploy other stages when actively working
azd deploy stage-ai-services      # Deploy when testing embeddings
azd deploy stage-agent-runtime    # Deploy when testing agents

# Tear down when not working
azd down stage-agent-runtime      # Saves ~$50/month
azd down stage-ai-services        # Saves OpenAI costs
# Keep Redis + Foundation running for data persistence
```

**Minimum cost:** ~$235-265/month (Foundation + Redis E5)  
**Add stages as needed:** +$50-200/month per stage

---

### Scenario 5: Production Deployment

Full production with all stages:

```bash
# Deploy everything (use E10 Redis for production)
azd deploy --all --environment prod

# Production configuration:
# - Redis E10 (12GB, HA)
# - Auto-scaling agents (1-10 replicas)
# - Private endpoints only
# - Enhanced monitoring
```

**Cost:** ~$545-750/month

---

## 📋 Stage Dependencies

```
Stage 0: Foundation (Networking, Logging)
    ├── Stage 1: Data Platform (Redis, Storage)
    │       └── Stage 3: Data Ingestion ─┐
    │                                     │
    └── Stage 2: AI Services (OpenAI)    │
            └──────────────────────┬──────┘
                                   │
                        Stage 4: Agent Runtime
```

**Key:**
- Stage 0 is required by all other stages
- Stage 1 & 2 are independent of each other
- Stage 3 requires Stages 0, 1, and 2
- Stage 4 requires Stages 0, 1, and 2

---

## 🗂️ Bicep File Structure

```
infra/
├── main.bicep                          # Orchestrator (deploys all stages)
├── main.parameters.json                # Global parameters
├── stages/
│   ├── stage0-foundation.bicep         # Networking, logging
│   ├── stage0-foundation.parameters.json
│   ├── stage1-data-platform.bicep      # Redis, Storage
│   ├── stage1-data-platform.parameters.json
│   ├── stage2-ai-services.bicep        # Azure OpenAI
│   ├── stage2-ai-services.parameters.json
│   ├── stage3-data-ingestion.bicep     # Ingestion Container App
│   ├── stage3-data-ingestion.parameters.json
│   ├── stage4-agent-runtime.bicep      # Agent API Container App
│   └── stage4-agent-runtime.parameters.json
├── modules/                            # Reusable Bicep modules
│   ├── networking.bicep
│   ├── redis.bicep
│   ├── openai.bicep
│   ├── storage.bicep
│   ├── container-apps.bicep
│   ├── container-registry.bicep
│   └── monitoring.bicep
└── scripts/
    ├── deploy-stage.sh                 # Helper script for stage deployment
    └── delete-stage.sh                 # Helper script for stage deletion
```

---

## 🔧 Azure.yaml Configuration

```yaml
name: finagentix
metadata:
  template: finagentix-template

# Default deployment deploys all stages
services:
  stage-foundation:
    project: ./infra/stages/stage0-foundation.bicep
    language: bicep
    host: azd
  
  stage-data-platform:
    project: ./infra/stages/stage1-data-platform.bicep
    language: bicep
    host: azd
    dependsOn:
      - stage-foundation
  
  stage-ai-services:
    project: ./infra/stages/stage2-ai-services.bicep
    language: bicep
    host: azd
    dependsOn:
      - stage-foundation
  
  stage-data-ingestion:
    project: ./infra/stages/stage3-data-ingestion.bicep
    language: bicep
    host: azd
    dependsOn:
      - stage-foundation
      - stage-data-platform
      - stage-ai-services
  
  stage-agent-runtime:
    project: ./infra/stages/stage4-agent-runtime.bicep
    language: bicep
    host: azd
    dependsOn:
      - stage-foundation
      - stage-data-platform
      - stage-ai-services
```

---

## 💡 Stage Management Commands

### Deploy Specific Stage
```bash
azd deploy stage-foundation
azd deploy stage-data-platform
azd deploy stage-data-ingestion
```

### Deploy Multiple Stages
```bash
azd deploy stage-foundation stage-data-platform stage-ai-services
```

### Deploy All Stages
```bash
azd deploy --all
# or
azd up
```

### Delete Specific Stage
```bash
azd down stage-data-ingestion
```

### Delete All Stages
```bash
azd down --purge
```

### Check Stage Status
```bash
azd show stage-data-platform
azd show --all
```

---

## 🎯 Recommended Development Workflow

### Week 1: Infrastructure Setup
```bash
# Day 1: Deploy foundation
azd deploy stage-foundation

# Day 2: Deploy data platform (start with E5)
azd deploy stage-data-platform --parameters redisSku=E5

# Day 3: Deploy AI services
azd deploy stage-ai-services
```

### Week 2: Data Ingestion
```bash
# Day 4: Deploy ingestion service
azd deploy stage-data-ingestion

# Day 5-7: Run data ingestion (2-3 days for NewsAPI rate limits)
# Monitor logs: azd logs stage-data-ingestion

# Day 8: Verify data in Redis, then delete ingestion service
azd down stage-data-ingestion
```

### Week 3-4: Agent Development
```bash
# Day 9: Deploy agent runtime
azd deploy stage-agent-runtime

# Day 10-20: Develop and test agents
# Logs: azd logs stage-agent-runtime

# When not actively developing (evenings/weekends):
azd down stage-agent-runtime    # Save costs
azd deploy stage-agent-runtime  # Redeploy when working again
```

### Week 5+: Production Preparation
```bash
# Upgrade to production Redis
azd deploy stage-data-platform --parameters redisSku=E10

# Deploy production agent runtime with scaling
azd deploy stage-agent-runtime --parameters minReplicas=2 maxReplicas=10
```

---

## 💰 Cost Breakdown by Stage

| Stage | Resources | Monthly Cost | Can Delete? |
|-------|-----------|--------------|-------------|
| **Stage 0: Foundation** | VNet, NSG, Logging | $10-30 | No (shared) |
| **Stage 1: Data Platform** | Redis E5/E10, Storage | $225-450 | No (data loss) |
| **Stage 2: AI Services** | Azure OpenAI | $50-200 | Yes (usage-based) |
| **Stage 3: Data Ingestion** | ACR, Container App | $5-15 | **Yes (after data load)** |
| **Stage 4: Agent Runtime** | Container App | $20-50 | **Yes (when not using)** |
| **TOTAL (all stages)** | | **$320-750/month** | |
| **Minimum (Stage 0+1)** | | **$235-480/month** | |

**Cost Optimization:**
- Keep Stage 0 + 1 running (Foundation + Data Platform)
- Deploy/delete Stage 3 as needed (one-time ingestion)
- Deploy/delete Stage 4 when actively developing/using agents
- Stage 2 is usage-based (only pay for actual API calls)

---

## ✅ Stage Deployment Checklist

### Stage 0: Foundation
- [ ] VNet created with correct address space
- [ ] All subnets created
- [ ] Private DNS zones configured
- [ ] NSG rules applied
- [ ] Log Analytics Workspace created

### Stage 1: Data Platform
- [ ] Azure Managed Redis cluster created
- [ ] Redis modules enabled (Search, TimeSeries, JSON, Bloom)
- [ ] Redis accessible via private endpoint
- [ ] Storage Account created
- [ ] Storage containers created (sec-filings, news-articles)
- [ ] Test Redis connection: `redis-cli PING`

### Stage 2: AI Services
- [ ] Azure OpenAI account created
- [ ] GPT-4 model deployed
- [ ] Embedding model deployed
- [ ] Private endpoint configured
- [ ] Test API: `curl $OPENAI_ENDPOINT/openai/deployments`

### Stage 3: Data Ingestion
- [ ] Container Registry created
- [ ] Ingestion Docker image built and pushed
- [ ] Container App deployed
- [ ] Environment variables configured
- [ ] Test ingestion: Check logs for successful data fetching

### Stage 4: Agent Runtime
- [ ] Agent API Docker image built and pushed
- [ ] Container App deployed with auto-scaling
- [ ] HTTPS ingress configured
- [ ] Test API endpoint: `curl $API_URL/health`
- [ ] Test agent query: `curl $API_URL/query`

---

## 🔄 Re-deployment Scenarios

### Scenario: Refresh Data
```bash
# Re-deploy ingestion stage
azd deploy stage-data-ingestion

# Run ingestion job
# Monitor progress

# Delete stage after completion
azd down stage-data-ingestion
```

### Scenario: Update Agent Code
```bash
# Update code in src/api/
# Rebuild and redeploy stage 4 only
azd deploy stage-agent-runtime

# No need to redeploy other stages
```

### Scenario: Upgrade Redis
```bash
# Update Redis SKU in parameters
azd deploy stage-data-platform --parameters redisSku=E10

# Other stages are not affected
```

---

## 🎯 Summary

**Key Benefits of Staged Deployment:**

1. **Cost Control** - Pay only for what you're using
2. **Reusability** - Share Redis/OpenAI across projects
3. **Flexibility** - Deploy/delete stages independently
4. **Development Speed** - Test incrementally
5. **Production Ready** - Same stages scale to production

**Next Steps:**
1. Review stage definitions
2. Create Bicep templates for each stage
3. Configure azure.yaml for staged deployment
4. Deploy Stage 0 (Foundation)
5. Deploy Stage 1 (Data Platform)
6. Test Redis connectivity
7. Deploy remaining stages as needed

---

**Document Version:** 1.0  
**Last Updated:** December 5, 2025  
**Status:** Ready for Bicep implementation
