# Featureform Deployment Guide

## Quick Start

Deploy Featureform to Azure in one command:

```bash
./infra/scripts/deploy-featureform.sh
```

That's it! The script handles everything automatically.

---

## What Gets Deployed

1. **Container Apps Environment** (if not exists)
   - Internal-only to avoid public IP quota
   - Integrated with existing VNet and Log Analytics
   
2. **Featureform Container App**
   - Latest Featureform image
   - Connected to Redis for metadata (DB 2) and online store (DB 0)
   - HTTPS ingress with HTTP/2 support
   - Auto-scaling 1-3 replicas

---

## Prerequisites

- Azure CLI installed and authenticated
- Existing FinagentiX infrastructure deployed (Stage 0-2)
- Resource group: `finagentix-dev-rg`
- Redis Enterprise deployed

To deploy prerequisites:
```bash
./infra/scripts/deploy.sh
```

---

## Deployment Options

### Option 1: Standalone Script (Recommended)
```bash
./infra/scripts/deploy-featureform.sh
```

**Features**:
- ✅ Detects existing resources
- ✅ Handles failed environments automatically
- ✅ Prompts before overwriting
- ✅ Colored output with status indicators
- ✅ Complete error messages

### Option 2: Integrated with Main Deployment
```bash
./infra/scripts/deploy.sh
# Answer 'y' when prompted: "Do you want to deploy Featureform now?"
```

### Option 3: Manual Bicep Deployment
```bash
# Get Redis password
REDIS_PASSWORD=$(az redisenterprise database list-keys \
  -g finagentix-dev-rg \
  --cluster-name redis-545d8fdb508d4 \
  --query "primaryKey" -o tsv)

# Deploy
az deployment group create \
  --resource-group finagentix-dev-rg \
  --template-file infra/deploy-featureform-final.bicep \
  --parameters \
    location=eastus \
    resourceToken=545d8fdb508d4 \
    redisPassword="$REDIS_PASSWORD"
```

---

## Verification

### Check Deployment Status
```bash
az containerapp show \
  -g finagentix-dev-rg \
  -n featureform-545d8fdb508d4 \
  --query "{Name:name, Status:properties.runningStatus, URL:properties.configuration.ingress.fqdn}"
```

### Expected Output
```json
{
  "Name": "featureform-545d8fdb508d4",
  "Status": "Running",
  "URL": "featureform-545d8fdb508d4.victoriousdune-76bc4f5c.eastus.azurecontainerapps.io"
}
```

### View Logs
```bash
az containerapp logs show \
  -g finagentix-dev-rg \
  -n featureform-545d8fdb508d4 \
  --tail 100 \
  --follow
```

---

## Redeployment

The script is **idempotent** and safe to run multiple times.

### Update Existing Deployment
```bash
./infra/scripts/deploy-featureform.sh
# Answer 'y' when prompted to update
```

### Force Clean Redeployment
```bash
# Delete app
az containerapp delete \
  -g finagentix-dev-rg \
  -n featureform-545d8fdb508d4 \
  --yes

# Redeploy
./infra/scripts/deploy-featureform.sh
```

---

## Troubleshooting

### Issue: Container App Not Running

**Check replica status:**
```bash
az containerapp revision list \
  -g finagentix-dev-rg \
  -n featureform-545d8fdb508d4 \
  -o table
```

**Check logs for errors:**
```bash
az containerapp logs show \
  -g finagentix-dev-rg \
  -n featureform-545d8fdb508d4 \
  --tail 500
```

### Issue: Redis Connection Errors

**Verify Redis is running:**
```bash
az redisenterprise database show \
  -g finagentix-dev-rg \
  --cluster-name redis-545d8fdb508d4 \
  --query "{State:provisioningState, Host:hostName, Port:port}"
```

**Test connectivity (requires Redis CLI):**
```bash
REDIS_PASSWORD=$(az redisenterprise database list-keys \
  -g finagentix-dev-rg \
  --cluster-name redis-545d8fdb508d4 \
  --query "primaryKey" -o tsv)

redis-cli -h redis-545d8fdb508d4.eastus.redis.azure.net -p 10000 --tls --pass "$REDIS_PASSWORD" ping
# Expected: PONG
```

### Issue: Container Apps Environment Failed

**Delete and recreate:**
```bash
# Delete failed environment
az containerapp env delete \
  -g finagentix-dev-rg \
  -n cae-545d8fdb508d4 \
  --yes

# Wait for deletion
sleep 60

# Redeploy (will recreate environment)
./infra/scripts/deploy-featureform.sh
```

---

## Architecture

```
┌─────────────────────────────────────────┐
│  Container Apps Environment              │
│  (Internal-only, no public IP)          │
│                                          │
│  ┌───────────────────────────────────┐  │
│  │  Featureform Container App         │  │
│  │  - Image: featureformcom/latest   │  │
│  │  - CPU: 1.0, RAM: 2GB              │  │
│  │  - Scale: 1-3 replicas             │  │
│  │  - Port: 7878 (HTTPS/HTTP2)        │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
            ↓ SSL/TLS
┌─────────────────────────────────────────┐
│  Redis Enterprise                        │
│  - DB 0: Online Feature Store           │
│  - DB 2: Metadata Store                 │
│  - Port: 10000 (SSL)                    │
└─────────────────────────────────────────┘
```

---

## Configuration

### Environment Variables (Automatic)

The deployment script configures these automatically:

| Variable | Value | Purpose |
|----------|-------|---------|
| `METADATA_BACKEND` | redis | Use Redis for metadata |
| `METADATA_REDIS_HOST` | redis-545d8fdb508d4.eastus.redis.azure.net | Redis host |
| `METADATA_REDIS_PORT` | 10000 | Redis port |
| `METADATA_REDIS_DB` | 2 | Metadata database |
| `METADATA_REDIS_SSL` | true | Enable SSL |
| `REDIS_HOST` | redis-545d8fdb508d4.eastus.redis.azure.net | Redis host |
| `REDIS_PORT` | 10000 | Redis port |
| `REDIS_SSL` | true | Enable SSL |

### Secrets (Automatic)

- `redis-password`: Retrieved from Redis Enterprise and stored as Container App secret

---

## Feature Definitions (Coming Soon)

⚠️ **Note**: Feature definitions require Python 3.11 or 3.12 due to featureform package compatibility.

### Feature Definitions File
`featureform/definitions.py` - Ready to apply once Python environment is available

### Defined Features
- Stock entity
- Azure Redis provider
- Technical indicators: SMA 20/50/200, volatility
- SQL and DataFrame transformations
- Training sets for ML

### Apply Definitions (Python 3.11/3.12)
```bash
# Set Featureform host
export FEATUREFORM_HOST=featureform-545d8fdb508d4.victoriousdune-76bc4f5c.eastus.azurecontainerapps.io

# Apply definitions
./scripts/deploy_featureform_definitions.sh
```

---

## Cost Estimate

| Resource | Monthly Cost (USD) |
|----------|--------------------|
| Container Apps Environment | ~$0 (shared) |
| Featureform App (1 CPU, 2GB) | ~$30-40 |
| **Total Additional Cost** | **~$30-40** |

*Existing Redis Enterprise cost (~$480/month) is shared with other services.*

---

## Files

### Deployment Scripts
- `infra/scripts/deploy-featureform.sh` - Main deployment script
- `scripts/deploy_featureform_definitions.sh` - Feature definitions script

### Infrastructure
- `infra/deploy-featureform-final.bicep` - Bicep template
- `featureform/definitions.py` - Feature definitions (Python 3.11/3.12)

### Documentation
- `docs/FEATUREFORM_DEPLOYMENT_SUCCESS.md` - Detailed deployment report
- `DEPLOYMENT_SUMMARY.md` - High-level summary
- `docs/FEATUREFORM_AZURE_SETUP.md` - Complete setup guide

---

## Support

### View Deployment History
```bash
az deployment group list \
  -g finagentix-dev-rg \
  --query "[?contains(name, 'featureform')].{Name:name, State:properties.provisioningState, Time:properties.timestamp}" \
  -o table
```

### Get Resource Details
```bash
az resource list \
  -g finagentix-dev-rg \
  --query "[?contains(name, 'featureform') || contains(name, 'cae')].{Name:name, Type:type, State:provisioningState}" \
  -o table
```

### Export Configuration
```bash
az containerapp show \
  -g finagentix-dev-rg \
  -n featureform-545d8fdb508d4 \
  > featureform-config.json
```

---

## Related Documentation

- [Azure Setup Guide](docs/FEATUREFORM_AZURE_SETUP.md)
- [Integration Guide](docs/FEATUREFORM_INTEGRATION.md)
- [Deployment Checklist](docs/FEATUREFORM_DEPLOYMENT_CHECKLIST.md)
- [Deployment Success Report](docs/FEATUREFORM_DEPLOYMENT_SUCCESS.md)
- [Main Deployment Summary](DEPLOYMENT_SUMMARY.md)

---

## Quick Reference

```bash
# Deploy
./infra/scripts/deploy-featureform.sh

# Check status
az containerapp show -g finagentix-dev-rg -n featureform-545d8fdb508d4

# View logs
az containerapp logs show -g finagentix-dev-rg -n featureform-545d8fdb508d4 --tail 100

# Redeploy
az containerapp delete -g finagentix-dev-rg -n featureform-545d8fdb508d4 --yes
./infra/scripts/deploy-featureform.sh
```

---

**Status**: ✅ Deployment infrastructure complete and production-ready!

**Featureform URL**: `https://featureform-545d8fdb508d4.victoriousdune-76bc4f5c.eastus.azurecontainerapps.io`
