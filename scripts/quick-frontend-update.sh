#!/bin/bash
# Quick Frontend Update - Build locally and copy to running container
# Much faster than full container rebuild for small changes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-finagentix-dev-rg}"

echo "🚀 Quick Frontend Update"
echo "========================"

# Get resource token from container registry (more reliable)
ACR_NAME=$(az acr list -g "$RESOURCE_GROUP" --query "[0].name" -o tsv)
RESOURCE_TOKEN=$(echo "$ACR_NAME" | sed 's/^acr//')
FRONTEND_APP="ca-frontend-${RESOURCE_TOKEN}"

echo "📦 Frontend App: $FRONTEND_APP"
echo "📦 ACR: $ACR_NAME"

# Step 1: Build frontend locally (fast with node_modules cached)
echo ""
echo "🔨 Building frontend locally..."
cd "$PROJECT_ROOT/frontend"

# Install deps only if needed
if [ ! -d "node_modules" ]; then
    echo "   Installing dependencies..."
    npm ci
fi

# Build
npm run build
echo "✅ Build complete"

# Step 2: Create minimal build context with just what we need
echo ""
echo "📤 Uploading to ACR (minimal context)..."

cd "$PROJECT_ROOT"

# Create temp directory with only required files
TEMP_DIR=$(mktemp -d)
cp -r frontend/dist "$TEMP_DIR/"
cp docker/nginx.conf "$TEMP_DIR/"
cp docker/frontend-runtime-config.sh "$TEMP_DIR/"

# Create minimal Dockerfile
cat > "$TEMP_DIR/Dockerfile" << 'EOF'
FROM nginx:1.27-alpine
COPY dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
RUN chmod +x /docker-entrypoint.d/40-runtime-config.sh
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF

# Build with unique tag (from minimal context ~300KB instead of 300MB)
TIMESTAMP=$(date +%s)
echo "   Building from minimal context (~300KB)..."
az acr build \
    --registry "$ACR_NAME" \
    --image "finagentix/frontend:v${TIMESTAMP}" \
    "$TEMP_DIR" \
    --only-show-errors

rm -rf "$TEMP_DIR"

# Step 3: Update container app to use new image
echo ""
echo "🔄 Updating container app..."
az containerapp update \
    --name "$FRONTEND_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --image "${ACR_NAME}.azurecr.io/finagentix/frontend:v${TIMESTAMP}" \
    --only-show-errors \
    --output none

# Get the environment domain
ENV_NAME=$(az containerapp env list -g "$RESOURCE_GROUP" --query "[0].name" -o tsv)
DOMAIN=$(az containerapp env show -g "$RESOURCE_GROUP" --name "$ENV_NAME" --query 'properties.defaultDomain' -o tsv)

echo ""
echo "✅ Update complete!"
echo ""
echo "🌐 Frontend: https://${FRONTEND_APP}.${DOMAIN}"
echo ""
echo "⏱️  This was much faster because:"
echo "   - Built locally (cached node_modules)"
echo "   - Minimal upload context (~300KB vs 300MB)"
echo "   - No npm install in container build"
