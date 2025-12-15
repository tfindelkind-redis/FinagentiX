#!/bin/bash

# Deploy Azure OpenAI using az commands (workaround for Bicep streaming bug)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get environment from variable or default
AZURE_ENV_NAME="${AZURE_ENV_NAME:-dev}"
AZURE_LOCATION="${AZURE_LOCATION:-westus3}"
RESOURCE_GROUP="finagentix-${AZURE_ENV_NAME}-rg"

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Deploy Azure OpenAI${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Discover resource token
echo "🔍 Discovering resource token..."
RESOURCE_TOKEN=$(az vm list -g "$RESOURCE_GROUP" --query "[?starts_with(name, 'debug-vm-')].name" -o tsv | sed 's/debug-vm-//' | head -n 1)

if [ -z "$RESOURCE_TOKEN" ]; then
    # Try Redis
    RESOURCE_TOKEN=$(az redisenterprise show -g "$RESOURCE_GROUP" --query "[?starts_with(name, 'redis-')].name" -o tsv | sed 's/redis-//' | head -n 1)
fi

if [ -z "$RESOURCE_TOKEN" ]; then
    echo -e "${RED}❌ Could not discover resource token${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Resource token: $RESOURCE_TOKEN${NC}"

OPENAI_NAME="openai-${RESOURCE_TOKEN}"

# Check if already exists
if az cognitiveservices account show -g "$RESOURCE_GROUP" -n "$OPENAI_NAME" &>/dev/null; then
    echo -e "${GREEN}✅ Azure OpenAI already exists: $OPENAI_NAME${NC}"
    
    # Check if models are already deployed
    DEPLOYMENT_COUNT=$(az cognitiveservices account deployment list -g "$RESOURCE_GROUP" -n "$OPENAI_NAME" --query "length(@)" -o tsv 2>/dev/null || echo "0")
    
    if [ "$DEPLOYMENT_COUNT" -ge "2" ]; then
        echo ""
        echo "📋 Model deployments already exist:"
        az cognitiveservices account deployment list -g "$RESOURCE_GROUP" -n "$OPENAI_NAME" \
            --query "[].{Name:name, Model:properties.model.name, State:properties.provisioningState}" -o table
        exit 0
    fi
    
    echo ""
    echo "📦 Deploying models..."
fi

echo ""
echo "🤖 Creating Azure OpenAI resource..."
az cognitiveservices account create \
    --name "$OPENAI_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$AZURE_LOCATION" \
    --kind OpenAI \
    --sku S0 \
    --custom-domain "$OPENAI_NAME" \
    --output none

echo -e "${GREEN}✅ Azure OpenAI created${NC}"

# Wait for resource to be ready
echo ""
echo "⏳ Waiting for resource to be ready..."
sleep 10

# Deploy text-embedding-3-large
echo ""
echo "📦 Deploying text-embedding-3-large model..."
az cognitiveservices account deployment create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$OPENAI_NAME" \
    --deployment-name text-embedding-3-large \
    --model-name text-embedding-3-large \
    --model-version "1" \
    --model-format OpenAI \
    --sku-name "Standard" \
    --sku-capacity 10 \
    --output none

echo -e "${GREEN}✅ text-embedding-3-large deployed${NC}"

# Deploy GPT-4o
echo ""
echo "📦 Deploying gpt-4o model..."
az cognitiveservices account deployment create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$OPENAI_NAME" \
    --deployment-name gpt-4o \
    --model-name gpt-4o \
    --model-version "2024-11-20" \
    --model-format OpenAI \
    --sku-name "Standard" \
    --sku-capacity 10 \
    --output none

echo -e "${GREEN}✅ gpt-4o deployed${NC}"

# Show final status
echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}✅ Azure OpenAI Deployment Complete${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

ENDPOINT=$(az cognitiveservices account show -g "$RESOURCE_GROUP" -n "$OPENAI_NAME" --query "properties.endpoint" -o tsv)

echo "Resource: $OPENAI_NAME"
echo "Endpoint: $ENDPOINT"
echo ""
echo "Deployments:"
az cognitiveservices account deployment list -g "$RESOURCE_GROUP" -n "$OPENAI_NAME" \
    --query "[].{Name:name, Model:properties.model.name, Version:properties.model.version, State:properties.provisioningState}" -o table
