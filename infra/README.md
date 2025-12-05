# FinagentiX Infrastructure Deployment

## 🎯 Quick Start

### Prerequisites

- [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli) installed
- [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) installed
- Azure subscription with appropriate permissions
- Bicep CLI (included with Azure CLI)

### Initial Setup

```bash
# 1. Clone the repository
cd FinagentiX

# 2. Initialize azd
azd init

# 3. Log in to Azure
azd auth login

# 4. Set environment variables (optional)
azd env set AZURE_LOCATION eastus
azd env set REDIS_SKU Enterprise_E5  # or Enterprise_E10 for prod
```

## 📦 Deployment Options

### Option 1: Deploy All Stages at Once (Recommended for First Deployment)

```bash
# Deploy complete infrastructure
azd up

# This will provision:
# - Stage 0: Foundation (Networking, Logging)
# - Stage 1: Data Platform (Redis, Storage)
# - Stage 2: AI Services (Azure OpenAI)
# - Stage 3: Data Ingestion (Container App)
# - Stage 4: Agent Runtime (Container App)
```

### Option 2: Deploy Stages Independently

#### Stage 0: Foundation (Required First)
```bash
# Deploy networking and monitoring
azd provision --from-module stage0-foundation

# Or using Azure CLI directly
az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters environmentName=dev deployStage=foundation
```

#### Stage 1: Data Platform
```bash
# Deploy Redis + Storage (requires Stage 0)
az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters environmentName=dev deployStage=data-platform redisSku=Enterprise_E5
```

#### Stage 2: AI Services
```bash
# Deploy Azure OpenAI (requires Stage 0)
az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters environmentName=dev deployStage=ai-services
```

#### Stage 3: Data Ingestion
```bash
# Deploy ingestion Container App (requires Stage 0, 1, 2)
az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters environmentName=dev deployStage=data-ingestion
```

#### Stage 4: Agent Runtime
```bash
# Deploy agent API Container App (requires Stage 0, 1, 2)
az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters environmentName=dev deployStage=agent-runtime
```

## 🔧 Configuration

### Environment Variables

After deployment, azd automatically sets these environment variables:

```bash
# View all environment variables
azd env get-values

# Key variables:
REDIS_HOST              # Redis Enterprise hostname
REDIS_PORT              # Redis port (10000)
REDIS_PASSWORD          # Redis access key
AZURE_OPENAI_ENDPOINT   # Azure OpenAI endpoint
AZURE_OPENAI_KEY        # Azure OpenAI key
STORAGE_ACCOUNT_NAME    # Storage account name
```

### Redis SKU Options

- `Enterprise_E5` (6GB) - ~$225/month - Good for development
- `Enterprise_E10` (12GB) - ~$450/month - Minimum for production
- `Enterprise_E20` (25GB) - ~$900/month - Large production workloads

## 🗑️ Cleanup

### Delete Specific Stage

```bash
# Delete only data ingestion (to save costs after data load)
az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters environmentName=dev deployStage=data-ingestion \
  --mode Complete
```

### Delete Everything

```bash
# Delete all resources
azd down --purge --force

# Or manually
az group delete --name finagentix-dev-rg --yes
```

## 📊 Deployment Scenarios

### Scenario 1: Development (Minimal Cost)

Deploy only what you need:

```bash
# 1. Foundation + Data Platform
azd provision # Select only stage0 and stage1

# 2. When ready for data ingestion, add AI Services + Ingestion
azd provision # Add stage2 and stage3

# 3. After data is loaded, delete ingestion stage
# (Manual cleanup of ingestion container app)

# 4. When testing agents, deploy Agent Runtime
azd provision # Add stage4
```

**Cost: ~$235-265/month** (Foundation + Redis E5)

### Scenario 2: Full Production

```bash
# Deploy everything with E10 Redis
azd env set REDIS_SKU Enterprise_E10
azd up
```

**Cost: ~$545-750/month**

## 🚀 Post-Deployment Steps

### 1. Verify Redis Connection

```bash
# Get Redis connection details
REDIS_HOST=$(azd env get-value REDIS_HOST)
REDIS_PASSWORD=$(azd env get-value REDIS_PASSWORD)

# Test connection with redis-cli
redis-cli -h $REDIS_HOST -p 10000 -a $REDIS_PASSWORD --tls PING
```

### 2. Create Redis Indices

```bash
# SSH into a container or use Azure Cloud Shell
# Create vector search index for documents
redis-cli -h $REDIS_HOST -p 10000 -a $REDIS_PASSWORD --tls \
  FT.CREATE idx:documents \
  ON HASH PREFIX 1 doc: \
  SCHEMA \
    title TEXT WEIGHT 2.0 \
    content TEXT \
    embedding VECTOR HNSW 6 TYPE FLOAT32 DIM 3072 DISTANCE_METRIC COSINE

# Create time-series for market data
redis-cli -h $REDIS_HOST -p 10000 -a $REDIS_PASSWORD --tls \
  TS.CREATE ts:AAPL:close RETENTION 7776000000 LABELS ticker AAPL type close
```

### 3. Build and Push Container Images

```bash
# Build data ingestion image
docker build -t finagentix/data-ingestion:latest ./src/ingestion
docker tag finagentix/data-ingestion:latest $ACR_NAME.azurecr.io/finagentix/data-ingestion:latest

# Push to ACR
ACR_NAME=$(azd env get-value CONTAINER_REGISTRY_NAME)
az acr login --name $ACR_NAME
docker push $ACR_NAME.azurecr.io/finagentix/data-ingestion:latest

# Same for agent API
docker build -t finagentix/agent-api:latest ./src/api
docker tag finagentix/agent-api:latest $ACR_NAME.azurecr.io/finagentix/agent-api:latest
docker push $ACR_NAME.azurecr.io/finagentix/agent-api:latest
```

### 4. Run Data Ingestion

```bash
# The ingestion Container App is deployed but needs images
# After pushing images, restart the app
az containerapp revision restart \
  --name ca-data-ingestion-* \
  --resource-group finagentix-dev-rg
```

## 🔍 Monitoring

### View Logs

```bash
# Container Apps logs
az containerapp logs show \
  --name ca-data-ingestion-* \
  --resource-group finagentix-dev-rg \
  --follow

az containerapp logs show \
  --name ca-agent-api-* \
  --resource-group finagentix-dev-rg \
  --follow
```

### Monitor Redis

```bash
# Redis metrics in Azure Portal
# Navigate to: Redis Enterprise > Metrics
# Key metrics:
# - Connected Clients
# - Total Commands Processed
# - Used Memory
# - Cache Hit Rate
```

### Application Insights

Access in Azure Portal:
```
Resource Group > Application Insights > Application map
```

## 🐛 Troubleshooting

### Issue: Private Endpoint DNS Resolution

```bash
# Verify private DNS zones are linked to VNet
az network private-dns link vnet list \
  --resource-group finagentix-dev-rg \
  --zone-name privatelink.redisenterprise.cache.azure.net
```

### Issue: Container App Can't Connect to Redis

```bash
# Check if Container Apps subnet is connected to VNet
az network vnet subnet show \
  --resource-group finagentix-dev-rg \
  --vnet-name vnet-* \
  --name container-apps-subnet
```

### Issue: Redis Modules Not Available

```bash
# Verify modules are enabled
az redisenterprise database show \
  --resource-group finagentix-dev-rg \
  --cluster-name redis-* \
  --name default \
  --query modules
```

## 📋 Checklist

- [ ] Azure CLI and azd installed
- [ ] Logged in to Azure (`azd auth login`)
- [ ] Environment initialized (`azd init`)
- [ ] Stage 0 deployed (Foundation)
- [ ] Stage 1 deployed (Data Platform)
- [ ] Redis connection tested
- [ ] Stage 2 deployed (AI Services)
- [ ] OpenAI deployments verified
- [ ] Container images built and pushed
- [ ] Stage 3 deployed (Data Ingestion)
- [ ] Data ingestion completed
- [ ] Stage 4 deployed (Agent Runtime)
- [ ] Agent API tested

## 🎯 Next Steps

1. ✅ Deploy infrastructure
2. ✅ Test Redis connectivity
3. ✅ Build and push Docker images
4. ✅ Run data ingestion
5. ✅ Test agent API
6. 🚀 Start developing agents!

---

For detailed architecture information, see [INFRASTRUCTURE.md](../docs/infrastructure/INFRASTRUCTURE.md) and [DEPLOYMENT_STAGES.md](../docs/infrastructure/DEPLOYMENT_STAGES.md).
