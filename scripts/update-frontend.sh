#!/bin/bash
# FinagentiX Frontend Update Script
# Usage: ./scripts/update-frontend.sh [--skip-build] [--skip-restart]
#
# This script updates the frontend container app with the latest changes:
# 1. Loads configuration from .env
# 2. Builds the frontend container image
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
            echo "Update the FinagentiX frontend on Azure Container Apps"
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
echo -e "${BLUE}🚀 FinagentiX Frontend Update${NC}"
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
    "AZURE_FRONTEND_APP_NAME"
    "AZURE_API_FQDN"
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
echo "   Frontend App:        ${AZURE_FRONTEND_APP_NAME}"
echo "   API URL:             https://${AZURE_API_FQDN}"
echo ""

# Get version info from git
GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
GIT_COMMIT_SHORT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
BUILD_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
BUILD_TIMESTAMP=$(date -u +"%Y%m%d%H%M%S")
APP_VERSION="1.0.0"

# Create unique tag to force new revision (Azure ignores :latest if unchanged)
IMAGE_TAG="${GIT_COMMIT_SHORT}-${BUILD_TIMESTAMP}"

echo "📦 Build Info:"
echo "   Git Commit:  ${GIT_COMMIT_SHORT}"
echo "   Git Branch:  ${GIT_BRANCH}"
echo "   Build Time:  ${BUILD_TIME}"
echo "   Image Tag:   ${IMAGE_TAG}"
echo ""

# Step 1: Build and push container image
if [ "$SKIP_BUILD" = false ]; then
    echo -e "${BLUE}🔨 Step 1: Building frontend container image...${NC}"
    
    cd "$ROOT_DIR"
    
    # Build using Azure Container Registry with version info
    # Push both unique tag and :latest for convenience
    az acr build \
        --registry "${AZURE_CONTAINER_REGISTRY_NAME}" \
        --image "finagentix/frontend:${IMAGE_TAG}" \
        --image "finagentix/frontend:latest" \
        --file docker/frontend.Dockerfile \
        --build-arg VITE_API_URL="https://${AZURE_API_FQDN}" \
        --build-arg VITE_GIT_COMMIT="${GIT_COMMIT}" \
        --build-arg VITE_GIT_BRANCH="${GIT_BRANCH}" \
        --build-arg VITE_BUILD_TIME="${BUILD_TIME}" \
        --build-arg VITE_APP_VERSION="${APP_VERSION}" \
        . \
        ${VERBOSE:+--verbose}
    
    echo -e "${GREEN}✅ Image built and pushed successfully${NC}"
else
    echo -e "${YELLOW}⏭️  Skipping build (--skip-build)${NC}"
fi

echo ""

# Step 2: Update Container App with new image (forces new revision)
if [ "$SKIP_RESTART" = false ]; then
    echo -e "${BLUE}🔄 Step 2: Updating Container App (forces fresh image pull)...${NC}"
    
    # Use unique tag to force Azure to create new revision
    # Using :latest doesn't trigger new revision if digest hasn't changed
    IMAGE_NAME="${AZURE_CONTAINER_REGISTRY_NAME}.azurecr.io/finagentix/frontend:${IMAGE_TAG}"
    
    echo "   Updating to image: $IMAGE_NAME"
    
    az containerapp update \
        --name "${AZURE_FRONTEND_APP_NAME}" \
        --resource-group "${AZURE_RESOURCE_GROUP}" \
        --image "$IMAGE_NAME" \
        --output none
    
    echo -e "${GREEN}✅ Container App updated with new revision${NC}"
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
    --name "${AZURE_FRONTEND_APP_NAME}" \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --query "properties.runningStatus" -o tsv)

if [ "$APP_STATUS" = "Running" ]; then
    echo -e "${GREEN}✅ Frontend is running${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend status: $APP_STATUS${NC}"
fi

# Get the URL
FRONTEND_URL="https://${AZURE_FRONTEND_FQDN:-$(az containerapp show \
    --name "${AZURE_FRONTEND_APP_NAME}" \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --query "properties.configuration.ingress.fqdn" -o tsv)}"

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Frontend Update Complete!${NC}"
echo "=========================================="
echo ""
echo "🌐 Frontend URL: $FRONTEND_URL"
echo ""
echo "📝 Next steps:"
echo "   - Open $FRONTEND_URL in your browser"
echo "   - Clear browser cache if you don't see changes (Cmd+Shift+R)"
echo "   - Check logs: az containerapp logs show -g ${AZURE_RESOURCE_GROUP} -n ${AZURE_FRONTEND_APP_NAME}"
echo ""
