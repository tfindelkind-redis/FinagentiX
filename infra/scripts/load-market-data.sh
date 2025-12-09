#!/bin/bash

# Load market data to Redis TimeSeries from the Debug VM
# This script connects to the VM and runs the data loading script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Load Market Data to Redis${NC}"
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

echo ""
echo -e "${BLUE}📋 Configuration:${NC}"
echo "  Resource Token: $RESOURCE_TOKEN"
echo "  Location: $LOCATION"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  VM: $VM_NAME"
echo "  Redis: $REDIS_NAME"

# Get Redis password
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
MODE="${1:-dry-run}"  # dry-run, all, or ticker name

echo ""
echo -e "${BLUE}🚀 Connecting to VM and loading data...${NC}"
echo ""

# Create a script to run on the VM
TEMP_SCRIPT=$(mktemp)
cat > "$TEMP_SCRIPT" << 'EOFSCRIPT'
#!/bin/bash

set -e

echo "========================================="
echo "Running on VM: Loading Market Data"
echo "========================================="
echo ""

MODE="$1"
REDIS_HOST="$2"
REDIS_PORT="$3"
REDIS_PASSWORD="$4"

echo "📋 Configuration:"
echo "  Mode: $MODE"
echo "  Redis: $REDIS_HOST:$REDIS_PORT"
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

# Install dependencies system-wide (VM doesn't have venv configured)
echo ""
echo "📦 Installing Python dependencies..."
pip3 install --user --quiet pandas redis pyarrow 2>/dev/null || {
    echo "⚠️  Some packages may already be installed"
}

# Set environment variables
export REDIS_HOST="$REDIS_HOST"
export REDIS_PORT="$REDIS_PORT"
export REDIS_PASSWORD="$REDIS_PASSWORD"
export PATH="$HOME/.local/bin:$PATH"

# Run the loading script
echo ""
echo "🚀 Loading market data..."
echo ""

case "$MODE" in
    "dry-run")
        python3 scripts/load_market_data.py --all --dry-run
        ;;
    "all")
        python3 scripts/load_market_data.py --all
        ;;
    "list")
        python3 scripts/load_market_data.py --list
        ;;
    *)
        # Assume it's a ticker symbol
        python3 scripts/load_market_data.py --ticker "$MODE"
        ;;
esac

echo ""
echo "✅ Done!"
EOFSCRIPT

chmod +x "$TEMP_SCRIPT"

# Copy script to VM
scp -o StrictHostKeyChecking=no "$TEMP_SCRIPT" "azureuser@${VM_IP}:/tmp/load_market_data.sh"

# Run script on VM
ssh -o StrictHostKeyChecking=no "azureuser@${VM_IP}" \
    "bash /tmp/load_market_data.sh '$MODE' '$REDIS_HOST' 10000 '$REDIS_PASSWORD'"

# Cleanup
rm "$TEMP_SCRIPT"

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}✅ Complete!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Verify data: ./infra/scripts/load-market-data.sh verify-AAPL"
echo "  2. Load all: ./infra/scripts/load-market-data.sh all"
echo ""
echo "To SSH to the VM manually:"
echo "  ssh azureuser@$VM_IP"
