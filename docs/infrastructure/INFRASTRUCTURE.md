# Infrastructure Setup for FinagentiX

## 🎯 Overview

This document defines the complete Azure infrastructure for FinagentiX, deployed using **Azure Developer CLI (azd)** and **Bicep** templates for full automation.

---

## 🏗️ Infrastructure Components

### 1. **Azure Managed Redis** (Core Data Platform)

> **IMPORTANT:** We use **Azure Managed Redis** (NOT "Azure Cache for Redis"). Azure Managed Redis uses the Enterprise tier SKUs (E5, E10, E20, etc.) which include RediSearch, RedisTimeSeries, RedisJSON, and RedisBloom modules required for this architecture.

**Purpose:** Primary data store for all Redis AI Vision patterns

**SKU:** `Enterprise_E10` (12GB memory)
- **Why:** Smallest Enterprise tier with all modules (TimeSeries, Search, JSON, Bloom)
- **Cost:** ~$450/month (can scale down to E5 for dev: ~$225/month)
- **Service Type:** `Microsoft.Cache/redisEnterprise` (NOT `Microsoft.Cache/Redis`)

**Modules Required:**
- ✅ **RediSearch** (Vector similarity, full-text search)
- ✅ **RedisTimeSeries** (OHLCV market data)
- ✅ **RedisJSON** (Complex objects, user context)
- ✅ **RedisBloom** (Probabilistic data structures for fraud detection)

**Configuration:**
- Clustering: Enabled (3 shards for HA)
- Geo-replication: Disabled (Phase 1)
- Persistence: AOF + RDB snapshots
- Network: Private endpoint (VNet integration)

**What it's used for:**
- Semantic caching (LLM response cache)
- Vector search (RAG for SEC filings, news)
- Time-series data (OHLCV bars, tick data)
- Feature storage (Featureform backend)
- Contextual memory (user sessions, portfolio state)
- Real-time alerts (Pub/Sub, Sorted Sets)
- Checkpoint tracking (data ingestion state)

---

### 2. **Azure OpenAI Service**

**Purpose:** LLM completions and embeddings generation

**Models Required:**
- **GPT-4** (gpt-4-1106-preview) - Agent reasoning, analysis
  - Deployment: `gpt-4-deployment`
  - Quota: 50K TPM (tokens per minute) for Phase 1
  
- **text-embedding-3-large** - Document and query embeddings
  - Deployment: `embedding-deployment`
  - Quota: 100K TPM

**Configuration:**
- Region: Same as Redis (East US or West Europe for low latency)
- Content filtering: Default (moderate)
- Network: Private endpoint (VNet integration)

**What it's used for:**
- LLM completions for agent reasoning
- Query embeddings for semantic search
- Document embeddings for RAG
- Sentiment analysis (via GPT-4)

---

### 3. **Azure Storage Account**

**Purpose:** Archive storage for raw documents and backups

**SKU:** `Standard_LRS` (Locally Redundant Storage)
- **Cost:** ~$0.02/GB/month (minimal for 10-50MB of data)

**Containers:**
- `sec-filings` - Raw SEC filing HTML/XML
- `news-articles` - News article backups
- `embeddings-backup` - Backup of Redis vector indices
- `checkpoints` - Optional checkpoint backups

**Configuration:**
- Access tier: Hot (frequent access during ingestion)
- Lifecycle management: Move to Cool after 90 days
- Network: Private endpoint (VNet integration)

**What it's used for:**
- Archive raw SEC filings (avoid re-downloading)
- Backup Redis data for disaster recovery
- Store large documents before chunking
- Compliance/audit logs

---

### 4. **Azure Container Apps** (Compute Layer)

**Purpose:** Run Python services for data ingestion and agent API

**Why Container Apps:**
- Serverless (pay per use)
- Auto-scaling (0 to N replicas)
- Integrated with VNet (private Redis access)
- KEDA-based scaling (can scale on Redis queue length)

**Container Apps:**

#### a) **Data Ingestion Service**
- **Image:** `finagentix/data-ingestion:latest`
- **Purpose:** One-time batch data load
- **Scaling:** Manual (run once)
- **Resources:** 1 vCPU, 2GB RAM
- **Environment Variables:**
  - `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
  - `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`
  - `NEWSAPI_KEY`, `YAHOO_FINANCE_DELAY`
  
#### b) **Agent API Service**
- **Image:** `finagentix/agent-api:latest`
- **Purpose:** FastAPI REST + WebSocket for agent interactions
- **Scaling:** Auto (1-10 replicas based on HTTP requests)
- **Resources:** 2 vCPU, 4GB RAM per replica
- **Environment Variables:**
  - `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
  - `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`
  - `FEATUREFORM_HOST` (Redis host)

**Configuration:**
- Ingress: HTTP/2, HTTPS only
- Session affinity: None (stateless agents)
- Network: VNet integration for private Redis access

**What it's used for:**
- Run data ingestion scripts (yfinance, NewsAPI, SEC EDGAR)
- Host FastAPI application for agent interactions
- Execute Microsoft Agentic Framework agents
- Serve Featureform features via API

---

### 5. **Azure Virtual Network (VNet)**

**Purpose:** Private network for secure component communication

**Address Space:** `10.0.0.0/16`

**Subnets:**
- `redis-subnet` (10.0.1.0/24) - Azure Managed Redis private endpoint
- `openai-subnet` (10.0.2.0/24) - Azure OpenAI private endpoint
- `storage-subnet` (10.0.3.0/24) - Storage Account private endpoint
- `container-apps-subnet` (10.0.4.0/23) - Container Apps environment

**Configuration:**
- DNS: Azure Private DNS zones for private endpoints
- NSG: Default (allow internal traffic, deny external Redis access)
- Service Endpoints: Disabled (using Private Endpoints instead)

**What it's used for:**
- Secure communication between Container Apps and Redis
- Private access to Azure OpenAI (no public internet exposure)
- Network isolation (Redis not publicly accessible)
- Compliance (all traffic within Azure backbone)

---

### 6. **Azure Container Registry (ACR)**

**Purpose:** Store Docker images for Container Apps

**SKU:** `Basic` (~$5/month)

**Repositories:**
- `finagentix/data-ingestion`
- `finagentix/agent-api`

**Configuration:**
- Admin access: Enabled (for azd deploy)
- Geo-replication: Disabled (Phase 1)
- Network: Public (Container Apps pull via Azure backbone)

**What it's used for:**
- Host Docker images built from local code
- Versioned deployments (tag with git commit SHA)
- Automated builds (future: GitHub Actions)

---

### 7. **Azure Log Analytics Workspace**

**Purpose:** Centralized logging and monitoring

**Configuration:**
- Retention: 30 days (free tier)
- Data cap: None (pay-as-you-go)

**What it logs:**
- Container Apps logs (stdout/stderr)
- Redis metrics (connections, memory, latency)
- OpenAI usage (token consumption, latency)
- Application Insights traces

**What it's used for:**
- Debug agent failures
- Monitor Redis performance
- Track OpenAI token usage and costs
- Alert on errors or performance degradation

---

### 8. **Azure Application Insights**

**Purpose:** Application performance monitoring (APM)

**Configuration:**
- Linked to Log Analytics Workspace
- Sampling: 100% (Phase 1, reduce later)

**What it monitors:**
- Agent API request latency
- Redis query performance
- OpenAI call latency and failures
- Custom events (agent decisions, cache hits)

**What it's used for:**
- Track end-to-end request traces
- Monitor semantic cache hit rate
- Alert on high OpenAI costs
- Performance dashboards

---

## 📊 Infrastructure Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      AZURE SUBSCRIPTION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  RESOURCE GROUP: rg-finagentix-dev                      │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐   │   │
│  │  │  AZURE VIRTUAL NETWORK (10.0.0.0/16)             │   │   │
│  │  │                                                   │   │   │
│  │  │  ┌────────────────┐  ┌────────────────┐          │   │   │
│  │  │  │ Redis Subnet   │  │ OpenAI Subnet  │          │   │   │
│  │  │  │ (10.0.1.0/24)  │  │ (10.0.2.0/24)  │          │   │   │
│  │  │  └───────┬────────┘  └───────┬────────┘          │   │   │
│  │  │          │                   │                   │   │   │
│  │  │  ┌───────▼────────┐  ┌───────▼────────┐          │   │   │
│  │  │  │ Redis Private  │  │ OpenAI Private │          │   │   │
│  │  │  │   Endpoint     │  │   Endpoint     │          │   │   │
│  │  │  └───────┬────────┘  └───────┬────────┘          │   │   │
│  │  │          │                   │                   │   │   │
│  │  │  ┌───────┴───────────────────┴────────┐          │   │   │
│  │  │  │  Container Apps Subnet             │          │   │   │
│  │  │  │  (10.0.4.0/23)                     │          │   │   │
│  │  │  │                                    │          │   │   │
│  │  │  │  ┌─────────────┐  ┌─────────────┐ │          │   │   │
│  │  │  │  │ Ingestion   │  │  Agent API  │ │          │   │   │
│  │  │  │  │   Service   │  │   Service   │ │          │   │   │
│  │  │  │  └─────────────┘  └─────────────┘ │          │   │   │
│  │  │  └────────────────────────────────────┘          │   │   │
│  │  └──────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐   │   │
│  │  │  Azure Managed Redis (E10)                       │   │   │
│  │  │  • RediSearch, TimeSeries, JSON, Bloom           │   │   │
│  │  └──────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐   │   │
│  │  │  Azure OpenAI Service                            │   │   │
│  │  │  • GPT-4 deployment                              │   │   │
│  │  │  • text-embedding-3-large deployment             │   │   │
│  │  └──────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐   │   │
│  │  │  Azure Storage Account                           │   │   │
│  │  │  • sec-filings container                         │   │   │
│  │  │  • news-articles container                       │   │   │
│  │  └──────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐   │   │
│  │  │  Azure Container Registry (ACR)                  │   │   │
│  │  │  • finagentix/data-ingestion:latest              │   │   │
│  │  │  • finagentix/agent-api:latest                   │   │   │
│  │  └──────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐   │   │
│  │  │  Log Analytics Workspace                         │   │   │
│  │  │  • Container logs                                │   │   │
│  │  │  • Redis metrics                                 │   │   │
│  │  │  • OpenAI usage                                  │   │   │
│  │  └──────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💰 Cost Estimation (Phase 1 - Dev)

| Resource | SKU | Monthly Cost | Notes |
|----------|-----|--------------|-------|
| **Redis Enterprise** | E10 (12GB) | $450 | Can use E5 ($225) for dev |
| **Azure OpenAI** | GPT-4 + Embeddings | $50-200 | Depends on usage, cache saves 30-70% |
| **Container Apps** | 2 services | $20-50 | Minimal usage, auto-scales to 0 |
| **Storage Account** | Standard LRS | <$1 | Only 10-50MB of data |
| **Container Registry** | Basic | $5 | Single region |
| **Log Analytics** | 30-day retention | $10-30 | ~1GB/day estimated |
| **VNet & Networking** | Private Endpoints | $10 | 3 endpoints |
| **Application Insights** | Linked to LA | Included | No extra cost |
| **TOTAL (E10)** | | **~$545-750/month** | |
| **TOTAL (E5 for dev)** | | **~$320-525/month** | Recommended for dev |

**Cost Optimization:**
- Use **E5 Redis** ($225/month) for development
- Semantic caching reduces OpenAI costs by 30-70%
- Container Apps scale to 0 when not in use
- Can pause Redis Enterprise when not developing (billing stops)

---

## 🚀 Deployment Strategy

### Option 1: Azure Developer CLI (azd) - **RECOMMENDED**

**Why azd?**
- Simplified Azure deployment
- Infrastructure as Code (Bicep)
- Environment management (dev, staging, prod)
- One command deploy: `azd up`
- Integrated with Container Apps

**Project Structure:**
```
FinagentiX/
├── azure.yaml                 # azd configuration
├── infra/                     # Bicep templates
│   ├── main.bicep            # Main infrastructure
│   ├── redis.bicep           # Redis Enterprise
│   ├── openai.bicep          # Azure OpenAI
│   ├── storage.bicep         # Storage Account
│   ├── container-apps.bicep  # Container Apps
│   ├── networking.bicep      # VNet, Private Endpoints
│   └── monitoring.bicep      # Log Analytics, App Insights
├── src/
│   ├── ingestion/            # Data ingestion service
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── api/                  # Agent API service
│       ├── Dockerfile
│       └── requirements.txt
```

**Deployment Commands:**
```bash
# Initialize project
azd init

# Provision infrastructure
azd provision

# Deploy application
azd deploy

# Full deployment (provision + deploy)
azd up

# Tear down everything
azd down --purge
```

---

### Option 2: Pure Bicep (No azd)

**If you prefer raw Bicep:**
```bash
# Deploy infrastructure
az deployment sub create \
  --name finagentix-deployment \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters environment=dev

# Delete everything
az group delete --name rg-finagentix-dev --yes
```

---

## 🔧 Infrastructure as Code (Bicep) Modules

### Module Breakdown

1. **main.bicep** - Orchestrates all modules
   - Creates Resource Group
   - Calls all sub-modules
   - Outputs connection strings

2. **redis.bicep** - Azure Managed Redis Enterprise
   - Creates Redis Enterprise cluster
   - Enables required modules (Search, TimeSeries, JSON, Bloom)
   - Configures persistence, clustering
   - Creates private endpoint
   - Outputs: `redisHost`, `redisPassword`

3. **openai.bicep** - Azure OpenAI Service
   - Creates OpenAI account
   - Deploys GPT-4 model
   - Deploys embedding model
   - Creates private endpoint
   - Outputs: `openaiEndpoint`, `openaiKey`

4. **storage.bicep** - Storage Account
   - Creates storage account
   - Creates containers: `sec-filings`, `news-articles`
   - Configures lifecycle policies
   - Creates private endpoint
   - Outputs: `storageConnectionString`

5. **networking.bicep** - VNet and Private Endpoints
   - Creates VNet with 4 subnets
   - Creates Private DNS zones
   - Links DNS zones to VNet
   - Creates Network Security Groups (NSG)

6. **container-apps.bicep** - Container Apps
   - Creates Container Apps Environment
   - Configures VNet integration
   - Deploys ingestion service (manual scaling)
   - Deploys agent API service (auto-scaling)
   - Outputs: `apiUrl`

7. **container-registry.bicep** - ACR
   - Creates ACR
   - Enables admin access
   - Outputs: `acrLoginServer`, `acrPassword`

8. **monitoring.bicep** - Observability
   - Creates Log Analytics Workspace
   - Creates Application Insights
   - Links Container Apps to logging
   - Outputs: `logAnalyticsId`, `appInsightsKey`

---

## 📋 Environment Variables

After deployment, these environment variables will be needed:

```bash
# Redis
REDIS_HOST=<redis-endpoint>.redisenterprise.cache.azure.net
REDIS_PORT=10000
REDIS_PASSWORD=<from-bicep-output>
REDIS_SSL=true

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<openai-name>.openai.azure.com/
AZURE_OPENAI_KEY=<from-bicep-output>
AZURE_OPENAI_GPT4_DEPLOYMENT=gpt-4-deployment
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=embedding-deployment

# Storage
AZURE_STORAGE_CONNECTION_STRING=<from-bicep-output>
AZURE_STORAGE_CONTAINER_FILINGS=sec-filings
AZURE_STORAGE_CONTAINER_NEWS=news-articles

# External APIs (user-provided)
NEWSAPI_KEY=<your-newsapi-key>

# Application
ENVIRONMENT=dev
LOG_LEVEL=INFO
```

---

## ✅ Post-Deployment Checklist

After running `azd up`:

- [ ] Verify Redis is accessible from Container Apps
- [ ] Test Redis modules: `FT.CREATE`, `TS.CREATE`, `JSON.SET`
- [ ] Verify Azure OpenAI deployments are ready
- [ ] Test Storage Account access (upload test file)
- [ ] Check Container Apps logs in Log Analytics
- [ ] Verify private endpoints are working (no public Redis access)
- [ ] Run data ingestion service (one-time load)
- [ ] Test Agent API endpoints
- [ ] Configure Application Insights alerts

---

## 🔒 Security Considerations

1. **Redis Enterprise:**
   - ✅ Private endpoint only (no public access)
   - ✅ TLS encryption in transit
   - ✅ Strong password (generated by Bicep)
   - ✅ AOF + RDB persistence enabled

2. **Azure OpenAI:**
   - ✅ Private endpoint only
   - ✅ API key rotation support
   - ✅ Content filtering enabled

3. **Storage Account:**
   - ✅ Private endpoint only
   - ✅ Encryption at rest (Microsoft-managed keys)
   - ✅ Minimal RBAC permissions

4. **Container Apps:**
   - ✅ Managed identity for Azure resource access
   - ✅ Secrets stored in Container Apps environment
   - ✅ VNet integration (no direct internet for outbound Redis)

5. **Network:**
   - ✅ NSG rules (deny all external to Redis)
   - ✅ Private DNS for name resolution
   - ✅ No public IPs for data services

---

## 🔄 Deployment Lifecycle

### Development Workflow

```bash
# 1. Make code changes
vim src/api/main.py

# 2. Deploy (builds containers, pushes to ACR, updates Container Apps)
azd deploy

# 3. Check logs
azd logs --service agent-api

# 4. Tear down when done (stops billing)
azd down
```

### Re-deploying Infrastructure

```bash
# Update Bicep templates
vim infra/redis.bicep

# Re-provision (updates existing resources)
azd provision

# Or full re-deploy
azd up
```

### Deleting Everything

```bash
# Complete cleanup
azd down --purge --force

# Verify resource group is deleted
az group list --query "[?name=='rg-finagentix-dev']"
```

---

## 🎯 What Gets Deployed and Why - Summary

| Component | Why Needed | Used By |
|-----------|------------|---------|
| **Redis Enterprise** | Core data platform for all AI Vision patterns | Agents, Featureform, Caching, RAG, Time-series |
| **Azure OpenAI** | LLM reasoning and embeddings | All agents, RAG, Sentiment analysis |
| **Storage Account** | Archive raw documents, avoid re-fetching | Data ingestion, Backup |
| **Container Apps** | Run Python services (ingestion, agents) | Data load, Agent API hosting |
| **VNet** | Secure private networking | All services communicate privately |
| **ACR** | Host Docker images | Container Apps pull images |
| **Log Analytics** | Centralized logging and metrics | Debugging, monitoring, alerts |
| **App Insights** | APM and performance tracking | Track agent latency, cache hit rates |

---

## 📝 Next Steps

1. **Review this document** - Confirm infrastructure matches requirements
2. **Create Bicep templates** - Start with `main.bicep` and modules
3. **Set up azd project** - Configure `azure.yaml`
4. **Build Docker images** - Create Dockerfiles for ingestion and API
5. **Deploy infrastructure** - Run `azd provision`
6. **Test deployment** - Verify all services are accessible
7. **Run data ingestion** - One-time batch load
8. **Deploy agents** - Test agent API

---

**Document Version:** 1.0  
**Last Updated:** December 5, 2025  
**Status:** Ready for Bicep implementation
