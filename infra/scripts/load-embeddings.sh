#!/bin/bash

# Load embeddings to Redis from the Debug VM
# This script connects to the VM and runs the embeddings loading script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Load Embeddings to Redis${NC}"
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
    echo "   Make sure resources are deployed"
    exit 1
fi

echo -e "${GREEN}✅ Resource token: $RESOURCE_TOKEN${NC}"

# Get location
LOCATION=$(az group show -g "$RESOURCE_GROUP" --query "location" -o tsv)
echo -e "${GREEN}✅ Location: $LOCATION${NC}"

# Configuration
VM_NAME="debug-vm-${RESOURCE_TOKEN}"
REDIS_NAME="redis-${RESOURCE_TOKEN}"
OPENAI_NAME="openai-${RESOURCE_TOKEN}"

echo ""
echo -e "${BLUE}📋 Configuration:${NC}"
echo "  Resource Token: $RESOURCE_TOKEN"
echo "  Location: $LOCATION"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  VM: $VM_NAME"
echo "  Redis: $REDIS_NAME"
echo "  OpenAI: $OPENAI_NAME"

# Get Redis credentials
echo ""
echo "🔑 Retrieving Redis credentials..."
REDIS_PASSWORD=$(az redisenterprise database list-keys -g "$RESOURCE_GROUP" \
    --cluster-name "$REDIS_NAME" \
    --query "primaryKey" -o tsv)

if [ -z "$REDIS_PASSWORD" ]; then
    echo -e "${RED}❌ Failed to retrieve Redis password${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Redis credentials retrieved${NC}"

# Get Redis host
REDIS_HOST=$(az redisenterprise show -g "$RESOURCE_GROUP" -n "$REDIS_NAME" \
    --query "hostName" -o tsv)

echo -e "${GREEN}✅ Redis host: $REDIS_HOST${NC}"

# Get Azure OpenAI credentials
echo ""
echo "🔑 Retrieving Azure OpenAI credentials..."

OPENAI_ENDPOINT=$(az cognitiveservices account show -g "$RESOURCE_GROUP" -n "$OPENAI_NAME" \
    --query "properties.endpoint" -o tsv 2>/dev/null || echo "")

OPENAI_KEY=$(az cognitiveservices account keys list -g "$RESOURCE_GROUP" -n "$OPENAI_NAME" \
    --query "key1" -o tsv 2>/dev/null || echo "")

if [ -z "$OPENAI_ENDPOINT" ] || [ -z "$OPENAI_KEY" ]; then
    echo -e "${YELLOW}⚠️  Azure OpenAI not deployed${NC}"
    echo ""
    echo "Azure OpenAI is required for embeddings. Deploying now..."
    echo ""
    
    # Deploy Azure OpenAI (Stage 2)
    if ! "$SCRIPT_DIR/deploy.sh" --stage stage2; then
        echo -e "${RED}❌ Failed to deploy Azure OpenAI${NC}"
        echo ""
        echo "Please deploy manually:"
        echo "  export AZURE_ENV_NAME=dev"
        echo "  export AZURE_LOCATION=$LOCATION"
        echo "  ./infra/scripts/deploy.sh"
        echo ""
        echo "Then select stage2 (AI Services) when prompted."
        exit 1
    fi
    
    # Retrieve credentials again
    OPENAI_ENDPOINT=$(az cognitiveservices account show -g "$RESOURCE_GROUP" -n "$OPENAI_NAME" \
        --query "properties.endpoint" -o tsv)
    
    OPENAI_KEY=$(az cognitiveservices account keys list -g "$RESOURCE_GROUP" -n "$OPENAI_NAME" \
        --query "key1" -o tsv)
fi

echo -e "${GREEN}✅ OpenAI endpoint: $OPENAI_ENDPOINT${NC}"

# Get VM public IP
echo ""
echo "🔍 Getting VM public IP..."
VM_IP=$(az vm show -d -g "$RESOURCE_GROUP" -n "$VM_NAME" \
    --query "publicIps" -o tsv)

if [ -z "$VM_IP" ]; then
    echo -e "${RED}❌ Failed to get VM IP${NC}"
    exit 1
fi

echo -e "${GREEN}✅ VM IP: $VM_IP${NC}"

# Ensure SSH key is set up
echo ""
echo "🔐 Checking SSH setup..."
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no "azureuser@${VM_IP}" "exit" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Passwordless SSH not configured. Setting up...${NC}"
    if ! "$SCRIPT_DIR/setup-ssh-key.sh"; then
        echo -e "${RED}❌ SSH setup failed${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✅ SSH configured${NC}"

# Parse command-line arguments
MODE="${1:-dry-run}"  # dry-run, sec-filings, news, or all

echo ""
echo -e "${BLUE}🚀 Connecting to VM and loading embeddings...${NC}"
echo ""

# Create a script to run on the VM
TEMP_SCRIPT=$(mktemp)
cat > "$TEMP_SCRIPT" << 'EOFSCRIPT'
#!/bin/bash

set -e

echo "========================================="
echo "Running on VM: Loading Embeddings"
echo "========================================="
echo ""

MODE="$1"
REDIS_HOST="$2"
REDIS_PORT="$3"
REDIS_PASSWORD="$4"
OPENAI_ENDPOINT="$5"
OPENAI_KEY="$6"

echo "📋 Configuration:"
echo "  Mode: $MODE"
echo "  Redis: $REDIS_HOST:$REDIS_PORT"
echo "  OpenAI: $OPENAI_ENDPOINT"
echo ""

# Update repository
cd /tmp
if [ -d "FinagentiX" ]; then
    echo "🔄 Updating repository..."
    cd FinagentiX
    git pull
else
    echo "📥 Cloning repository..."
    git clone https://github.com/tfindelkind-redis/FinagentiX.git
    cd FinagentiX
fi

# Install dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip3 install --user --quiet openai pandas redis pyarrow numpy 2>/dev/null || {
    echo "⚠️  Some packages may already be installed"
}

# Set environment variables
export REDIS_HOST="$REDIS_HOST"
export REDIS_PORT="$REDIS_PORT"
export REDIS_PASSWORD="$REDIS_PASSWORD"
export AZURE_OPENAI_ENDPOINT="$OPENAI_ENDPOINT"
export AZURE_OPENAI_KEY="$OPENAI_KEY"
export PATH="$HOME/.local/bin:$PATH"

# Run the loading script
echo ""
echo "🚀 Loading embeddings..."
echo ""

case "$MODE" in
    "dry-run")
        python3 scripts/load_embeddings.py --all --dry-run
        ;;
    "all")
        python3 scripts/load_embeddings.py --all
        ;;
    "sec-filings")
        python3 scripts/load_embeddings.py --sec-filings
        ;;
    "news")
        python3 scripts/load_embeddings.py --news
        ;;
    *)
        echo "❌ Unknown mode: $MODE"
        echo "   Valid modes: dry-run, all, sec-filings, news"
        exit 1
        ;;
esac

echo ""
echo "✅ Done!"
EOFSCRIPT

chmod +x "$TEMP_SCRIPT"

# Copy script to VM
scp -o StrictHostKeyChecking=no "$TEMP_SCRIPT" "azureuser@${VM_IP}:/tmp/load_embeddings.sh"

# Run script on VM
ssh -o StrictHostKeyChecking=no "azureuser@${VM_IP}" \
    "bash /tmp/load_embeddings.sh '$MODE' '$REDIS_HOST' 10000 '$REDIS_PASSWORD' '$OPENAI_ENDPOINT' '$OPENAI_KEY'"

# Cleanup
rm "$TEMP_SCRIPT"

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}✅ Complete!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Test vector search with semantic queries"
echo "  2. Implement agents to use embeddings"
echo ""
echo "To SSH to the VM manually:"
echo "  ssh azureuser@$VM_IP"
