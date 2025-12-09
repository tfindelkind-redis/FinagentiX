#!/bin/bash
set -e

# Deploy Debug Pod for VNet Access
# This creates a lightweight container that can access internal Azure resources

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Debug Pod Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get environment details
if command -v azd &> /dev/null && azd env list &> /dev/null; then
    AZURE_ENV_NAME=$(azd env get-value AZURE_ENV_NAME 2>/dev/null || echo "dev")
    RESOURCE_GROUP="finagentix-${AZURE_ENV_NAME}-rg"
else
    AZURE_ENV_NAME="${AZURE_ENV_NAME:-dev}"
    RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-finagentix-${AZURE_ENV_NAME}-rg}"
fi

LOCATION="${AZURE_LOCATION:-westus3}"

# Get resource token
echo -e "${BLUE}📋 Retrieving resource token...${NC}"
RESOURCE_TOKEN=$(az deployment group list -g "$RESOURCE_GROUP" --query "[?contains(name, 'stage0')].properties.parameters.resourceToken.value | [0]" -o tsv 2>/dev/null)

if [ -z "$RESOURCE_TOKEN" ] || [ "$RESOURCE_TOKEN" == "null" ]; then
    echo -e "${YELLOW}❌ Could not find resource token. Infrastructure not deployed?${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Resource token: $RESOURCE_TOKEN${NC}"
echo ""

# Get debug subnet ID (dedicated for Container Instances)
echo -e "${BLUE}📋 Getting subnet information...${NC}"
SUBNET_ID=$(az network vnet subnet show \
    -g "$RESOURCE_GROUP" \
    --vnet-name "vnet-${RESOURCE_TOKEN}" \
    -n debug-subnet \
    --query id -o tsv 2>/dev/null)

if [ -z "$SUBNET_ID" ]; then
    echo -e "${YELLOW}⚠️  Debug subnet doesn't exist, creating it...${NC}"
    az deployment group create \
        -g "$RESOURCE_GROUP" \
        --template-file "$INFRA_DIR/modules/debug-subnet.bicep" \
        --parameters vnetName="vnet-${RESOURCE_TOKEN}" \
        --name "debug-subnet-$(date +%s)" \
        --no-wait
    sleep 15
    SUBNET_ID=$(az network vnet subnet show -g "$RESOURCE_GROUP" --vnet-name "vnet-${RESOURCE_TOKEN}" -n debug-subnet --query id -o tsv)
fi

echo -e "${GREEN}✅ Subnet ID retrieved${NC}"
echo ""

# Check if debug pod already exists
DEBUG_POD_NAME="debug-pod-${RESOURCE_TOKEN}"
EXISTING_POD=$(az container show -g "$RESOURCE_GROUP" -n "$DEBUG_POD_NAME" --query name -o tsv 2>/dev/null || echo "")

if [ -n "$EXISTING_POD" ]; then
    echo -e "${YELLOW}⚠️  Debug pod already exists${NC}"
    echo -e "${YELLOW}   Do you want to delete and recreate it? (y/N)${NC}"
    read -r CONFIRM
    if [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ]; then
        echo -e "${BLUE}Deleting existing debug pod...${NC}"
        az container delete -g "$RESOURCE_GROUP" -n "$DEBUG_POD_NAME" --yes || true
        sleep 10
    else
        echo -e "${BLUE}ℹ️  Using existing debug pod${NC}"
        echo ""
        echo -e "${GREEN}To connect:${NC}"
        echo "  az container exec -g $RESOURCE_GROUP -n $DEBUG_POD_NAME --exec-command /bin/bash"
        exit 0
    fi
fi

# Deploy debug pod
echo -e "${BLUE}🚀 Deploying debug pod (async)...${NC}"
DEPLOYMENT_NAME="debug-pod-$(date +%s)"

az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$INFRA_DIR/modules/debug-pod.bicep" \
    --parameters \
        location="$LOCATION" \
        resourceToken="$RESOURCE_TOKEN" \
        subnetId="$SUBNET_ID" \
    --name "$DEPLOYMENT_NAME" \
    --no-wait \
    --no-prompt true

echo ""
echo -e "${GREEN}✅ Deployment started (non-blocking)${NC}"
echo ""
echo -e "${BLUE}Debug Pod Name:${NC} $DEBUG_POD_NAME"
echo -e "${BLUE}Resource Group:${NC} $RESOURCE_GROUP"
echo ""
echo -e "${YELLOW}📋 Check deployment status:${NC}"
echo "  az deployment group show -g $RESOURCE_GROUP -n $DEPLOYMENT_NAME --query properties.provisioningState -o tsv"
echo ""
echo -e "${YELLOW}🔗 Once deployed, connect with:${NC}"
echo "  az container exec -g $RESOURCE_GROUP -n $DEBUG_POD_NAME --exec-command /bin/bash"
echo ""
echo -e "${GREEN}💡 The deployment takes 2-3 minutes. Check status before connecting.${NC}"
