#!/bin/bash
# Enable Azure OpenAI public access for local development
# This script updates the Azure OpenAI network rules to allow access from your current IP

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "Azure OpenAI Development Access Configuration"
echo "=============================================="
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed${NC}"
    echo "Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}Not logged in to Azure. Running 'az login'...${NC}"
    az login
fi

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Get resource group and OpenAI resource name
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-finagentix-dev-rg}"

# Find the OpenAI resource
echo "Looking for Azure OpenAI resource in ${RESOURCE_GROUP}..."
OPENAI_NAME=$(az cognitiveservices account list -g "$RESOURCE_GROUP" --query "[?kind=='OpenAI'].name" -o tsv 2>/dev/null)

if [ -z "$OPENAI_NAME" ]; then
    echo -e "${RED}Error: No Azure OpenAI resource found in resource group ${RESOURCE_GROUP}${NC}"
    exit 1
fi

echo -e "${GREEN}Found OpenAI resource: ${OPENAI_NAME}${NC}"

# Get current public IP
echo ""
echo "Detecting your public IP address..."
MY_IP=$(curl -s https://api.ipify.org)

if [ -z "$MY_IP" ]; then
    echo -e "${RED}Error: Could not detect your public IP address${NC}"
    exit 1
fi

echo -e "${GREEN}Your public IP: ${MY_IP}${NC}"

# Check current network settings
echo ""
echo "Current Azure OpenAI network settings:"
az cognitiveservices account show \
    -g "$RESOURCE_GROUP" \
    -n "$OPENAI_NAME" \
    --query "{PublicAccess:properties.publicNetworkAccess, DefaultAction:properties.networkAcls.defaultAction, IpRules:properties.networkAcls.ipRules}" \
    -o table

echo ""
echo "Choose an option:"
echo "  1) Enable public access from your IP only (${MY_IP})"
echo "  2) Enable public access from all networks (less secure)"
echo "  3) Disable public access (use private endpoint only)"
echo "  4) Exit without changes"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}Enabling public access from ${MY_IP}...${NC}"
        
        # Enable public access with IP rule
        az cognitiveservices account update \
            -g "$RESOURCE_GROUP" \
            -n "$OPENAI_NAME" \
            --public-network-access Enabled \
            --custom-domain "$OPENAI_NAME"
        
        # Add IP rule
        az cognitiveservices account network-rule add \
            -g "$RESOURCE_GROUP" \
            -n "$OPENAI_NAME" \
            --ip-address "${MY_IP}"
        
        echo -e "${GREEN}✅ Public access enabled from ${MY_IP}${NC}"
        ;;
    2)
        echo ""
        echo -e "${YELLOW}WARNING: This will allow access from any network!${NC}"
        read -p "Are you sure? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            az cognitiveservices account update \
                -g "$RESOURCE_GROUP" \
                -n "$OPENAI_NAME" \
                --public-network-access Enabled
            
            # Remove network ACLs by setting default action to Allow
            az cognitiveservices account network-rule list \
                -g "$RESOURCE_GROUP" \
                -n "$OPENAI_NAME" \
                --query "ipRules[].value" -o tsv | while read ip; do
                    az cognitiveservices account network-rule remove \
                        -g "$RESOURCE_GROUP" \
                        -n "$OPENAI_NAME" \
                        --ip-address "$ip" 2>/dev/null || true
            done
            
            echo -e "${GREEN}✅ Public access enabled from all networks${NC}"
        else
            echo "Cancelled."
        fi
        ;;
    3)
        echo ""
        echo -e "${YELLOW}Disabling public access...${NC}"
        az cognitiveservices account update \
            -g "$RESOURCE_GROUP" \
            -n "$OPENAI_NAME" \
            --public-network-access Disabled
        
        echo -e "${GREEN}✅ Public access disabled. Use private endpoint to access.${NC}"
        ;;
    4)
        echo "No changes made."
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo "Updated network settings:"
az cognitiveservices account show \
    -g "$RESOURCE_GROUP" \
    -n "$OPENAI_NAME" \
    --query "{PublicAccess:properties.publicNetworkAccess, DefaultAction:properties.networkAcls.defaultAction, IpRules:properties.networkAcls.ipRules}" \
    -o table

echo ""
echo "=============================================="
echo "Testing Azure OpenAI connection..."
echo "=============================================="

# Get endpoint
ENDPOINT=$(az cognitiveservices account show -g "$RESOURCE_GROUP" -n "$OPENAI_NAME" --query "properties.endpoint" -o tsv)

# Quick connectivity test
if curl -s --connect-timeout 5 "$ENDPOINT" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Azure OpenAI endpoint is reachable${NC}"
else
    echo -e "${YELLOW}⚠️  Azure OpenAI endpoint may not be reachable yet. Wait a few minutes for DNS propagation.${NC}"
fi

echo ""
echo "Done! You can now run your agents locally."
