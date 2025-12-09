#!/bin/bash

# Setup passwordless SSH to the Debug VM
# This script generates SSH keys if needed and copies them to the VM

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Setup Passwordless SSH to Debug VM${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Get environment from variable or default
AZURE_ENV_NAME="${AZURE_ENV_NAME:-dev}"
RESOURCE_GROUP="finagentix-${AZURE_ENV_NAME}-rg"

# Discover resource token from deployed resources
echo "🔍 Discovering resource token..."
RESOURCE_TOKEN=$(az vm list -g "$RESOURCE_GROUP" --query "[?starts_with(name, 'debug-vm-')].name" -o tsv | sed 's/debug-vm-//' | head -n 1)

if [ -z "$RESOURCE_TOKEN" ]; then
    echo -e "${RED}❌ Error: Could not discover resource token${NC}"
    echo "   Make sure the Debug VM is deployed"
    exit 1
fi

echo -e "${GREEN}✅ Resource token: $RESOURCE_TOKEN${NC}"

VM_NAME="debug-vm-${RESOURCE_TOKEN}"

# Get VM public IP
echo ""
echo "🔍 Getting VM public IP..."
VM_IP=$(az vm show -d -g "$RESOURCE_GROUP" -n "$VM_NAME" --query "publicIps" -o tsv)

if [ -z "$VM_IP" ]; then
    echo -e "${RED}❌ Failed to get VM IP${NC}"
    exit 1
fi

echo -e "${GREEN}✅ VM IP: $VM_IP${NC}"

# Check if SSH key exists
echo ""
echo "🔑 Checking SSH keys..."

SSH_KEY="$HOME/.ssh/id_rsa"
SSH_PUB_KEY="$HOME/.ssh/id_rsa.pub"

if [ ! -f "$SSH_KEY" ]; then
    echo -e "${YELLOW}⚠️  No SSH key found, generating new key...${NC}"
    ssh-keygen -t rsa -b 4096 -f "$SSH_KEY" -N "" -C "finagentix-$(date +%Y%m%d)"
    echo -e "${GREEN}✅ SSH key generated${NC}"
else
    echo -e "${GREEN}✅ SSH key exists${NC}"
fi

# Test if passwordless SSH already works
echo ""
echo "🧪 Testing SSH connection..."
if ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no "azureuser@${VM_IP}" "exit" 2>/dev/null; then
    echo -e "${GREEN}✅ Passwordless SSH already configured!${NC}"
    echo ""
    echo "Test command:"
    echo "  ssh azureuser@${VM_IP} 'hostname'"
    exit 0
fi

# Copy SSH key to VM
echo -e "${YELLOW}🔐 Setting up passwordless SSH...${NC}"
echo ""
echo "You will be prompted for the VM password once: ${GREEN}DebugVM2024!@#${NC}"
echo ""

if ssh-copy-id -o StrictHostKeyChecking=no "azureuser@${VM_IP}"; then
    echo ""
    echo -e "${GREEN}✅ Passwordless SSH configured successfully!${NC}"
    echo ""
    
    # Verify it works
    echo "🧪 Verifying SSH connection..."
    if ssh -o BatchMode=yes -o ConnectTimeout=5 "azureuser@${VM_IP}" "echo 'Connection test successful' && hostname"; then
        echo -e "${GREEN}✅ Verification successful!${NC}"
    else
        echo -e "${RED}❌ Verification failed${NC}"
        exit 1
    fi
else
    echo ""
    echo -e "${RED}❌ Failed to copy SSH key${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "You can now SSH without password:"
echo "  ${GREEN}ssh azureuser@${VM_IP}${NC}"
echo ""
echo "Or run commands directly:"
echo "  ${GREEN}ssh azureuser@${VM_IP} 'hostname'${NC}"
