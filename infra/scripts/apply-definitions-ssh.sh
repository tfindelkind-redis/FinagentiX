#!/bin/bash
set -e

# Apply Featureform Definitions via Direct SSH
# Uses sshpass and actual SSH connection

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Apply Featureform Definitions via SSH${NC}"
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
RESOURCE_TOKEN=$(az deployment group list -g "$RESOURCE_GROUP" --query "[?contains(name, 'stage0')].properties.parameters.resourceToken.value | [0]" -o tsv 2>/dev/null)

if [ -z "$RESOURCE_TOKEN" ] || [ "$RESOURCE_TOKEN" == "null" ]; then
    echo -e "${RED}❌ Could not find resource token${NC}"
    exit 1
fi

DEBUG_POD_NAME="debug-pod-${RESOURCE_TOKEN}"
FEATUREFORM_HOST="featureform-${RESOURCE_TOKEN}.internal.azurecontainerapps.io"

# Get pod IP
POD_IP=$(az container show -g "$RESOURCE_GROUP" -n "$DEBUG_POD_NAME" --query "ipAddress.ip" -o tsv 2>/dev/null)

if [ -z "$POD_IP" ]; then
    echo -e "${RED}❌ Debug pod not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Debug pod IP: $POD_IP${NC}"

# Get Redis password
echo -e "${BLUE}🔑 Retrieving Redis credentials...${NC}"
REDIS_PASSWORD=$(az redisenterprise database list-keys \
    -g "$RESOURCE_GROUP" \
    --cluster-name "redis-${RESOURCE_TOKEN}" \
    --query "primaryKey" -o tsv 2>/dev/null)

echo -e "${GREEN}✅ Credentials retrieved${NC}"
echo ""

# Check if sshpass is installed
if ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}⚠️  sshpass not installed. Install with: brew install sshpass${NC}"
    echo ""
    echo -e "${BLUE}Alternative: Connect manually with:${NC}"
    echo "  ssh root@$POD_IP"
    echo "  Password: debugpod2024"
    echo ""
    echo "Then run these commands:"
    echo "  pip3 install featureform redis python-dotenv requests"
    echo "  git clone https://github.com/tfindelkind-redis/FinagentiX.git /tmp/FinagentiX"
    echo "  cd /tmp/FinagentiX"
    echo "  export FEATUREFORM_HOST=$FEATUREFORM_HOST"
    echo "  export REDIS_HOST=redis-${RESOURCE_TOKEN}.eastus.redis.azure.net"
    echo "  export REDIS_PORT=10000"
    echo "  export REDIS_PASSWORD=$REDIS_PASSWORD"
    echo "  python3 featureform/definitions.py"
    exit 1
fi

# SSH password
SSH_PASSWORD="debugpod2024"

echo -e "${BLUE}🚀 Connecting via SSH and applying definitions...${NC}"
echo ""

# Create remote script
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$POD_IP << EOFREMOTE
set -e

echo "📦 Installing dependencies..."
pip3 install -q featureform redis python-dotenv requests 2>/dev/null || pip3 install featureform redis python-dotenv requests

echo "📥 Cloning repository..."
rm -rf /tmp/FinagentiX 2>/dev/null || true
git clone -q https://github.com/tfindelkind-redis/FinagentiX.git /tmp/FinagentiX

echo "🚀 Applying Featureform definitions..."
cd /tmp/FinagentiX

export FEATUREFORM_HOST="$FEATUREFORM_HOST"
export REDIS_HOST="redis-${RESOURCE_TOKEN}.eastus.redis.azure.net"
export REDIS_PORT="10000"
export REDIS_PASSWORD="$REDIS_PASSWORD"

python3 featureform/definitions.py

echo ""
echo "✅ Definitions applied successfully!"
echo ""

echo "📋 Verifying features..."
python3 << 'EOFPYTHON'
import featureform as ff
import os

client = ff.Client(host=os.getenv("FEATUREFORM_HOST"), insecure=True)
try:
    features = client.list_features()
    print(f"✅ Registered {len(features)} features")
    for f in features[:10]:
        print(f"  • {f.name}")
    if len(features) > 10:
        print(f"  ... and {len(features) - 10} more")
except Exception as e:
    print(f"⚠️  Could not list features: {e}")
EOFPYTHON
EOFREMOTE

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
