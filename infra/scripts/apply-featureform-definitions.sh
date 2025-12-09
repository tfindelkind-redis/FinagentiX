#!/bin/bash
set -e

# Apply Featureform Definitions from Debug Pod
# This script copies local definitions to the debug pod and applies them

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
echo -e "${BLUE}📋 Retrieving resource token...${NC}"
RESOURCE_TOKEN=$(az deployment group list -g "$RESOURCE_GROUP" --query "[?contains(name, 'stage0')].properties.parameters.resourceToken.value | [0]" -o tsv 2>/dev/null)

if [ -z "$RESOURCE_TOKEN" ] || [ "$RESOURCE_TOKEN" == "null" ]; then
    echo -e "${YELLOW}❌ Could not find resource token${NC}"
    exit 1
fi

DEBUG_POD_NAME="debug-pod-${RESOURCE_TOKEN}"
FEATUREFORM_HOST="featureform-${RESOURCE_TOKEN}.internal.azurecontainerapps.io"

echo -e "${GREEN}✅ Resource token: $RESOURCE_TOKEN${NC}"
echo ""

# Check if debug pod exists
echo -e "${BLUE}📋 Checking debug pod...${NC}"
POD_STATE=$(az container show -g "$RESOURCE_GROUP" -n "$DEBUG_POD_NAME" --query "properties.instanceView.state" -o tsv 2>/dev/null || echo "NotFound")

if [ "$POD_STATE" == "NotFound" ]; then
    echo -e "${YELLOW}❌ Debug pod not found. Deploy it first with: ./infra/scripts/deploy-debug-pod.sh${NC}"
    exit 1
fi

if [ "$POD_STATE" != "Running" ]; then
    echo -e "${YELLOW}⚠️  Debug pod is in state: $POD_STATE${NC}"
    echo -e "${YELLOW}   Starting it...${NC}"
    az container start -g "$RESOURCE_GROUP" -n "$DEBUG_POD_NAME"
    sleep 10
fi

echo -e "${GREEN}✅ Debug pod is running${NC}"
echo ""

# Get Redis password
echo -e "${BLUE}📋 Retrieving Redis credentials...${NC}"
REDIS_PASSWORD=$(az redisenterprise database list-keys \
    -g "$RESOURCE_GROUP" \
    --cluster-name "redis-${RESOURCE_TOKEN}" \
    --query "primaryKey" -o tsv)

echo -e "${GREEN}✅ Redis credentials retrieved${NC}"
echo ""

# Create definitions script
echo -e "${BLUE}📝 Preparing definitions script...${NC}"
DEFINITIONS_FILE="$REPO_ROOT/featureform/definitions.py"

if [ ! -f "$DEFINITIONS_FILE" ]; then
    echo -e "${YELLOW}❌ Definitions file not found: $DEFINITIONS_FILE${NC}"
    exit 1
fi

# Create a temporary script that will run in the container
TMP_SCRIPT=$(mktemp)
cat > "$TMP_SCRIPT" << 'EOFSCRIPT'
#!/bin/bash
set -e

echo "🔧 Installing dependencies..."
apt-get update -qq && apt-get install -y -qq git python3-pip curl > /dev/null 2>&1 || true
pip3 install --quiet featureform redis python-dotenv requests 2>/dev/null || true

echo "📥 Cloning repository..."
cd /tmp
rm -rf FinagentiX 2>/dev/null || true
git clone -q https://github.com/tfindelkind-redis/FinagentiX.git
cd FinagentiX

echo "🚀 Applying Featureform definitions..."
export FEATUREFORM_HOST="FEATUREFORM_HOST_PLACEHOLDER"
export REDIS_HOST="redis-RESOURCE_TOKEN_PLACEHOLDER.eastus.redis.azure.net"
export REDIS_PORT="10000"
export REDIS_PASSWORD="REDIS_PASSWORD_PLACEHOLDER"

python3 featureform/definitions.py

echo "✅ Definitions applied successfully!"
EOFSCRIPT

# Replace placeholders
sed -i.bak "s|FEATUREFORM_HOST_PLACEHOLDER|$FEATUREFORM_HOST|g" "$TMP_SCRIPT"
sed -i.bak "s|RESOURCE_TOKEN_PLACEHOLDER|$RESOURCE_TOKEN|g" "$TMP_SCRIPT"
sed -i.bak "s|REDIS_PASSWORD_PLACEHOLDER|$REDIS_PASSWORD|g" "$TMP_SCRIPT"
rm -f "$TMP_SCRIPT.bak"

echo -e "${GREEN}✅ Script prepared${NC}"
echo ""

# Write a simple Python script that applies definitions
cat > "$TMP_SCRIPT" << 'EOFPYTHON'
import os
import sys

# Set environment
host = "FEATUREFORM_HOST_VAR"
os.environ["FEATUREFORM_HOST"] = host
os.environ["REDIS_HOST"] = "REDIS_HOST_VAR"
os.environ["REDIS_PORT"] = "10000"
os.environ["REDIS_PASSWORD"] = "REDIS_PASSWORD_VAR"

print(f"Connecting to Featureform at {host}...")

# Read and execute definitions
with open("/tmp/FinagentiX/featureform/definitions.py") as f:
    code = f.read()
    exec(code)

print("✅ Definitions applied successfully!")
EOFPYTHON

# Replace variables
sed -i.bak "s|FEATUREFORM_HOST_VAR|$FEATUREFORM_HOST|g" "$TMP_SCRIPT"
sed -i.bak "s|REDIS_HOST_VAR|redis-${RESOURCE_TOKEN}.eastus.redis.azure.net|g" "$TMP_SCRIPT"
sed -i.bak "s|REDIS_PASSWORD_VAR|$REDIS_PASSWORD|g" "$TMP_SCRIPT"
rm -f "$TMP_SCRIPT.bak"

# Create wrapper script
WRAPPER_SCRIPT="/tmp/ff-apply-wrapper-$$.sh"
cat > "$WRAPPER_SCRIPT" << 'EOFWRAPPER'
#!/bin/bash
set -e
pip3 install -q featureform redis python-dotenv requests 2>/dev/null || true
rm -rf /tmp/FinagentiX 2>/dev/null || true
git clone -q https://github.com/tfindelkind-redis/FinagentiX.git /tmp/FinagentiX
cd /tmp/FinagentiX
python3 featureform/definitions.py
EOFWRAPPER

chmod +x "$WRAPPER_SCRIPT"

# Execute in pod
echo -e "${BLUE}🚀 Applying definitions in debug pod...${NC}"
echo ""

# Copy wrapper to pod and execute with environment variables
cat "$WRAPPER_SCRIPT" | az container exec -g "$RESOURCE_GROUP" -n "$DEBUG_POD_NAME" \
    --container-name debug \
    --exec-command "/bin/bash -c 'cat > /tmp/wrapper.sh && chmod +x /tmp/wrapper.sh && FEATUREFORM_HOST=$FEATUREFORM_HOST REDIS_HOST=redis-${RESOURCE_TOKEN}.eastus.redis.azure.net REDIS_PASSWORD=$REDIS_PASSWORD /tmp/wrapper.sh'"

rm -f "$WRAPPER_SCRIPT" "$TMP_SCRIPT"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Definitions Applied!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}💡 To verify features were created, connect to debug pod:${NC}"
echo "  az container exec -g $RESOURCE_GROUP -n $DEBUG_POD_NAME --exec-command /bin/bash"
echo ""
