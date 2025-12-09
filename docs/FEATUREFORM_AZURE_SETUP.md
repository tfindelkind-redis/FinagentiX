# Featureform Azure Deployment Guide

## Overview

Featureform is **automatically deployed** as part of the main infrastructure deployment (Stage 3b). It runs on Azure Container Apps, integrated with your existing Azure Redis Enterprise as the online feature store.

**NOTE**: Featureform deploys automatically when you run `azd up` or deploy the full infrastructure. This guide provides details on the deployment and how to use it.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AZURE CONTAINER APPS                      │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Featureform Server (Port 7878)                        │ │
│  │  • Feature definitions                                 │ │
│  │  • Transformation engine                               │ │
│  │  • Metadata management                                 │ │
│  └──────────┬─────────────────────────────────────┬───────┘ │
│             ↓                                     ↓          │
│  ┌──────────────────────┐           ┌──────────────────────┐│
│  │  Postgres Flexible   │           │  Azure Redis         ││
│  │  Server              │           │  Enterprise          ││
│  │  • Feature metadata  │           │  • Online features   ││
│  │  • Lineage tracking  │           │  • Fast serving      ││
│  └──────────────────────┘           └──────────────────────┘│
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           ↓
                ┌──────────────────────┐
                │  Python Agents       │
                │  • Featureform       │
                │    Client API        │
                │  • Feature queries   │
                └──────────────────────┘
```

## Prerequisites

1. **Existing Resources**:
   - Azure Redis Enterprise (from Stage 1b)
   - Azure Container Apps Environment (from Stage 3)
   - Virtual Network with subnets

2. **Required Information**:
   - Redis host, port, password
   - Container Apps Environment ID
   - Subnet IDs for Postgres

## Automatic Deployment

Featureform is deployed automatically as **Stage 3b** when you deploy the full infrastructure:

```bash
cd /Users/thomas.findelkind/Code/FinagentiX

# Deploy all infrastructure (includes Featureform)
azd up

# Or use Bicep directly
az deployment group create \
  --resource-group finagentix-dev-rg \
  --template-file infra/main.bicep \
  --parameters environmentName=dev
```

This automatically deploys:
- **Postgres Flexible Server** for Featureform metadata
- **Featureform Container App** (featureformcom/featureform:latest)
- **Integration** with Azure Redis Enterprise (online store)
- **HTTPS ingress** on port 7878

## Post-Deployment Setup

### Step 1: Get Featureform URL

After deployment, get the Featureform URL from outputs:

```bash
# Get deployment outputs
az deployment group show \
  --resource-group finagentix-dev-rg \
  --name main-<resourceToken> \
  --query "properties.outputs" -o json

# Or directly query the Container App
az containerapp show \
  --name featureform-<resourceToken> \
  --resource-group finagentix-dev-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv
```

### Step 2: Update .env File

The deployment automatically populates these values in Azure (via Key Vault or App Settings). For local development, add to `.env`:

```bash
FEATUREFORM_HOST=<from-deployment-output>
FEATUREFORM_PORT=443
FEATUREFORM_INSECURE=false
```

### Step 3: Apply Feature Definitions

```bash
cd /Users/thomas.findelkind/Code/FinagentiX

# Set Featureform host
export FEATUREFORM_HOST=featureform-545d8fdb508d4.nicebeach-12345678.eastus.azurecontainerapps.io:443

# Apply definitions
featureform apply featureform/definitions.py
```

This will:
- Register Azure Redis as online store
- Define technical indicators (SMA 20/50/200)
- Define risk metrics (volatility, beta, etc.)
- Create feature transformations
- Set up training sets

### Step 5: Verify Deployment

```bash
# Check Featureform status
featureform get features

# Expected output:
# NAME                VARIANT   TYPE      ENTITY
# sma_20             default   float32   Stock
# sma_50             default   float32   Stock
# sma_200            default   float32   Stock
# volatility_30d     default   float32   Stock
```

## Python Client Usage

### Install Client (without full package)

Since the full Featureform package has Python 3.13 issues, use the client API directly:

```bash
# Install just the client
pip install featureform-client
```

### Query Features from Agents

```python
from featureform import Client
import os

# Initialize Featureform client
client = Client(
    host=os.getenv("FEATUREFORM_HOST"),
    cert_path=os.getenv("FEATUREFORM_CERT_PATH"),
    insecure=os.getenv("FEATUREFORM_INSECURE", "false").lower() == "true"
)

# Get features for a stock
features = client.features(
    [
        ("sma_20", "default"),
        ("sma_50", "default"),
        ("volatility_30d", "default")
    ],
    {"Stock": "AAPL"}
)

print(f"AAPL Features: {features}")
# Output: [185.32, 182.45, 0.23]
```

### Integration with Existing Tools

Update `src/tools/feature_tools.py` to use Featureform client:

```python
from featureform import Client
from src.agents.config import get_config

# Global Featureform client
_ff_client = None

def _get_featureform_client():
    global _ff_client
    if _ff_client is None:
        config = get_config()
        _ff_client = Client(
            host=config.featureform.host,
            insecure=False
        )
    return _ff_client

def get_technical_indicators(ticker: str, indicators: List[str]) -> Dict:
    """Get technical indicators from Featureform"""
    try:
        client = _get_featureform_client()
        
        # Map indicator names to Featureform features
        feature_list = []
        for indicator in indicators:
            if indicator == "sma_20":
                feature_list.append(("sma_20", "default"))
            elif indicator == "sma_50":
                feature_list.append(("sma_50", "default"))
            # ... etc
        
        # Query Featureform
        values = client.features(feature_list, {"Stock": ticker})
        
        # Return as dict
        return {name: val for (name, _), val in zip(feature_list, values)}
        
    except Exception as e:
        print(f"Featureform error, falling back: {e}")
        # Fall back to NumPy calculation
        return _calculate_indicators_fallback(ticker, indicators)
```

## Feature Materialization

Features need to be materialized (computed and stored) before serving:

```bash
# Trigger feature materialization
featureform materialize --feature sma_20 --variant default
featureform materialize --feature sma_50 --variant default
featureform materialize --feature sma_200 --variant default
```

Or use Python:

```python
from featureform import Client

client = Client(host=os.getenv("FEATUREFORM_HOST"))

# Materialize all features
client.materialize_feature("sma_20", "default")
client.materialize_feature("sma_50", "default")
client.materialize_feature("volatility_30d", "default")
```

## Monitoring

### Check Featureform Logs

```bash
az containerapp logs show \
  --name featureform-545d8fdb508d4 \
  --resource-group finagentix-dev-rg \
  --follow
```

### Check Feature Status

```bash
# Get feature status
featureform get feature sma_20 default

# Output shows:
# STATUS: READY
# LAST_UPDATED: 2025-12-08T13:45:00Z
# ROWS: 1000
```

### Dashboard

Featureform provides a web dashboard:

```
https://featureform-545d8fdb508d4.nicebeach-12345678.eastus.azurecontainerapps.io
```

## Cost Estimation

- **Postgres Flexible Server** (B1ms): ~$15/month
- **Featureform Container App** (1 CPU, 2GB): ~$35/month
- **Total**: ~$50/month

Can scale to zero when not in use to save costs.

## Troubleshooting

### 1. Connection Timeout

```bash
# Check if Featureform is running
az containerapp show \
  --name featureform-545d8fdb508d4 \
  --resource-group finagentix-dev-rg \
  --query "properties.runningStatus"
```

### 2. Redis Connection Failed

```bash
# Verify Redis credentials in Container App secrets
az containerapp secret list \
  --name featureform-545d8fdb508d4 \
  --resource-group finagentix-dev-rg
```

### 3. Feature Not Found

```bash
# Re-apply definitions
featureform apply featureform/definitions.py

# Materialize features
featureform materialize --feature sma_20 --variant default
```

## Next Steps

1. **Define More Features**: Add RSI, MACD, Bollinger Bands to `definitions.py`
2. **Schedule Materialization**: Use Azure Container Apps Jobs to materialize daily
3. **Integrate with Agents**: Update all tools to use Featureform client
4. **Monitor Performance**: Track feature serving latency (<10ms target)

## References

- [Featureform Documentation](https://docs.featureform.com/)
- [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/)
- [Azure Postgres Flexible Server](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/)
