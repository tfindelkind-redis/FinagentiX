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
DEPLOY_DATA_INGESTION=${DEPLOY_DATA_INGESTION:-false}
BUILD_CONTAINER_IMAGES=${BUILD_CONTAINER_IMAGES:-true}
BUILD_FRONTEND_IMAGE=${BUILD_FRONTEND_IMAGE:-true}
REDEPLOY_STAGE3=${REDEPLOY_STAGE3:-false}
REDEPLOY_STAGE4=${REDEPLOY_STAGE4:-false}
REDEPLOY_STAGE5=${REDEPLOY_STAGE5:-false}

echo "=========================================="
echo "FinagentiX Infrastructure Deployment"
echo "=========================================="
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "Environment: ${AZURE_ENV_NAME}"
echo "Resource Token: $RESOURCE_TOKEN"
echo "Deploy Data Ingestion App: $DEPLOY_DATA_INGESTION"
echo "Build API Image: $BUILD_CONTAINER_IMAGES"
echo "Build Frontend Image: $BUILD_FRONTEND_IMAGE"
echo "Redeploy Stage3: $REDEPLOY_STAGE3"
echo "Redeploy Stage4: $REDEPLOY_STAGE4"
echo "Redeploy Stage5: $REDEPLOY_STAGE5"
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
LOG_ANALYTICS_WORKSPACE_ID=$(echo "$STAGE0_OUTPUTS" | jq -r '.logAnalyticsWorkspaceId.value')
APPLICATION_INSIGHTS_CONNECTION_STRING=$(echo "$STAGE0_OUTPUTS" | jq -r '.applicationInsightsConnectionString.value')

echo "✅ Stage 0 outputs retrieved"
echo ""

# Stage 1a: Storage
EXISTING_STAGE1A=$(az deployment group list -g "$RESOURCE_GROUP" --query "[?contains(name, 'stage1a-storage') && properties.provisioningState=='Succeeded'] | [0].name" -o tsv 2>/dev/null)

if [ -n "$EXISTING_STAGE1A" ] && [ "$EXISTING_STAGE1A" != "null" ]; then
    echo "ℹ️  Stage 1a already deployed: $EXISTING_STAGE1A"
    echo "   Skipping Stage 1a deployment..."
    STAGE1A_DEPLOYMENT_NAME="$EXISTING_STAGE1A"
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
    STAGE1B_DEPLOYMENT_NAME="$EXISTING_STAGE1B"
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
    STAGE2_DEPLOYMENT_NAME="$EXISTING_STAGE2"
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

# Retrieve Stage 1 outputs
echo "📋 Retrieving Stage 1 outputs..."
STAGE1A_OUTPUTS=$(az deployment group show -g "$RESOURCE_GROUP" -n "$STAGE1A_DEPLOYMENT_NAME" --query "properties.outputs" -o json)
STAGE1B_OUTPUTS=$(az deployment group show -g "$RESOURCE_GROUP" -n "$STAGE1B_DEPLOYMENT_NAME" --query "properties.outputs" -o json)

STORAGE_ACCOUNT_NAME=$(echo "$STAGE1A_OUTPUTS" | jq -r '.storageAccountName.value')
REDIS_HOST=$(echo "$STAGE1B_OUTPUTS" | jq -r '.redisHostName.value')
REDIS_PORT=$(echo "$STAGE1B_OUTPUTS" | jq -r '.redisPort.value')

REDIS_CLUSTER_ID=$(az redisenterprise show \
    --resource-group "$RESOURCE_GROUP" \
    --name "redis-${RESOURCE_TOKEN}" \
    --query id -o tsv)

REDIS_DATABASE_ID="${REDIS_CLUSTER_ID%$'\r'}/databases/default"

REDIS_PASSWORD=$(az redisenterprise database list-keys \
    --ids "$REDIS_DATABASE_ID" \
    --query "primaryKey" -o tsv)

echo "📋 Retrieving Stage 2 outputs..."
STAGE2_OUTPUTS=$(az deployment group show -g "$RESOURCE_GROUP" -n "$STAGE2_DEPLOYMENT_NAME" --query "properties.outputs" -o json)
OPENAI_ENDPOINT=$(echo "$STAGE2_OUTPUTS" | jq -r '.openaiEndpoint.value')
OPENAI_RESOURCE_NAME=$(echo "$STAGE2_OUTPUTS" | jq -r '.openaiName.value')
OPENAI_KEY=$(az cognitiveservices account keys list \
    --name "$OPENAI_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "key1" -o tsv)
OPENAI_GPT4_DEPLOYMENT=$(echo "$STAGE2_OUTPUTS" | jq -r '.gpt4DeploymentName.value // empty')
OPENAI_EMBEDDING_DEPLOYMENT=$(echo "$STAGE2_OUTPUTS" | jq -r '.embeddingDeploymentName.value // empty')
OPENAI_API_VERSION="${AZURE_OPENAI_API_VERSION:-2024-08-01-preview}"

if [ -z "$OPENAI_KEY" ] || [ "$OPENAI_KEY" = "null" ]; then
    echo "❌ Unable to retrieve Azure OpenAI key"
    exit 1
fi

# Stage 3: Container Apps environment and registry
EXISTING_STAGE3=$(az deployment group list -g "$RESOURCE_GROUP" --query "[?contains(name, 'stage3-data-ingestion') && properties.provisioningState=='Succeeded'] | [0].name" -o tsv 2>/dev/null)

if [ -n "$EXISTING_STAGE3" ] && [ "$EXISTING_STAGE3" != "null" ] && [ "$REDEPLOY_STAGE3" != "true" ]; then
    echo "ℹ️  Stage 3 already deployed: $EXISTING_STAGE3"
    echo "   Skipping Stage 3 deployment..."
    STAGE3_DEPLOYMENT_NAME="$EXISTING_STAGE3"
else
    if [ "$REDEPLOY_STAGE3" = "true" ] && [ -n "$EXISTING_STAGE3" ] && [ "$EXISTING_STAGE3" != "null" ]; then
        echo "♻️  Redeploying Stage 3 as requested..."
    else
        echo "🛠️  Stage 3: Deploying Container Apps environment and registry..."
    fi
    STAGE3_DEPLOYMENT_NAME="stage3-data-ingestion-$(date +%s)"

    az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$INFRA_DIR/stages/stage3-data-ingestion.bicep" \
        --parameters \
            environmentName="${AZURE_ENV_NAME}" \
            location="$LOCATION" \
            resourceToken="$RESOURCE_TOKEN" \
            containerAppsSubnetId="$CONTAINER_APPS_SUBNET_ID" \
            logAnalyticsWorkspaceId="$LOG_ANALYTICS_WORKSPACE_ID" \
            applicationInsightsConnectionString="$APPLICATION_INSIGHTS_CONNECTION_STRING" \
            redisHost="$REDIS_HOST" \
            redisPort="$REDIS_PORT" \
            redisPassword="$REDIS_PASSWORD" \
            storageAccountName="$STORAGE_ACCOUNT_NAME" \
            openaiEndpoint="$OPENAI_ENDPOINT" \
            openaiKey="$OPENAI_KEY" \
            openaiGpt4Deployment="$OPENAI_GPT4_DEPLOYMENT" \
            openaiEmbeddingDeployment="$OPENAI_EMBEDDING_DEPLOYMENT" \
            openaiApiVersion="$OPENAI_API_VERSION" \
            deployDataIngestionApp=$DEPLOY_DATA_INGESTION \
        --name "$STAGE3_DEPLOYMENT_NAME" \
        --no-prompt true \
        --output table
    echo "✅ Stage 3 deployed"
fi

STAGE3_OUTPUTS=$(az deployment group show -g "$RESOURCE_GROUP" -n "$STAGE3_DEPLOYMENT_NAME" --query "properties.outputs" -o json)
CONTAINER_APPS_ENVIRONMENT_ID=$(echo "$STAGE3_OUTPUTS" | jq -r '.containerAppsEnvironmentId.value')
CONTAINER_REGISTRY_NAME=$(echo "$STAGE3_OUTPUTS" | jq -r '.containerRegistryName.value')
CONTAINER_REGISTRY_LOGIN_SERVER=$(echo "$STAGE3_OUTPUTS" | jq -r '.containerRegistryLoginServer.value')
INGESTION_URL=$(echo "$STAGE3_OUTPUTS" | jq -r '.ingestionUrl.value // empty')

echo "📦 Container Apps Environment: $CONTAINER_APPS_ENVIRONMENT_ID"
echo "📦 Container Registry: $CONTAINER_REGISTRY_NAME"
if [ -n "$INGESTION_URL" ]; then
    echo "🛰️  Data Ingestion App: $INGESTION_URL"
fi

if [ "$BUILD_CONTAINER_IMAGES" = "true" ]; then
    echo "🔨 Building container image for FinagentiX API..."
    az acr build \
        --registry "$CONTAINER_REGISTRY_NAME" \
        --image finagentix/agent-api:latest \
        --file docker/api.Dockerfile \
        .
else
    echo "⏭️  Skipping container image build (BUILD_CONTAINER_IMAGES=false)"
fi

# Stage 4: Agent runtime container app
EXISTING_STAGE4=$(az deployment group list -g "$RESOURCE_GROUP" --query "[?contains(name, 'stage4-agent-runtime') && properties.provisioningState=='Succeeded'] | [0].name" -o tsv 2>/dev/null)

if [ -n "$EXISTING_STAGE4" ] && [ "$EXISTING_STAGE4" != "null" ] && [ "$REDEPLOY_STAGE4" != "true" ]; then
    echo "ℹ️  Stage 4 already deployed: $EXISTING_STAGE4"
    echo "   Skipping Stage 4 deployment..."
else
    if [ "$REDEPLOY_STAGE4" = "true" ] && [ -n "$EXISTING_STAGE4" ] && [ "$EXISTING_STAGE4" != "null" ]; then
        echo "♻️  Redeploying Stage 4 as requested..."
    else
        echo "🎯 Stage 4: Deploying Agent API Container App..."
    fi
    STAGE4_DEPLOYMENT_NAME="stage4-agent-runtime-$(date +%s)"

    az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$INFRA_DIR/stages/stage4-agent-runtime.bicep" \
        --parameters \
            environmentName="${AZURE_ENV_NAME}" \
            location="$LOCATION" \
            resourceToken="$RESOURCE_TOKEN" \
            containerAppsSubnetId="$CONTAINER_APPS_SUBNET_ID" \
            logAnalyticsWorkspaceId="$LOG_ANALYTICS_WORKSPACE_ID" \
            applicationInsightsConnectionString="$APPLICATION_INSIGHTS_CONNECTION_STRING" \
            redisHost="$REDIS_HOST" \
            redisPort="$REDIS_PORT" \
            redisPassword="$REDIS_PASSWORD" \
            openaiEndpoint="$OPENAI_ENDPOINT" \
            openaiKey="$OPENAI_KEY" \
            openaiGpt4Deployment="$OPENAI_GPT4_DEPLOYMENT" \
            openaiEmbeddingDeployment="$OPENAI_EMBEDDING_DEPLOYMENT" \
            openaiApiVersion="$OPENAI_API_VERSION" \
        --name "$STAGE4_DEPLOYMENT_NAME" \
        --no-prompt true \
        --output table

    echo "✅ Stage 4 deployed"
fi

API_FQDN=$(az containerapp show \
    --name "ca-agent-api-${RESOURCE_TOKEN}" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")

if [ -n "$API_FQDN" ]; then
    echo "🌐 Agent API available at: https://$API_FQDN"
else
    echo "⚠️  Unable to determine Agent API endpoint automatically."
fi

echo ""

FRONTEND_API_URL="https://${API_FQDN:-ca-agent-api-${RESOURCE_TOKEN}.${LOCATION}.azurecontainerapps.io}"

if [ "$BUILD_FRONTEND_IMAGE" = "true" ]; then
    echo "🔨 Building container image for FinagentiX Frontend..."
    az acr build \
        --registry "$CONTAINER_REGISTRY_NAME" \
        --image finagentix/frontend:latest \
        --file docker/frontend.Dockerfile \
        --build-arg VITE_API_URL="$FRONTEND_API_URL" \
        .
else
    echo "⏭️  Skipping frontend image build (BUILD_FRONTEND_IMAGE=false)"
fi

# Stage 5: Web frontend container app
EXISTING_STAGE5=$(az deployment group list -g "$RESOURCE_GROUP" --query "[?contains(name, 'stage5-web-frontend') && properties.provisioningState=='Succeeded'] | [0].name" -o tsv 2>/dev/null)

if [ -n "$EXISTING_STAGE5" ] && [ "$EXISTING_STAGE5" != "null" ] && [ "$REDEPLOY_STAGE5" != "true" ]; then
    echo "ℹ️  Stage 5 already deployed: $EXISTING_STAGE5"
else
    if [ "$REDEPLOY_STAGE5" = "true" ] && [ -n "$EXISTING_STAGE5" ] && [ "$EXISTING_STAGE5" != "null" ]; then
        echo "♻️  Redeploying Stage 5 as requested..."
    else
        echo "🖥️  Stage 5: Deploying Web Frontend..."
    fi
    STAGE5_DEPLOYMENT_NAME="stage5-web-frontend-$(date +%s)"

    az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$INFRA_DIR/stages/stage5-web-frontend.bicep" \
        --parameters \
            environmentName="${AZURE_ENV_NAME}" \
            location="$LOCATION" \
            resourceToken="$RESOURCE_TOKEN" \
            containerAppsEnvironmentId="$CONTAINER_APPS_ENVIRONMENT_ID" \
            containerRegistryName="$CONTAINER_REGISTRY_NAME" \
            containerRegistryLoginServer="$CONTAINER_REGISTRY_LOGIN_SERVER" \
            applicationInsightsConnectionString="$APPLICATION_INSIGHTS_CONNECTION_STRING" \
            apiBaseUrl="$FRONTEND_API_URL" \
        --name "$STAGE5_DEPLOYMENT_NAME" \
        --no-prompt true \
        --output table

    echo "✅ Stage 5 deployed"
fi

FRONTEND_APP_NAME="ca-frontend-${RESOURCE_TOKEN}"
FRONTEND_FQDN=$(az containerapp show \
    --name "$FRONTEND_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")

if [ -n "$FRONTEND_FQDN" ]; then
    echo "🖥️  Frontend available at: https://$FRONTEND_FQDN"
fi

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
    echo "🚀 Applying Featureform definitions automatically..."
    if ! "$SCRIPT_DIR/connect-and-apply.sh"; then
        echo "⚠️  Failed to apply definitions automatically"
        echo "   You can rerun the process with:"
        echo "   ./infra/scripts/connect-and-apply.sh"
    fi
else
    echo "🏪 To deploy Featureform later:"
    echo "   ./infra/scripts/deploy-featureform.sh"
    echo ""
    echo "📋 After deploying VM and Featureform, apply definitions with:"
    echo "   ./infra/scripts/connect-and-apply.sh"
fi
