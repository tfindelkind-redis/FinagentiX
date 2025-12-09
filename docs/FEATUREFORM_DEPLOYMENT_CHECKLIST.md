# Featureform Deployment - Ready to Deploy Checklist

## ✅ Completed Integration Work

### Infrastructure Code
- [x] **Stage 2b Bicep template** (`infra/stages/stage2b-featureform.bicep`)
  - Postgres Flexible Server for metadata
  - Featureform Container App
  - Redis Enterprise integration
  - HTTPS ingress configuration

- [x] **Main pipeline integration** (`infra/main.bicep`)
  - Added Stage 3b (Featureform)
  - Dependency management (after Stage 3 Container Apps Environment)
  - Conditional outputs for Featureform host/URL

- [x] **Feature definitions** (`featureform/definitions.py`)
  - Stock entity definition
  - Azure Redis provider registration
  - Technical indicators (SMA 20/50/200)
  - Risk metrics (volatility 30d)
  - SQL and DataFrame transformations

- [x] **Deployment automation** (`scripts/deploy_featureform_definitions.sh`)
  - Auto-discover Featureform from Azure
  - Apply definitions post-deployment
  - Handles both CLI and Python approaches

### Documentation
- [x] **Azure setup guide** (`docs/FEATUREFORM_AZURE_SETUP.md`)
- [x] **Integration summary** (`docs/FEATUREFORM_INTEGRATION_SUMMARY.md`)
- [x] **Updated original docs** (`docs/FEATUREFORM_INTEGRATION.md`)

## 🚀 Deployment Commands

### Option 1: Deploy Everything with azd (Recommended)

```bash
cd /Users/thomas.findelkind/Code/FinagentiX

# Deploy all infrastructure (includes Featureform)
azd up

# After deployment, apply feature definitions
./scripts/deploy_featureform_definitions.sh
```

### Option 2: Deploy with Azure CLI

```bash
cd /Users/thomas.findelkind/Code/FinagentiX

# Deploy main Bicep (includes Featureform)
az deployment group create \
  --resource-group finagentix-dev-rg \
  --template-file infra/main.bicep \
  --parameters environmentName=dev

# Get outputs
az deployment group show \
  --resource-group finagentix-dev-rg \
  --name main \
  --query "properties.outputs" -o json

# Apply feature definitions
./scripts/deploy_featureform_definitions.sh
```

### Option 3: Deploy Only Featureform Stage

If infrastructure already exists:

```bash
cd /Users/thomas.findelkind/Code/FinagentiX

# Get required values from existing deployment
RESOURCE_TOKEN=$(az deployment group show -g finagentix-dev-rg -n main --query "properties.outputs.AZURE_RESOURCE_GROUP.value" -o tsv | grep -o '[0-9a-z]*$')
VNET_ID=$(az network vnet show -g finagentix-dev-rg -n vnet-$RESOURCE_TOKEN --query "id" -o tsv)
SUBNET_ID=$(az network vnet subnet show -g finagentix-dev-rg --vnet-name vnet-$RESOURCE_TOKEN -n container-apps-subnet --query "id" -o tsv)
CAE_ID=$(az containerapp env show -g finagentix-dev-rg -n cae-$RESOURCE_TOKEN --query "id" -o tsv)
REDIS_HOST=$(az deployment group show -g finagentix-dev-rg -n main --query "properties.outputs.REDIS_HOST.value" -o tsv)
REDIS_PASSWORD=$(az deployment group show -g finagentix-dev-rg -n main --query "properties.outputs.REDIS_PASSWORD.value" -o tsv)

# Deploy Featureform only
az deployment group create \
  --resource-group finagentix-dev-rg \
  --template-file infra/stages/stage2b-featureform.bicep \
  --parameters \
    environmentName=dev \
    resourceToken=$RESOURCE_TOKEN \
    vnetId="$VNET_ID" \
    containerAppsSubnetId="$SUBNET_ID" \
    containerAppsEnvironmentId="$CAE_ID" \
    redisHost="$REDIS_HOST" \
    redisPassword="$REDIS_PASSWORD"
```

## 📋 Pre-Deployment Checklist

- [ ] Azure subscription active
- [ ] Resource group exists: `finagentix-dev-rg`
- [ ] Existing infrastructure deployed (Stage 0-3)
  - [ ] VNet and subnets
  - [ ] Redis Enterprise
  - [ ] Container Apps Environment
- [ ] Azure CLI authenticated: `az login`
- [ ] azd initialized: `azd init` (if using azd)

## 🔍 Post-Deployment Verification

### 1. Check Featureform Container App

```bash
# Check running status
az containerapp show \
  --name featureform-<resourceToken> \
  --resource-group finagentix-dev-rg \
  --query "{Name:name, Status:properties.runningStatus, FQDN:properties.configuration.ingress.fqdn}" -o table

# Check logs
az containerapp logs show \
  --name featureform-<resourceToken> \
  --resource-group finagentix-dev-rg \
  --follow
```

### 2. Check Postgres Server

```bash
# Check Postgres status
az postgres flexible-server show \
  --name postgres-ff-<resourceToken> \
  --resource-group finagentix-dev-rg \
  --query "{Name:name, State:state, FQDN:fullyQualifiedDomainName}" -o table
```

### 3. Verify Featureform API

```bash
# Get Featureform host
FEATUREFORM_HOST=$(az deployment group show \
  --resource-group finagentix-dev-rg \
  --name main \
  --query "properties.outputs.FEATUREFORM_HOST.value" -o tsv)

# Test API endpoint
curl -k https://$FEATUREFORM_HOST/health

# Open dashboard
open https://$FEATUREFORM_HOST
```

### 4. Apply Feature Definitions

```bash
# Apply definitions
./scripts/deploy_featureform_definitions.sh

# Verify features registered
featureform get features

# Expected output:
# NAME             VARIANT   TYPE      ENTITY
# sma_20          default   float32   Stock
# sma_50          default   float32   Stock
# sma_200         default   float32   Stock
# volatility_30d  default   float32   Stock
```

### 5. Test Feature Serving

```python
from featureform import Client
import os

# Initialize client
client = Client(host=os.getenv("FEATUREFORM_HOST"), insecure=False)

# Get features
features = client.features(
    [("sma_20", "default"), ("sma_50", "default")],
    {"Stock": "AAPL"}
)

print(f"AAPL Features: {features}")
```

## 📊 Expected Resources

After deployment, you should see:

| Resource | Name | Type | Purpose |
|----------|------|------|---------|
| Postgres | `postgres-ff-<token>` | Flexible Server | Featureform metadata |
| Database | `featureform` | Postgres DB | Feature definitions |
| Container App | `featureform-<token>` | Container App | Featureform server |
| Ingress | `<token>.azurecontainerapps.io` | HTTPS | API access |

## 💰 Cost Estimate

| Resource | SKU | Monthly Cost |
|----------|-----|--------------|
| Postgres Flexible Server | B1ms (1 core, 2GB) | ~$15 |
| Featureform Container App | 1 CPU, 2GB | ~$35 |
| **Total** | | **~$50** |

*Can scale Container App to zero when not in use.*

## 🔧 Troubleshooting

### Container App Not Starting

```bash
# Check events
az containerapp revision show \
  --name featureform-<resourceToken> \
  --resource-group finagentix-dev-rg \
  --query "properties.template" -o json

# Check logs for errors
az containerapp logs show \
  --name featureform-<resourceToken> \
  --resource-group finagentix-dev-rg \
  --tail 100
```

### Redis Connection Issues

```bash
# Verify Redis connection from Container App
az containerapp exec \
  --name featureform-<resourceToken> \
  --resource-group finagentix-dev-rg \
  --command "/bin/sh -c 'nc -zv $REDIS_HOST $REDIS_PORT'"
```

### Postgres Connection Issues

```bash
# Check Postgres firewall rules
az postgres flexible-server firewall-rule list \
  --name postgres-ff-<resourceToken> \
  --resource-group finagentix-dev-rg
```

### Feature Definitions Not Applying

```bash
# Re-apply with verbose output
featureform apply featureform/definitions.py --verbose

# Check Featureform server logs
az containerapp logs show \
  --name featureform-<resourceToken> \
  --resource-group finagentix-dev-rg \
  --follow
```

## 📚 Additional Resources

- **Full Setup Guide**: `docs/FEATUREFORM_AZURE_SETUP.md`
- **Integration Summary**: `docs/FEATUREFORM_INTEGRATION_SUMMARY.md`
- **Feature Definitions**: `featureform/definitions.py`
- **Bicep Template**: `infra/stages/stage2b-featureform.bicep`
- **Featureform Docs**: https://docs.featureform.com/

## ✨ Next Steps After Deployment

1. **Materialize Features**: Compute and store features in Redis
   ```bash
   featureform materialize --feature sma_20 --variant default
   ```

2. **Update Agent Tools**: Integrate Featureform Client in `src/tools/feature_tools.py`

3. **Schedule Batch Jobs**: Set up daily feature computation

4. **Monitor Performance**: Track feature serving latency and accuracy

5. **Add More Features**: Expand definitions to include more indicators

---

**Status**: ✅ Ready for Deployment
**Deployment Time**: ~15 minutes
**Next Action**: Run `azd up` or deploy Bicep template
