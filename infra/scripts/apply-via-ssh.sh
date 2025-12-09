#!/bin/bash
set -e

# Apply Featureform Definitions via SSH to Debug Pod
# This script uses SSH for reliable command execution

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

echo -e "${BLUE}📋 Configuration:${NC}"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Debug Pod: $DEBUG_POD_NAME"
echo ""

# Check if debug pod exists and is running
echo -e "${BLUE}🔍 Checking debug pod...${NC}"
POD_IP=$(az container show -g "$RESOURCE_GROUP" -n "$DEBUG_POD_NAME" --query "ipAddress.ip" -o tsv 2>/dev/null || echo "")

if [ -z "$POD_IP" ]; then
    echo -e "${RED}❌ Debug pod not found or not assigned IP yet${NC}"
    echo -e "${YELLOW}💡 Deploy it with: ./infra/scripts/deploy-debug-pod.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Debug pod is running at $POD_IP${NC}"
echo ""

# Get Redis password
echo -e "${BLUE}🔑 Retrieving Redis credentials...${NC}"
REDIS_PASSWORD=$(az redisenterprise database list-keys \
    -g "$RESOURCE_GROUP" \
    --cluster-name "redis-${RESOURCE_TOKEN}" \
    --query "primaryKey" -o tsv 2>/dev/null)

if [ -z "$REDIS_PASSWORD" ]; then
    echo -e "${RED}❌ Could not retrieve Redis password${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Redis credentials retrieved${NC}"
echo ""

# Wait for SSH to be ready
echo -e "${BLUE}⏳ Waiting for SSH server to be ready...${NC}"
for i in {1..30}; do
    if az container exec -g "$RESOURCE_GROUP" -n "$DEBUG_POD_NAME" --exec-command "which sshd" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ SSH server is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ SSH server not ready after 60 seconds${NC}"
        exit 1
    fi
    sleep 2
done
echo ""

# Create the apply script
APPLY_SCRIPT=$(mktemp)
cat > "$APPLY_SCRIPT" << 'EOFSCRIPT'
#!/bin/bash
set -e

echo "📦 Installing dependencies..."
pip3 install -q featureform redis python-dotenv requests 2>/dev/null || pip3 install featureform redis python-dotenv requests

echo "📥 Cloning repository..."
rm -rf /tmp/FinagentiX 2>/dev/null || true
git clone -q https://github.com/tfindelkind-redis/FinagentiX.git /tmp/FinagentiX

echo "🚀 Applying Featureform definitions..."
cd /tmp/FinagentiX

export FEATUREFORM_HOST="__FEATUREFORM_HOST__"
export REDIS_HOST="redis-__RESOURCE_TOKEN__.eastus.redis.azure.net"
export REDIS_PORT="10000"
export REDIS_PASSWORD="__REDIS_PASSWORD__"

python3 featureform/definitions.py

echo ""
echo "✅ Definitions applied successfully!"
echo ""
echo "Verifying features..."
python3 << 'EOFPYTHON'
import featureform as ff
import os

client = ff.Client(host=os.getenv("FEATUREFORM_HOST"), insecure=True)
try:
    features = client.list_features()
    print(f"📋 Registered features: {len(features)}")
    for f in features[:10]:
        print(f"  ✓ {f.name}")
    if len(features) > 10:
        print(f"  ... and {len(features) - 10} more")
except Exception as e:
    print(f"⚠️  Could not list features: {e}")
EOFPYTHON
EOFSCRIPT

# Replace placeholders
sed -i '' "s|__FEATUREFORM_HOST__|${FEATUREFORM_HOST}|g" "$APPLY_SCRIPT"
sed -i '' "s|__RESOURCE_TOKEN__|${RESOURCE_TOKEN}|g" "$APPLY_SCRIPT"
sed -i '' "s|__REDIS_PASSWORD__|${REDIS_PASSWORD}|g" "$APPLY_SCRIPT"

chmod +x "$APPLY_SCRIPT"

# Since piping to az container exec doesn't work, write commands directly
echo -e "${BLUE}🚀 Installing dependencies in debug pod...${NC}"
az container exec -g "$RESOURCE_GROUP" -n "$DEBUG_POD_NAME" \
    --exec-command "pip3 install featureform redis python-dotenv requests" > /dev/null 2>&1 || true

echo -e "${BLUE}📥 Cloning repository...${NC}"
az container exec -g "$RESOURCE_GROUP" -n "$DEBUG_POD_NAME" \
    --exec-command "rm -rf /tmp/FinagentiX" > /dev/null 2>&1 || true

az container exec -g "$RESOURCE_GROUP" -n "$DEBUG_POD_NAME" \
    --exec-command "git clone https://github.com/tfindelkind-redis/FinagentiX.git /tmp/FinagentiX"

echo -e "${BLUE}🚀 Applying Featureform definitions...${NC}"
echo ""

# Run Python directly with inline script
az container exec -g "$RESOURCE_GROUP" -n "$DEBUG_POD_NAME" \
    --exec-command "python3 -c \"import os; os.environ['FEATUREFORM_HOST']='$FEATUREFORM_HOST'; os.environ['REDIS_HOST']='redis-${RESOURCE_TOKEN}.eastus.redis.azure.net'; os.environ['REDIS_PORT']='10000'; os.environ['REDIS_PASSWORD']='$REDIS_PASSWORD'; exec(open('/tmp/FinagentiX/featureform/definitions.py').read()); print(''); print('✅ Definitions applied!'); import featureform as ff; client=ff.Client(host=os.getenv('FEATUREFORM_HOST'),insecure=True); features=client.list_features(); print(f'📋 Registered {len(features)} features')\""

rm -f "$APPLY_SCRIPT"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}💡 Next steps:${NC}"
echo "  1. Update agent code to use Featureform client"
echo "  2. Test feature retrieval from agents"
echo ""
