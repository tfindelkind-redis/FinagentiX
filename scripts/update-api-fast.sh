#!/bin/bash
# ============================================================
# Fast API Update Script
# ============================================================
# This script updates only the API code without rebuilding the
# entire Docker image. Much faster than a full redeploy.
#
# Strategy:
# 1. Build locally with cached layers
# 2. Push only changed layers
# 3. Restart container app
#
# Usage:
#   ./scripts/update-api-fast.sh
# ============================================================

set -e

START_TIME=$(date +%s)

echo "=============================================="
echo "⚡ Fast API Update"
echo "=============================================="
echo ""

# Configuration
RESOURCE_GROUP="finagentix-dev-rg"
ACR_NAME="acr3ae172dc9e9da"
CONTAINER_APP="ca-agent-api-3ae172dc9e9da"
IMAGE_NAME="finagentix-api"

# Generate unique tag to force new revision (Azure caches "latest" tag)
IMAGE_TAG=$(date +%Y%m%d%H%M%S)

# Step 1: Login to ACR
echo "🔐 Logging into ACR..."
az acr login --name "$ACR_NAME"
echo ""

# Step 2: Build with cache
echo "🔨 Building Docker image (with layer cache)..."
echo "   Image tag: $IMAGE_TAG"
BUILD_START=$(date +%s)

# Pull the latest image to use as cache
docker pull --platform linux/amd64 "$ACR_NAME.azurecr.io/$IMAGE_NAME:latest" 2>/dev/null || true

# Build with cache-from (always target linux/amd64 for Azure Container Apps)
# Tag with both unique timestamp AND latest for cache purposes
docker build \
    --platform linux/amd64 \
    -f docker/api.Dockerfile \
    --cache-from "$ACR_NAME.azurecr.io/$IMAGE_NAME:latest" \
    -t "$ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG" \
    -t "$ACR_NAME.azurecr.io/$IMAGE_NAME:latest" \
    .

BUILD_END=$(date +%s)
BUILD_DURATION=$((BUILD_END - BUILD_START))
echo "✅ Build completed in ${BUILD_DURATION}s"
echo ""

# Step 3: Push BOTH tags (unique tag forces new image pull in Azure)
echo "📤 Pushing image with tag: $IMAGE_TAG..."
PUSH_START=$(date +%s)
docker push "$ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG"
docker push "$ACR_NAME.azurecr.io/$IMAGE_NAME:latest"
PUSH_END=$(date +%s)
PUSH_DURATION=$((PUSH_END - PUSH_START))
echo "✅ Push completed in ${PUSH_DURATION}s"
echo ""

# Step 4: Update container app with NEW unique tag (forces new revision)
echo "🔄 Updating Container App with new image..."
RESTART_START=$(date +%s)

# Update with unique tag - this FORCES a new revision since the tag changed
az containerapp update \
    --name "$CONTAINER_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --image "$ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG" \
    --output none

RESTART_END=$(date +%s)
RESTART_DURATION=$((RESTART_END - RESTART_START))
echo "✅ Update completed in ${RESTART_DURATION}s"
echo ""

# Step 5: Force restart the new revision to ensure fresh container
echo "🔃 Restarting revision to ensure fresh container..."
CURRENT_REVISION=$(az containerapp revision list \
    --name "$CONTAINER_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --query "[0].name" \
    -o tsv)
az containerapp revision restart \
    --name "$CONTAINER_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --revision "$CURRENT_REVISION" \
    --output none
echo "✅ Revision restarted"
echo ""

# Wait for health check
echo "⏳ Waiting for API to be healthy..."
API_URL="https://ca-agent-api-3ae172dc9e9da.redflower-348a14ef.westus3.azurecontainerapps.io/health"
MAX_WAIT=60
WAITED=0

while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -sf "$API_URL" > /dev/null 2>&1; then
        echo "✅ API is healthy!"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    echo "   Waiting... (${WAITED}s)"
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "⚠️  API health check timed out. Check logs with:"
    echo "   az containerapp logs show -n $CONTAINER_APP -g $RESOURCE_GROUP --follow"
fi

END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))

echo ""
echo "=============================================="
echo "⚡ Update Complete!"
echo "=============================================="
echo "  Build time:   ${BUILD_DURATION}s"
echo "  Push time:    ${PUSH_DURATION}s"
echo "  Restart time: ${RESTART_DURATION}s"
echo "  Total time:   ${TOTAL_DURATION}s"
echo ""
echo "  API URL: $API_URL"
echo "=============================================="
