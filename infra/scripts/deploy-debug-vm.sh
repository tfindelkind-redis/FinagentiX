#!/bin/bash
set -e

# Deploy Debug VM for VNet Access
# Creates a small Linux VM with SSH access to internal resources

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Debug VM Deployment${NC}"
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
    echo -e "${YELLOW}❌ Could not find resource token${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Resource token: $RESOURCE_TOKEN${NC}"

# Get or create VM subnet (separate from Container Instance subnet)
echo -e "${BLUE}📋 Getting subnet information...${NC}"
SUBNET_ID=$(az network vnet subnet show \
    -g "$RESOURCE_GROUP" \
    --vnet-name "vnet-${RESOURCE_TOKEN}" \
    -n vm-subnet \
    --query id -o tsv 2>/dev/null)

if [ -z "$SUBNET_ID" ]; then
    echo -e "${YELLOW}⚠️  VM subnet doesn't exist, creating it...${NC}"
    az network vnet subnet create \
        -g "$RESOURCE_GROUP" \
        --vnet-name "vnet-${RESOURCE_TOKEN}" \
        -n vm-subnet \
        --address-prefixes 10.0.7.0/28 \
        --output none
    SUBNET_ID=$(az network vnet subnet show -g "$RESOURCE_GROUP" --vnet-name "vnet-${RESOURCE_TOKEN}" -n vm-subnet --query id -o tsv)
fi

echo -e "${GREEN}✅ Subnet ID retrieved${NC}"
echo ""

# Set admin credentials
ADMIN_USERNAME="azureuser"
ADMIN_PASSWORD="DebugVM2024!@#"

echo -e "${BLUE}📋 VM Configuration:${NC}"
echo "  Username: $ADMIN_USERNAME"
echo "  Password: $ADMIN_PASSWORD"
echo "  Size: Standard_B1s (1 vCPU, 1 GB RAM)"
echo "  Cost: ~\$7.59/month"
echo ""

# Check if VM already exists
VM_NAME="debug-vm-${RESOURCE_TOKEN}"
EXISTING_VM=$(az vm show -g "$RESOURCE_GROUP" -n "$VM_NAME" --query name -o tsv 2>/dev/null || echo "")

if [ -n "$EXISTING_VM" ]; then
    echo -e "${YELLOW}⚠️  Debug VM already exists${NC}"
    echo -e "${YELLOW}   Do you want to delete and recreate it? (y/N)${NC}"
    read -r CONFIRM
    if [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ]; then
        echo -e "${BLUE}Deleting existing VM...${NC}"
        az vm delete -g "$RESOURCE_GROUP" -n "$VM_NAME" --yes
        az network nic delete -g "$RESOURCE_GROUP" -n "${VM_NAME}-nic" --yes 2>/dev/null || true
        az network nsg delete -g "$RESOURCE_GROUP" -n "${VM_NAME}-nsg" --yes 2>/dev/null || true
        sleep 10
    else
        VM_IP=$(az vm show -g "$RESOURCE_GROUP" -n "$VM_NAME" -d --query privateIps -o tsv)
        echo -e "${BLUE}ℹ️  Using existing debug VM${NC}"
        echo ""
        echo -e "${GREEN}To connect:${NC}"
        echo "  ssh $ADMIN_USERNAME@$VM_IP"
        echo "  Password: $ADMIN_PASSWORD"
        exit 0
    fi
fi

# Deploy debug VM
echo -e "${BLUE}🚀 Deploying debug VM...${NC}"
DEPLOYMENT_NAME="debug-vm-$(date +%s)"

az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$INFRA_DIR/modules/debug-vm.bicep" \
    --parameters \
        location="$LOCATION" \
        resourceToken="$RESOURCE_TOKEN" \
        subnetId="$SUBNET_ID" \
        adminUsername="$ADMIN_USERNAME" \
        adminPassword="$ADMIN_PASSWORD" \
    --name "$DEPLOYMENT_NAME"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 Debug VM Deployed Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get outputs
PRIVATE_IP=$(az deployment group show -g "$RESOURCE_GROUP" -n "$DEPLOYMENT_NAME" --query "properties.outputs.privateIp.value" -o tsv)
PUBLIC_IP=$(az deployment group show -g "$RESOURCE_GROUP" -n "$DEPLOYMENT_NAME" --query "properties.outputs.publicIp.value" -o tsv)

echo -e "${GREEN}VM Details:${NC}"
echo "  Name: $VM_NAME"
echo "  Private IP: $PRIVATE_IP"
echo "  Public IP: $PUBLIC_IP"
echo "  Username: $ADMIN_USERNAME"
echo "  Password: $ADMIN_PASSWORD"
echo ""
echo -e "${GREEN}🔗 To connect:${NC}"
echo -e "${BLUE}  ssh $ADMIN_USERNAME@$PUBLIC_IP${NC}"
echo ""
echo -e "${YELLOW}⚠️  The NSG allows SSH from anywhere. Consider restricting to your IP.${NC}"
echo ""
echo -e "${BLUE}Cost: ~\$7.59/month while running, \$0 when stopped${NC}"
echo -e "${BLUE}To stop: az vm deallocate -g $RESOURCE_GROUP -n $VM_NAME${NC}"
echo -e "${BLUE}To start: az vm start -g $RESOURCE_GROUP -n $VM_NAME${NC}"
echo -e "${BLUE}To delete: az vm delete -g $RESOURCE_GROUP -n $VM_NAME --yes${NC}"
echo ""

# Check if Featureform is deployed to suggest applying definitions
if az containerapp show -g "$RESOURCE_GROUP" -n "featureform-${RESOURCE_TOKEN}" &>/dev/null; then
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
    echo -e "${BLUE}ℹ️  Next: Deploy Featureform and apply definitions${NC}"
    echo "   ./infra/scripts/deploy-featureform.sh"
    echo "   ./infra/scripts/connect-and-apply.sh"
fi
echo ""
