#!/bin/bash

# Show FinagentiX Deployment Information
# Displays all URLs, endpoints, and connection info for the deployed resources

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
AZURE_ENV_NAME="${AZURE_ENV_NAME:-dev}"
AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-finagentix-${AZURE_ENV_NAME}-rg}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}${BOLD}           FinagentiX Deployment Information                   ${NC}${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if logged in to Azure
if ! az account show &>/dev/null; then
    echo -e "${RED}❌ Not logged in to Azure. Run: az login${NC}"
    exit 1
fi

echo -e "${CYAN}📋 Resource Group:${NC} $AZURE_RESOURCE_GROUP"
echo ""

# Get resource token from deployed resources
RESOURCE_TOKEN=$(az vm list -g "$AZURE_RESOURCE_GROUP" --query "[?starts_with(name, 'debug-vm-')].name" -o tsv 2>/dev/null | sed 's/debug-vm-//' | head -n 1)

if [ -z "$RESOURCE_TOKEN" ]; then
    echo -e "${RED}❌ No deployed resources found in $AZURE_RESOURCE_GROUP${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Resource Token: $RESOURCE_TOKEN${NC}"
echo ""

# ============================================
# Debug VM
# ============================================
echo -e "${BLUE}┌──────────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC}${BOLD} 🖥️  Debug VM                                                     ${NC}${BLUE}│${NC}"
echo -e "${BLUE}└──────────────────────────────────────────────────────────────────┘${NC}"

VM_NAME="debug-vm-${RESOURCE_TOKEN}"
VM_PUBLIC_IP=$(az vm show -d -g "$AZURE_RESOURCE_GROUP" -n "$VM_NAME" --query "publicIps" -o tsv 2>/dev/null)

if [ -n "$VM_PUBLIC_IP" ]; then
    echo -e "  ${CYAN}Public IP:${NC}     $VM_PUBLIC_IP"
    echo -e "  ${CYAN}SSH Command:${NC}   ${GREEN}ssh azureuser@$VM_PUBLIC_IP${NC}"
    echo -e "  ${CYAN}Username:${NC}      azureuser"
else
    echo -e "  ${YELLOW}⚠️  VM not found or no public IP${NC}"
fi
echo ""

# ============================================
# Azure OpenAI
# ============================================
echo -e "${BLUE}┌──────────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC}${BOLD} 🤖 Azure OpenAI                                                  ${NC}${BLUE}│${NC}"
echo -e "${BLUE}└──────────────────────────────────────────────────────────────────┘${NC}"

OPENAI_NAME="openai-${RESOURCE_TOKEN}"
OPENAI_ENDPOINT=$(az cognitiveservices account show -g "$AZURE_RESOURCE_GROUP" -n "$OPENAI_NAME" --query "properties.endpoint" -o tsv 2>/dev/null)

if [ -n "$OPENAI_ENDPOINT" ]; then
    echo -e "  ${CYAN}Endpoint:${NC}      $OPENAI_ENDPOINT"
    echo -e "  ${CYAN}Resource:${NC}      $OPENAI_NAME"
    
    # List deployments
    echo -e "  ${CYAN}Deployments:${NC}"
    az cognitiveservices account deployment list -g "$AZURE_RESOURCE_GROUP" -n "$OPENAI_NAME" \
        --query "[].{name:name, model:properties.model.name, version:properties.model.version}" -o table 2>/dev/null | tail -n +3 | while read line; do
        echo "                   $line"
    done
else
    echo -e "  ${YELLOW}⚠️  Azure OpenAI not deployed${NC}"
fi
echo ""

# ============================================
# Redis Enterprise
# ============================================
echo -e "${BLUE}┌──────────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC}${BOLD} 🔴 Redis Enterprise                                              ${NC}${BLUE}│${NC}"
echo -e "${BLUE}└──────────────────────────────────────────────────────────────────┘${NC}"

REDIS_NAME="redis-${RESOURCE_TOKEN}"
REDIS_HOST=$(az redisenterprise show -g "$AZURE_RESOURCE_GROUP" -n "$REDIS_NAME" --query "hostName" -o tsv 2>/dev/null)

if [ -n "$REDIS_HOST" ]; then
    echo -e "  ${CYAN}Host:${NC}          $REDIS_HOST"
    echo -e "  ${CYAN}Port:${NC}          10000"
    echo -e "  ${CYAN}Resource:${NC}      $REDIS_NAME"
    
    # Get private endpoint IP if exists
    REDIS_PRIVATE_IP=$(az network private-endpoint list -g "$AZURE_RESOURCE_GROUP" \
        --query "[?contains(name, 'redis')].customDnsConfigs[0].ipAddresses[0]" -o tsv 2>/dev/null | head -n 1)
    if [ -n "$REDIS_PRIVATE_IP" ]; then
        echo -e "  ${CYAN}Private IP:${NC}    $REDIS_PRIVATE_IP"
    fi
else
    echo -e "  ${YELLOW}⚠️  Redis not deployed${NC}"
fi
echo ""

# ============================================
# Azure Storage
# ============================================
echo -e "${BLUE}┌──────────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC}${BOLD} 📦 Azure Storage                                                 ${NC}${BLUE}│${NC}"
echo -e "${BLUE}└──────────────────────────────────────────────────────────────────┘${NC}"

STORAGE_NAME=$(az storage account list -g "$AZURE_RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null)

if [ -n "$STORAGE_NAME" ]; then
    STORAGE_ENDPOINT=$(az storage account show -n "$STORAGE_NAME" --query "primaryEndpoints.blob" -o tsv 2>/dev/null)
    echo -e "  ${CYAN}Account:${NC}       $STORAGE_NAME"
    echo -e "  ${CYAN}Blob URL:${NC}      $STORAGE_ENDPOINT"
    
    # Show containers
    STORAGE_KEY=$(az storage account keys list -g "$AZURE_RESOURCE_GROUP" -n "$STORAGE_NAME" --query "[0].value" -o tsv 2>/dev/null)
    echo -e "  ${CYAN}Containers:${NC}"
    az storage container list --account-name "$STORAGE_NAME" --account-key "$STORAGE_KEY" \
        --query "[].name" -o tsv 2>/dev/null | while read container; do
        count=$(az storage blob list --container-name "$container" --account-name "$STORAGE_NAME" --account-key "$STORAGE_KEY" --query "length(@)" -o tsv 2>/dev/null)
        echo -e "                   📁 $container ($count blobs)"
    done
else
    echo -e "  ${YELLOW}⚠️  Storage not deployed${NC}"
fi
echo ""

# ============================================
# Application URLs (if deployed)
# ============================================
echo -e "${BLUE}┌──────────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC}${BOLD} 🌐 Application URLs                                              ${NC}${BLUE}│${NC}"
echo -e "${BLUE}└──────────────────────────────────────────────────────────────────┘${NC}"

# Check for Container Apps
API_URL=$(az containerapp list -g "$AZURE_RESOURCE_GROUP" --query "[?contains(name, 'api')].properties.configuration.ingress.fqdn" -o tsv 2>/dev/null | head -n 1)
FRONTEND_URL=$(az containerapp list -g "$AZURE_RESOURCE_GROUP" --query "[?contains(name, 'frontend')].properties.configuration.ingress.fqdn" -o tsv 2>/dev/null | head -n 1)

if [ -n "$API_URL" ]; then
    echo -e "  ${CYAN}API:${NC}           ${GREEN}https://$API_URL${NC}"
    echo -e "  ${CYAN}API Docs:${NC}      ${GREEN}https://$API_URL/docs${NC}"
    echo -e "  ${CYAN}API Health:${NC}    ${GREEN}https://$API_URL/health${NC}"
else
    echo -e "  ${YELLOW}⚠️  API Container App not deployed${NC}"
fi

if [ -n "$FRONTEND_URL" ]; then
    echo -e "  ${CYAN}Frontend:${NC}      ${GREEN}https://$FRONTEND_URL${NC}"
else
    echo -e "  ${YELLOW}⚠️  Frontend Container App not deployed${NC}"
fi

# Check for Static Web App
SWA_URL=$(az staticwebapp list -g "$AZURE_RESOURCE_GROUP" --query "[0].defaultHostname" -o tsv 2>/dev/null)
if [ -n "$SWA_URL" ]; then
    echo -e "  ${CYAN}Static Web:${NC}    ${GREEN}https://$SWA_URL${NC}"
fi
echo ""

# ============================================
# Local Development
# ============================================
echo -e "${BLUE}┌──────────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC}${BOLD} 💻 Local Development                                             ${NC}${BLUE}│${NC}"
echo -e "${BLUE}└──────────────────────────────────────────────────────────────────┘${NC}"

if [ -n "$VM_PUBLIC_IP" ]; then
    echo -e "  ${CYAN}SSH Tunnel:${NC}    ssh -L 8443:openai-${RESOURCE_TOKEN}.openai.azure.com:443 azureuser@$VM_PUBLIC_IP"
    echo -e "  ${CYAN}Local API:${NC}     https://localhost:8443/"
fi

# Check if tunnel is running
if pgrep -f "ssh.*8443.*$VM_PUBLIC_IP" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ SSH Tunnel is ACTIVE${NC}"
else
    echo -e "  ${YELLOW}⚠️  SSH Tunnel is NOT running${NC}"
    echo -e "     Run: ${GREEN}./setup_azure_tunnel.sh${NC}"
fi
echo ""

# ============================================
# Quick Commands
# ============================================
echo -e "${BLUE}┌──────────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC}${BOLD} ⚡ Quick Commands                                                ${NC}${BLUE}│${NC}"
echo -e "${BLUE}└──────────────────────────────────────────────────────────────────┘${NC}"
echo -e "  ${CYAN}Start tunnel:${NC}     ./setup_azure_tunnel.sh"
echo -e "  ${CYAN}Test agents:${NC}      python scripts/test_agents_with_tunnel.py"
echo -e "  ${CYAN}View logs:${NC}        tail -f logs/generate-embeddings-*.log"
echo -e "  ${CYAN}Check Redis:${NC}      python scripts/test_redis.py"
echo ""

echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
