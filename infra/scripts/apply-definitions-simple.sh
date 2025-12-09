#!/bin/bash
set -e

# Apply Featureform Definitions - Simple Version
# Copies local Python file to container via stdin and executes it

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Apply Featureform Definitions${NC}"
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

# Get resource token
echo -e "${BLUE}📋 Retrieving configuration...${NC}"
RESOURCE_TOKEN=$(az deployment group list -g "$RESOURCE_GROUP" --query "[?contains(name, 'stage0')].properties.parameters.resourceToken.value | [0]" -o tsv 2>/dev/null)

DEBUG_POD_NAME="debug-pod-${RESOURCE_TOKEN}"
FEATUREFORM_HOST="featureform-${RESOURCE_TOKEN}.internal.azurecontainerapps.io"

# Get Redis password
REDIS_PASSWORD=$(az redisenterprise database list-keys \
    -g "$RESOURCE_GROUP" \
    --cluster-name "redis-${RESOURCE_TOKEN}" \
    --query "primaryKey" -o tsv)

echo -e "${GREEN}✅ Configuration retrieved${NC}"
echo ""

# Step 1: Install dependencies
echo -e "${BLUE}🔧 Installing dependencies in debug pod...${NC}"
az container exec \
    -g "$RESOURCE_GROUP" \
    -n "$DEBUG_POD_NAME" \
    --exec-command "/bin/bash" \
    <<'EOF'
apt-get update -qq && apt-get install -y -qq git python3-pip curl > /dev/null 2>&1
pip3 install --quiet featureform redis python-dotenv requests 2>/dev/null
echo "Dependencies installed"
EOF

# Step 2: Clone repository  
echo -e "${BLUE}📥 Cloning repository...${NC}"
az container exec \
    -g "$RESOURCE_GROUP" \
    -n "$DEBUG_POD_NAME" \
    --exec-command "/bin/bash" \
    <<'EOF'
cd /tmp
rm -rf FinagentiX 2>/dev/null || true
git clone -q https://github.com/tfindelkind-redis/FinagentiX.git
echo "Repository cloned"
EOF

# Step 3: Set environment and apply definitions
echo -e "${BLUE}🚀 Applying definitions...${NC}"
az container exec \
    -g "$RESOURCE_GROUP" \
    -n "$DEBUG_POD_NAME" \
    --exec-command "/bin/bash" \
    <<EOF
cd /tmp/FinagentiX
export FEATUREFORM_HOST="$FEATUREFORM_HOST"
export REDIS_HOST="redis-$RESOURCE_TOKEN.eastus.redis.azure.net"
export REDIS_PORT="10000"
export REDIS_PASSWORD="$REDIS_PASSWORD"
python3 featureform/definitions.py
EOF

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Definitions Applied Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
