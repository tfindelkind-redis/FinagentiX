#!/bin/bash
# FinagentiX API Update Script
# Usage: ./scripts/update-api.sh [--skip-build] [--skip-restart]
#
# This script updates the API container app with the latest changes:
# 1. Loads configuration from .env
# 2. Builds the API container image
# 3. Pushes to Azure Container Registry
# 4. Restarts the Container App to pull the new image

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${ROOT_DIR}/.env"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
SKIP_BUILD=false
SKIP_RESTART=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-restart)
            SKIP_RESTART=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Update the FinagentiX API on Azure Container Apps"
            echo ""
            echo "Options:"
            echo "  --skip-build     Skip building the container image"
            echo "  --skip-restart   Skip restarting the container app"
            echo "  --verbose, -v    Show detailed output"
            echo "  --help, -h       Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo "=========================================="
echo -e "${BLUE}🚀 FinagentiX API Update${NC}"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ .env file not found at $ENV_FILE${NC}"
    echo "   Run ./infra/scripts/update-env.sh --all first"
    exit 1
fi

# Load environment variables from .env
echo "📄 Loading configuration from .env..."
set -a
source "$ENV_FILE"
set +a

# Check required variables and try to fetch if missing
REQUIRED_VARS=(
    "AZURE_RESOURCE_GROUP"
    "AZURE_CONTAINER_REGISTRY_NAME"
    "AZURE_API_APP_NAME"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Missing variables: ${MISSING_VARS[*]}${NC}"
    echo "   Running update-env.sh to fetch latest values..."
    "${ROOT_DIR}/infra/scripts/update-env.sh" --all
    
    # Reload .env
    set -a
    source "$ENV_FILE"
    set +a
    
    # Check again
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            echo -e "${RED}❌ Still missing required variable: $var${NC}"
            exit 1
        fi
    done
fi

# Display configuration
echo ""
echo "📋 Configuration:"
echo "   Resource Group:      ${AZURE_RESOURCE_GROUP}"
echo "   Container Registry:  ${AZURE_CONTAINER_REGISTRY_NAME}"
echo "   API App:             ${AZURE_API_APP_NAME}"
echo ""

# Step 1: Build and push container image
if [ "$SKIP_BUILD" = false ]; then
    echo -e "${BLUE}🔨 Step 1: Building API container image...${NC}"
    
    cd "$ROOT_DIR"
    
    # Build using Azure Container Registry
    az acr build \
        --registry "${AZURE_CONTAINER_REGISTRY_NAME}" \
        --image finagentix/agent-api:latest \
        --file docker/api.Dockerfile \
        . \
        ${VERBOSE:+--verbose}
    
    echo -e "${GREEN}✅ Image built and pushed successfully${NC}"
else
    echo -e "${YELLOW}⏭️  Skipping build (--skip-build)${NC}"
fi

echo ""

# Step 2: Restart the Container App
if [ "$SKIP_RESTART" = false ]; then
    echo -e "${BLUE}🔄 Step 2: Restarting Container App...${NC}"
    
    # Get the current revision
    CURRENT_REVISION=$(az containerapp revision list \
        --name "${AZURE_API_APP_NAME}" \
        --resource-group "${AZURE_RESOURCE_GROUP}" \
        --query "[0].name" -o tsv)
    
    if [ -z "$CURRENT_REVISION" ]; then
        echo -e "${RED}❌ Could not find current revision${NC}"
        exit 1
    fi
    
    echo "   Current revision: $CURRENT_REVISION"
    
    # Restart the revision
    az containerapp revision restart \
        --name "${AZURE_API_APP_NAME}" \
        --resource-group "${AZURE_RESOURCE_GROUP}" \
        --revision "$CURRENT_REVISION"
    
    echo -e "${GREEN}✅ Container App restarted${NC}"
else
    echo -e "${YELLOW}⏭️  Skipping restart (--skip-restart)${NC}"
fi

echo ""

# Step 3: Verify deployment
echo -e "${BLUE}🔍 Step 3: Verifying deployment...${NC}"

# Wait a few seconds for the restart to take effect
sleep 5

# Check the app status
APP_STATUS=$(az containerapp show \
    --name "${AZURE_API_APP_NAME}" \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --query "properties.runningStatus" -o tsv)

if [ "$APP_STATUS" = "Running" ]; then
    echo -e "${GREEN}✅ API is running${NC}"
else
    echo -e "${YELLOW}⚠️  API status: $APP_STATUS${NC}"
fi

# Get the URL
API_URL="https://${AZURE_API_FQDN:-$(az containerapp show \
    --name "${AZURE_API_APP_NAME}" \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --query "properties.configuration.ingress.fqdn" -o tsv)}"

echo ""
echo "=========================================="
echo -e "${GREEN}✅ API Update Complete!${NC}"
echo "=========================================="
echo ""
echo "🌐 API URL: $API_URL"
echo "🏥 Health Check: $API_URL/health"
echo ""
echo "📝 Next steps:"
echo "   - Test health: curl $API_URL/health"
echo "   - Check logs: az containerapp logs show -g ${AZURE_RESOURCE_GROUP} -n ${AZURE_API_APP_NAME}"
echo ""
