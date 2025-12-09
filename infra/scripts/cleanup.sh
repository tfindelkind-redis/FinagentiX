#!/bin/bash
set -e

# FinagentiX Cleanup Script
# This script deletes all infrastructure resources

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-finagentix-${AZURE_ENV_NAME}-rg}"

echo "========================================="
echo "FinagentiX Infrastructure Cleanup"
echo "========================================="
echo "Resource Group: $RESOURCE_GROUP"
echo ""

# Confirm deletion (skip if SKIP_CONFIRM=1)
if [ "${SKIP_CONFIRM:-0}" != "1" ]; then
    read -p "⚠️  This will DELETE all resources in '$RESOURCE_GROUP'. Continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "❌ Cleanup cancelled"
        exit 0
    fi
else
    echo "ℹ️  Skipping confirmation (SKIP_CONFIRM=1)"
fi

# Check if resource group exists
if ! az group exists --name "$RESOURCE_GROUP" | grep -q "true"; then
    echo "ℹ️  Resource group '$RESOURCE_GROUP' does not exist"
    exit 0
fi

echo "📋 Resources to be deleted:"
az resource list --resource-group "$RESOURCE_GROUP" --query "[].{Name:name, Type:type}" -o table
echo ""

# Delete resource group
echo "🗑️  Deleting resource group '$RESOURCE_GROUP'..."
if ! az group delete \
    --name "$RESOURCE_GROUP" \
    --yes \
    --no-wait; then
    echo "❌ Failed to initiate deletion"
    exit 1
fi

echo ""
echo "✅ Deletion initiated"
echo "ℹ️  This may take 10-15 minutes to complete."
echo "ℹ️  Check status with: az group show --name $RESOURCE_GROUP"
echo ""
echo "To monitor deletion:"
echo "  watch -n 10 'az group exists --name $RESOURCE_GROUP'"
