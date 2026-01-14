#!/bin/bash
# SSH Port Forward to Azure OpenAI via Private Endpoint
# Routes Azure OpenAI traffic through the VNet debug VM
#
# Usage:
#   Terminal 1: ./setup_azure_tunnel.sh       (keep running)
#   Terminal 2: export AZURE_OPENAI_ENDPOINT=https://localhost:8443/
#               python your_script.py

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
VM_IP="4.227.91.227"
VM_USER="azureuser"
LOCAL_PORT=8443

# Get Azure OpenAI host from .env
if [ -f .env ]; then
    AZURE_OPENAI_HOST=$(grep "^AZURE_OPENAI_ENDPOINT=" .env | sed 's/AZURE_OPENAI_ENDPOINT=//' | sed 's|https://||' | sed 's|/||g')
else
    echo "Error: .env file not found"
    exit 1
fi

if [ -z "$AZURE_OPENAI_HOST" ]; then
    echo "Error: AZURE_OPENAI_ENDPOINT not found in .env"
    exit 1
fi

AZURE_OPENAI_PORT=443

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}Azure OpenAI SSH Tunnel (Private Endpoint)${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "${GREEN}VM:${NC} ${VM_USER}@${VM_IP}"
echo -e "${GREEN}Target:${NC} ${AZURE_OPENAI_HOST}:${AZURE_OPENAI_PORT}"
echo -e "${GREEN}Local:${NC} localhost:${LOCAL_PORT}"
echo ""
echo -e "${YELLOW}To use this tunnel, in another terminal run:${NC}"
echo ""
echo "  export AZURE_OPENAI_ENDPOINT=https://localhost:${LOCAL_PORT}/"
echo "  # Then run your Python scripts"
echo ""
echo -e "${YELLOW}Or add to .env.local:${NC}"
echo ""
echo "  AZURE_OPENAI_ENDPOINT=https://localhost:${LOCAL_PORT}/"
echo ""
echo -e "${BLUE}Press Ctrl+C to stop the tunnel.${NC}"
echo ""

# Create SSH tunnel with port forwarding
# -L: Local port forwarding
# -N: Don't execute remote command
ssh -L ${LOCAL_PORT}:${AZURE_OPENAI_HOST}:${AZURE_OPENAI_PORT} -N ${VM_USER}@${VM_IP}
