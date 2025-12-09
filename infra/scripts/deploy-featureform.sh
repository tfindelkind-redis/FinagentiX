#!/bin/bash
set -e

# FinagentiX Featureform Deployment Script
# This script deploys Featureform to Azure Container Apps
# It handles Container Apps Environment creation and Featureform app deployment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Use azd environment if available, otherwise use defaults
if command -v azd &> /dev/null && azd env list &> /dev/null; then
    echo -e "${BLUE}ℹ️  Using azd environment${NC}"
    AZURE_ENV_NAME=$(azd env get-value AZURE_ENV_NAME 2>/dev/null || echo "dev")
    AZURE_LOCATION=$(azd env get-value AZURE_LOCATION 2>/dev/null || echo "westus3")
    RESOURCE_GROUP="finagentix-${AZURE_ENV_NAME}-rg"
else
    echo -e "${BLUE}ℹ️  azd not configured, using environment variables or defaults${NC}"
    AZURE_ENV_NAME="${AZURE_ENV_NAME:-dev}"
    AZURE_LOCATION="${AZURE_LOCATION:-westus3}"
    RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-finagentix-${AZURE_ENV_NAME}-rg}"
fi

LOCATION="$AZURE_LOCATION"

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}Featureform Deployment${NC}"
echo -e "${BLUE}==========================================${NC}"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "Environment: ${AZURE_ENV_NAME}"
echo ""

# Get resource token from existing deployments
echo -e "${BLUE}📋 Retrieving resource token...${NC}"
RESOURCE_TOKEN=$(az deployment group list -g "$RESOURCE_GROUP" --query "[?contains(name, 'stage0')].properties.parameters.resourceToken.value | [0]" -o tsv 2>/dev/null)

if [ -z "$RESOURCE_TOKEN" ] || [ "$RESOURCE_TOKEN" == "null" ]; then
    echo -e "${RED}❌ Could not find resource token. Make sure Stage 0 (Foundation) is deployed first.${NC}"
    echo "   Run: ./infra/scripts/deploy.sh"
    exit 1
fi

echo -e "${GREEN}✅ Resource token: $RESOURCE_TOKEN${NC}"
echo ""

# Check if Container Apps Environment exists and is healthy
echo -e "${BLUE}🔍 Checking Container Apps Environment status...${NC}"
CAE_NAME="cae-${RESOURCE_TOKEN}"
CAE_EXISTS=$(az containerapp env show -g "$RESOURCE_GROUP" -n "$CAE_NAME" --query "name" -o tsv 2>/dev/null || echo "")
CAE_STATE=$(az containerapp env show -g "$RESOURCE_GROUP" -n "$CAE_NAME" --query "properties.provisioningState" -o tsv 2>/dev/null || echo "NotFound")

if [ -n "$CAE_EXISTS" ] && [ "$CAE_STATE" == "Succeeded" ]; then
    echo -e "${GREEN}✅ Container Apps Environment exists and is healthy: $CAE_NAME${NC}"
elif [ -n "$CAE_EXISTS" ] && [ "$CAE_STATE" == "Failed" ]; then
    echo -e "${YELLOW}⚠️  Container Apps Environment exists but is in Failed state${NC}"
    echo -e "${YELLOW}   Deleting failed environment...${NC}"
    az containerapp env delete -g "$RESOURCE_GROUP" -n "$CAE_NAME" --yes || true
    sleep 10
    CAE_EXISTS=""
    CAE_STATE="NotFound"
else
    echo -e "${YELLOW}ℹ️  Container Apps Environment not found${NC}"
fi

# Create Container Apps Environment if needed
if [ -z "$CAE_EXISTS" ] || [ "$CAE_STATE" != "Succeeded" ]; then
    echo -e "${BLUE}🏗️  Creating Container Apps Environment...${NC}"
    
    # Get required resource IDs
    LOG_ANALYTICS_ID=$(az monitor log-analytics workspace show -g "$RESOURCE_GROUP" -n "log-${RESOURCE_TOKEN}" --query customerId -o tsv)
    LOG_ANALYTICS_KEY=$(az monitor log-analytics workspace get-shared-keys -g "$RESOURCE_GROUP" -n "log-${RESOURCE_TOKEN}" --query primarySharedKey -o tsv)
    SUBNET_ID=$(az network vnet subnet show -g "$RESOURCE_GROUP" --vnet-name "vnet-${RESOURCE_TOKEN}" -n container-apps-subnet --query id -o tsv)
    
    # Create internal-only environment to avoid public IP quota issues
    echo -e "${YELLOW}⚠️  Creating internal-only environment to avoid public IP quota${NC}"
    echo -e "${YELLOW}   This means Featureform will only be accessible from within the VNet${NC}"
    
    az containerapp env create \
        --name "$CAE_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --logs-destination log-analytics \
        --logs-workspace-id "$LOG_ANALYTICS_ID" \
        --logs-workspace-key "$LOG_ANALYTICS_KEY" \
        --infrastructure-subnet-resource-id "$SUBNET_ID" \
        --internal-only true \
        --output none
    
    echo -e "${GREEN}✅ Container Apps Environment created${NC}"
    
    # Wait for environment to be ready
    echo -e "${BLUE}⏳ Waiting for environment to be provisioned...${NC}"
    for i in {1..60}; do
        CAE_STATE=$(az containerapp env show -g "$RESOURCE_GROUP" -n "$CAE_NAME" --query "properties.provisioningState" -o tsv 2>/dev/null || echo "NotFound")
        if [ "$CAE_STATE" == "Succeeded" ]; then
            echo -e "${GREEN}✅ Container Apps Environment is ready${NC}"
            break
        elif [ "$CAE_STATE" == "Failed" ]; then
            echo -e "${RED}❌ Container Apps Environment creation failed${NC}"
            az containerapp env show -g "$RESOURCE_GROUP" -n "$CAE_NAME" --query "properties.deploymentErrors" -o json
            exit 1
        fi
        echo -n "."
        sleep 5
    done
    echo ""
fi

# Check if Featureform app already exists
echo -e "${BLUE}🔍 Checking if Featureform app exists...${NC}"
FEATUREFORM_NAME="featureform-${RESOURCE_TOKEN}"
FEATUREFORM_EXISTS=$(az containerapp show -g "$RESOURCE_GROUP" -n "$FEATUREFORM_NAME" --query "name" -o tsv 2>/dev/null || echo "")

if [ -n "$FEATUREFORM_EXISTS" ]; then
    echo -e "${YELLOW}⚠️  Featureform app already exists${NC}"
    echo -e "${YELLOW}   Do you want to update it? (y/N)${NC}"
    read -r CONFIRM
    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        echo -e "${BLUE}ℹ️  Skipping Featureform deployment${NC}"
        
        # Show current URL
        FEATUREFORM_URL=$(az containerapp show -g "$RESOURCE_GROUP" -n "$FEATUREFORM_NAME" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null)
        if [ -n "$FEATUREFORM_URL" ]; then
            echo -e "${GREEN}✅ Featureform URL: https://${FEATUREFORM_URL}${NC}"
        fi
        exit 0
    fi
    
    # Delete existing app for clean redeployment
    echo -e "${YELLOW}Deleting existing Featureform app...${NC}"
    az containerapp delete -g "$RESOURCE_GROUP" -n "$FEATUREFORM_NAME" --yes || true
    sleep 10
fi

# Get Redis password
echo -e "${BLUE}🔑 Retrieving Redis password...${NC}"
REDIS_PASSWORD=$(az redisenterprise database list-keys -g "$RESOURCE_GROUP" --cluster-name "redis-${RESOURCE_TOKEN}" --query "primaryKey" -o tsv)

if [ -z "$REDIS_PASSWORD" ]; then
    echo -e "${RED}❌ Could not retrieve Redis password${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Redis password retrieved${NC}"
echo ""

# Deploy Featureform using Bicep
echo -e "${BLUE}🚀 Deploying Featureform Container App...${NC}"
DEPLOYMENT_NAME="featureform-deployment-$(date +%s)"

az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$INFRA_DIR/deploy-featureform-final.bicep" \
    --parameters \
        location="$LOCATION" \
        resourceToken="$RESOURCE_TOKEN" \
        redisPassword="$REDIS_PASSWORD" \
    --name "$DEPLOYMENT_NAME" \
    --no-prompt true

DEPLOYMENT_STATE=$(az deployment group show -g "$RESOURCE_GROUP" -n "$DEPLOYMENT_NAME" --query "properties.provisioningState" -o tsv)

if [ "$DEPLOYMENT_STATE" == "Succeeded" ]; then
    echo -e "${GREEN}✅ Featureform deployed successfully${NC}"
    echo ""
    
    # Get Featureform URL
    FEATUREFORM_URL=$(az deployment group show -g "$RESOURCE_GROUP" -n "$DEPLOYMENT_NAME" --query "properties.outputs.featureformUrl.value" -o tsv)
    
    echo -e "${GREEN}==========================================${NC}"
    echo -e "${GREEN}🎉 Featureform Deployment Complete!${NC}"
    echo -e "${GREEN}==========================================${NC}"
    echo ""
    echo -e "${GREEN}Featureform URL: $FEATUREFORM_URL${NC}"
    echo ""
    
    # Check if debug VM exists to apply definitions
    if az vm show -g "$RESOURCE_GROUP" -n "debug-vm-${RESOURCE_TOKEN}" &>/dev/null; then
        echo ""
        echo -e "${BLUE}========================================${NC}"
        echo -e "${BLUE}📝 Apply Featureform Definitions${NC}"
        echo -e "${BLUE}========================================${NC}"
        echo ""
        read -p "Would you like to apply Featureform definitions now? (yes/no): " apply_defs
        if [ "$apply_defs" = "yes" ]; then
            echo "🚀 Running connect-and-apply script..."
            SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
            "$SCRIPT_DIR/connect-and-apply.sh" || {
                echo "⚠️  Failed to apply definitions automatically"
                echo "You can run it manually later with:"
                echo "   ./infra/scripts/connect-and-apply.sh"
            }
        else
            echo ""
            echo -e "${BLUE}ℹ️  To apply definitions later, run:${NC}"
            echo "   ./infra/scripts/connect-and-apply.sh"
        fi
    else
        echo ""
        echo -e "${BLUE}ℹ️  Next steps:${NC}"
        echo "   1. Deploy debug VM:"
        echo "      ./infra/scripts/deploy-debug-vm.sh"
        echo ""
        echo "   2. Apply feature definitions:"
        echo "      ./infra/scripts/connect-and-apply.sh"
    fi
    echo ""
else
    echo -e "${RED}❌ Featureform deployment failed with state: $DEPLOYMENT_STATE${NC}"
    echo ""
    echo "Deployment errors:"
    az deployment group show -g "$RESOURCE_GROUP" -n "$DEPLOYMENT_NAME" --query "properties.error" -o json
    exit 1
fi
