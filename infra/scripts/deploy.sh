#!/bin/bash
set -e

# FinagentiX Deployment Script
# This script deploys all infrastructure stages in the correct order

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"

# Use azd environment if available, otherwise use defaults
if command -v azd &> /dev/null && azd env list &> /dev/null; then
    echo "ℹ️  Using azd environment"
    AZURE_ENV_NAME=$(azd env get-value AZURE_ENV_NAME 2>/dev/null || echo "dev")
    AZURE_LOCATION=$(azd env get-value AZURE_LOCATION 2>/dev/null || echo "westus3")
    RESOURCE_GROUP="finagentix-${AZURE_ENV_NAME}-rg"
else
    echo "ℹ️  azd not configured, using environment variables or defaults"
    AZURE_ENV_NAME="${AZURE_ENV_NAME:-dev}"
    AZURE_LOCATION="${AZURE_LOCATION:-westus3}"
    RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-finagentix-${AZURE_ENV_NAME}-rg}"
fi

LOCATION="$AZURE_LOCATION"
RESOURCE_TOKEN=$(echo $RANDOM | md5sum | head -c 13 2>/dev/null || echo $RANDOM | md5 | head -c 13)

echo "=========================================="
echo "FinagentiX Infrastructure Deployment"
echo "=========================================="
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "Environment: ${AZURE_ENV_NAME}"
echo "Resource Token: $RESOURCE_TOKEN"
echo ""

# Function to check deployment status
check_deployment() {
    local name=$1
    local rg=$2
    echo "Checking deployment: $name"
    az deployment group show -g "$rg" -n "$name" --query "properties.provisioningState" -o tsv 2>/dev/null || echo "NotFound"
}

# Function to wait for deployment
wait_for_deployment() {
    local name=$1
    local rg=$2
    local timeout=1800  # 30 minutes
    local elapsed=0
    
    echo "Waiting for deployment '$name' to complete..."
    while [ $elapsed -lt $timeout ]; do
        state=$(check_deployment "$name" "$rg")
        if [ "$state" == "Succeeded" ]; then
            echo "✅ Deployment '$name' succeeded"
            return 0
        elif [ "$state" == "Failed" ] || [ "$state" == "Canceled" ]; then
            echo "❌ Deployment '$name' failed with state: $state"
            return 1
        fi
        sleep 10
        elapsed=$((elapsed + 10))
        echo -n "."
    done
    echo "⏱️  Deployment '$name' timed out"
    return 1
}

# Create resource group if it doesn't exist
echo "📦 Creating resource group..."
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --tags environment="${AZURE_ENV_NAME}" project="FinagentiX" managedBy="azd" owner="${AZURE_OWNER:-$(az account show --query user.name -o tsv)}" \
    --output none

echo "✅ Resource group created"
echo ""

# Stage 0: Foundation
# Check if Stage 0 is already deployed
EXISTING_STAGE0=$(az deployment group list -g "$RESOURCE_GROUP" --query "[?contains(name, 'stage0-foundation')] | [0].name" -o tsv 2>/dev/null)

if [ -n "$EXISTING_STAGE0" ] && [ "$EXISTING_STAGE0" != "null" ]; then
    echo "ℹ️  Stage 0 already deployed: $EXISTING_STAGE0"
    echo "   Skipping Stage 0 deployment..."
    STAGE0_DEPLOYMENT_NAME="$EXISTING_STAGE0"
else
    echo "🏗️  Stage 0: Deploying Foundation (VNet, DNS, Monitoring)..."
    STAGE0_DEPLOYMENT_NAME="stage0-foundation-$(date +%s)"
    
    az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$INFRA_DIR/stages/stage0-foundation.bicep" \
        --parameters environmentName="${AZURE_ENV_NAME}" location="$LOCATION" resourceToken="$RESOURCE_TOKEN" \
        --name "$STAGE0_DEPLOYMENT_NAME" \
        --no-prompt true \
        --output table
    
    echo "✅ Stage 0 Foundation deployed"
fi
echo ""

# Get Stage 0 outputs
echo "📋 Retrieving Stage 0 outputs..."
STAGE0_OUTPUTS=$(az deployment group show -g "$RESOURCE_GROUP" -n "$STAGE0_DEPLOYMENT_NAME" --query "properties.outputs" -o json)

# If Stage 0 already existed, get the resource token from the deployment parameters
if [ -n "$EXISTING_STAGE0" ] && [ "$EXISTING_STAGE0" != "null" ]; then
    RESOURCE_TOKEN=$(az deployment group show -g "$RESOURCE_GROUP" -n "$STAGE0_DEPLOYMENT_NAME" --query "properties.parameters.resourceToken.value" -o tsv)
    echo "   Using existing resource token: $RESOURCE_TOKEN"
fi

REDIS_SUBNET_ID=$(echo "$STAGE0_OUTPUTS" | jq -r '.redisSubnetId.value')
STORAGE_SUBNET_ID=$(echo "$STAGE0_OUTPUTS" | jq -r '.storageSubnetId.value')
OPENAI_SUBNET_ID=$(echo "$STAGE0_OUTPUTS" | jq -r '.openaiSubnetId.value')
CONTAINER_APPS_SUBNET_ID=$(echo "$STAGE0_OUTPUTS" | jq -r '.containerAppsSubnetId.value')
VNET_ID=$(echo "$STAGE0_OUTPUTS" | jq -r '.vnetId.value')
PRIVATE_DNS_REDIS=$(echo "$STAGE0_OUTPUTS" | jq -r '.privateDnsZoneIdRedis.value')
PRIVATE_DNS_STORAGE=$(echo "$STAGE0_OUTPUTS" | jq -r '.privateDnsZoneIdStorage.value')
PRIVATE_DNS_OPENAI=$(echo "$STAGE0_OUTPUTS" | jq -r '.privateDnsZoneIdOpenAI.value')

echo "✅ Stage 0 outputs retrieved"
echo ""

# Stage 1a: Storage
EXISTING_STAGE1A=$(az deployment group list -g "$RESOURCE_GROUP" --query "[?contains(name, 'stage1a-storage') && properties.provisioningState=='Succeeded'] | [0].name" -o tsv 2>/dev/null)

if [ -n "$EXISTING_STAGE1A" ] && [ "$EXISTING_STAGE1A" != "null" ]; then
    echo "ℹ️  Stage 1a already deployed: $EXISTING_STAGE1A"
    echo "   Skipping Stage 1a deployment..."
else
    echo "💾 Stage 1a: Deploying Storage Account..."
    STAGE1A_DEPLOYMENT_NAME="stage1a-storage-$(date +%s)"
    
    az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$INFRA_DIR/stages/stage1a-storage-only.bicep" \
        --parameters \
            location="$LOCATION" \
            resourceToken="$RESOURCE_TOKEN" \
            storageSubnetId="$STORAGE_SUBNET_ID" \
            privateDnsZoneIdStorage="$PRIVATE_DNS_STORAGE" \
            vnetId="$VNET_ID" \
        --name "$STAGE1A_DEPLOYMENT_NAME" \
        --no-prompt true \
        --no-wait
    
    echo "⏳ Waiting for Storage deployment to complete..."
    while true; do
        STATE=$(az deployment group show -g "$RESOURCE_GROUP" -n "$STAGE1A_DEPLOYMENT_NAME" --query "properties.provisioningState" -o tsv 2>/dev/null)
        if [ "$STATE" = "Succeeded" ]; then
            echo "✅ Storage Account deployed"
            break
        elif [ "$STATE" = "Failed" ] || [ "$STATE" = "Canceled" ]; then
            echo "❌ Storage deployment failed with state: $STATE"
            exit 1
        fi
        echo "   State: $STATE - waiting..."
        sleep 10
    done
fi
echo ""

# Stage 1b: Azure Managed Redis
EXISTING_STAGE1B=$(az deployment group list -g "$RESOURCE_GROUP" --query "[?contains(name, 'stage1b-redis') && properties.provisioningState=='Succeeded'] | [0].name" -o tsv 2>/dev/null)

if [ -n "$EXISTING_STAGE1B" ] && [ "$EXISTING_STAGE1B" != "null" ]; then
    echo "ℹ️  Stage 1b already deployed: $EXISTING_STAGE1B"
    echo "   Skipping Stage 1b deployment..."
else
    echo "🔴 Stage 1b: Deploying Azure Managed Redis (Balanced_B5)..."
    echo "⏱️  This will take 15-20 minutes..."
    STAGE1B_DEPLOYMENT_NAME="stage1b-redis-$(date +%s)"
    
    az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$INFRA_DIR/stages/stage1b-redis-only.bicep" \
        --parameters \
            location="$LOCATION" \
            resourceToken="$RESOURCE_TOKEN" \
            redisSku="${REDIS_SKU:-Balanced_B5}" \
            redisSubnetId="$REDIS_SUBNET_ID" \
            privateDnsZoneIdRedis="$PRIVATE_DNS_REDIS" \
        --name "$STAGE1B_DEPLOYMENT_NAME" \
        --no-prompt true \
        --no-wait
    
    echo "⏳ Waiting for Redis deployment to complete (this takes 15-20 minutes)..."
    WAIT_COUNT=0
    while true; do
        STATE=$(az deployment group show -g "$RESOURCE_GROUP" -n "$STAGE1B_DEPLOYMENT_NAME" --query "properties.provisioningState" -o tsv 2>/dev/null)
        if [ "$STATE" = "Succeeded" ]; then
            echo "✅ Redis deployed"
            break
        elif [ "$STATE" = "Failed" ] || [ "$STATE" = "Canceled" ]; then
            echo "❌ Redis deployment failed with state: $STATE"
            exit 1
        fi
        WAIT_COUNT=$((WAIT_COUNT + 1))
        if [ $((WAIT_COUNT % 6)) -eq 0 ]; then
            echo "   State: $STATE - elapsed: $((WAIT_COUNT / 6)) minute(s)..."
        fi
        sleep 10
    done
fi
echo ""

# Stage 2: Azure OpenAI
EXISTING_STAGE2=$(az deployment group list -g "$RESOURCE_GROUP" --query "[?contains(name, 'stage2-ai-services') && properties.provisioningState=='Succeeded'] | [0].name" -o tsv 2>/dev/null)

if [ -n "$EXISTING_STAGE2" ] && [ "$EXISTING_STAGE2" != "null" ]; then
    echo "ℹ️  Stage 2 already deployed: $EXISTING_STAGE2"
    echo "   Skipping Stage 2 deployment..."
else
    echo "🤖 Stage 2: Deploying Azure OpenAI..."
    STAGE2_DEPLOYMENT_NAME="stage2-ai-services-$(date +%s)"
    
    az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$INFRA_DIR/stages/stage2-ai-services.bicep" \
        --parameters \
            environmentName="${AZURE_ENV_NAME}" \
            location="$LOCATION" \
            resourceToken="$RESOURCE_TOKEN" \
            openaiSubnetId="$OPENAI_SUBNET_ID" \
            privateDnsZoneIdOpenAI="$PRIVATE_DNS_OPENAI" \
            vnetId="$VNET_ID" \
        --name "$STAGE2_DEPLOYMENT_NAME" \
        --no-prompt true \
        --no-wait
    
    echo "⏳ Waiting for OpenAI deployment to complete..."
    while true; do
        STATE=$(az deployment group show -g "$RESOURCE_GROUP" -n "$STAGE2_DEPLOYMENT_NAME" --query "properties.provisioningState" -o tsv 2>/dev/null)
        if [ "$STATE" = "Succeeded" ]; then
            echo "✅ Azure OpenAI deployed"
            break
        elif [ "$STATE" = "Failed" ] || [ "$STATE" = "Canceled" ]; then
            echo "❌ OpenAI deployment failed with state: $STATE"
            exit 1
        fi
        echo "   State: $STATE - waiting..."
        sleep 10
    done
fi

echo "✅ Azure OpenAI deployed"
echo ""

# Stage 3: Featureform (Optional - Feature Store)
echo "🏪 Stage 3: Featureform Feature Store..."
echo "   This stage deploys Featureform to Azure Container Apps"
echo "   Do you want to deploy Featureform now? (y/N)"
read -t 10 -r DEPLOY_FEATUREFORM || DEPLOY_FEATUREFORM="n"

if [ "$DEPLOY_FEATUREFORM" = "y" ] || [ "$DEPLOY_FEATUREFORM" = "Y" ]; then
    echo "   Deploying Featureform..."
    "$SCRIPT_DIR/deploy-featureform.sh" || {
        echo "⚠️  Featureform deployment failed, but continuing..."
    }
else
    echo "   Skipping Featureform deployment"
    echo "   You can deploy it later by running:"
    echo "   ./infra/scripts/deploy-featureform.sh"
fi
echo ""

echo "=========================================="
echo "✅ Infrastructure Deployment Complete!"
echo "=========================================="
echo ""
echo "📊 Current deployments:"
az deployment group list --resource-group "$RESOURCE_GROUP" --query "[].{Name:name, State:properties.provisioningState}" -o table
echo ""
echo "📦 Resources created:"
az resource list --resource-group "$RESOURCE_GROUP" --query "[].{Name:name, Type:type}" -o table
echo ""
echo "ℹ️  Note: Redis deployment may still be in progress. Check status with:"
echo "   az deployment group show -g $RESOURCE_GROUP -n stage1b-redis-* --query properties.provisioningState"
echo ""

# Optional: Apply Featureform definitions if VM exists
if az vm show -g "$RESOURCE_GROUP" -n "debug-vm-${RESOURCE_TOKEN}" &>/dev/null; then
    echo "=========================================="
    echo "📝 Apply Featureform Definitions"
    echo "=========================================="
    echo ""
    read -p "Would you like to apply Featureform definitions now? (yes/no): " apply_defs
    if [ "$apply_defs" = "yes" ]; then
        echo "🚀 Running connect-and-apply script..."
        "$SCRIPT_DIR/connect-and-apply.sh" || {
            echo "⚠️  Failed to apply definitions automatically"
            echo "You can run it manually later with:"
            echo "   ./infra/scripts/connect-and-apply.sh"
        }
    else
        echo "📋 To apply definitions later, run:"
        echo "   ./infra/scripts/connect-and-apply.sh"
    fi
else
    echo "🏪 To deploy Featureform later:"
    echo "   ./infra/scripts/deploy-featureform.sh"
    echo ""
    echo "📋 After deploying VM and Featureform, apply definitions with:"
    echo "   ./infra/scripts/connect-and-apply.sh"
fi
