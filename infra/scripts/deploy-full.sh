#!/bin/bash
set -e

# Full Deployment Script for FinagentiX to West US 3
# This script handles complete deployment from scratch

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
export AZURE_ENV_NAME="${AZURE_ENV_NAME:-dev}"
export AZURE_LOCATION="${AZURE_LOCATION:-westus3}"
export AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-finagentix-${AZURE_ENV_NAME}-rg}"

echo "=========================================="
echo "FinagentiX Full Deployment to West US 3"
echo "=========================================="
echo "Resource Group: $AZURE_RESOURCE_GROUP"
echo "Location: $AZURE_LOCATION"
echo "Environment: $AZURE_ENV_NAME"
echo ""

# Function to wait for resource group deletion
wait_for_deletion() {
    local rg=$1
    echo "⏳ Waiting for resource group deletion to complete..."
    local count=0
    while az group exists --name "$rg" | grep -q "true"; do
        count=$((count + 1))
        if [ $((count % 6)) -eq 0 ]; then
            echo "   Still deleting... $((count / 6)) minute(s) elapsed"
        fi
        sleep 10
    done
    echo "✅ Resource group deleted"
}

# Check if resource group exists
if az group exists --name "$AZURE_RESOURCE_GROUP" | grep -q "true"; then
    echo "⚠️  Resource group '$AZURE_RESOURCE_GROUP' already exists"
    echo ""
    read -p "Do you want to DELETE and recreate it? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        echo "🗑️  Deleting existing resource group..."
        export SKIP_CONFIRM=1
        "$SCRIPT_DIR/cleanup.sh"
        wait_for_deletion "$AZURE_RESOURCE_GROUP"
    else
        echo "❌ Deployment cancelled"
        exit 0
    fi
fi

echo ""
echo "=========================================="
echo "Step 1: Deploying Infrastructure"
echo "=========================================="
"$SCRIPT_DIR/deploy.sh"

echo ""
echo "=========================================="
echo "Step 2: Deploying Featureform"
echo "=========================================="
"$SCRIPT_DIR/deploy-featureform.sh"

echo ""
echo "=========================================="
echo "Step 3: Deploying Debug VM"
echo "=========================================="
"$SCRIPT_DIR/deploy-debug-vm.sh"

echo ""
echo "=========================================="
echo "✅ Full Deployment Complete!"
echo "=========================================="
echo ""

# Get resource token
RESOURCE_TOKEN=$(az deployment group list -g "$AZURE_RESOURCE_GROUP" --query "[?contains(name, 'stage0')].properties.parameters.resourceToken.value | [0]" -o tsv)

# Get Redis password
echo "📋 Getting Redis password..."
REDIS_PASSWORD=$(az redisenterprise database list-keys \
    -g "$AZURE_RESOURCE_GROUP" \
    --cluster-name "redis-${RESOURCE_TOKEN}" \
    --query "primaryKey" -o tsv)

# Get VM public IP
echo "📋 Getting VM public IP..."
VM_PUBLIC_IP=$(az vm show -g "$AZURE_RESOURCE_GROUP" -n "debug-vm-${RESOURCE_TOKEN}" -d --query "publicIps" -o tsv)

echo ""
echo "=========================================="
echo "Next Steps: Apply Featureform Definitions"
echo "=========================================="
echo ""
echo "1. SSH to the debug VM:"
echo "   ssh azureuser@$VM_PUBLIC_IP"
echo "   Password: DebugVM2024!@#"
echo ""
echo "=========================================="
echo "📝 Applying Featureform Definitions"
echo "=========================================="
echo ""
read -p "Apply Featureform definitions now? (yes/no): " apply_now
if [ "$apply_now" = "yes" ]; then
    echo "🚀 Running connect-and-apply script..."
    "$SCRIPT_DIR/connect-and-apply.sh" || {
        echo "⚠️  Automatic application failed. Manual steps:"
        echo ""
        echo "1. SSH to VM: ssh azureuser@${VM_PUBLIC_IP}"
        echo "2. On the VM, run:"
        echo "   curl -s https://raw.githubusercontent.com/tfindelkind-redis/FinagentiX/main/infra/scripts/apply-definitions-on-vm.sh | bash -s $RESOURCE_TOKEN '$REDIS_PASSWORD' $AZURE_LOCATION"
    }
else
    echo "📋 To apply definitions later, run:"
    echo "   ./infra/scripts/connect-and-apply.sh"
    echo ""
    echo "Or manually:"
    echo "1. SSH to VM: ssh azureuser@${VM_PUBLIC_IP}"
    echo "2. On the VM, run:"
    echo "   curl -s https://raw.githubusercontent.com/tfindelkind-redis/FinagentiX/main/infra/scripts/apply-definitions-on-vm.sh | bash -s $RESOURCE_TOKEN '$REDIS_PASSWORD' $AZURE_LOCATION"
fi
echo ""

# Save deployment info
cat > "/tmp/finagentix-deployment-info.txt" <<EOF
FinagentiX Deployment Information
==================================
Date: $(date)
Resource Group: $AZURE_RESOURCE_GROUP
Location: $AZURE_LOCATION
Resource Token: $RESOURCE_TOKEN

VM Public IP: $VM_PUBLIC_IP
VM Username: azureuser
VM Password: DebugVM2024!@#

Redis Password: $REDIS_PASSWORD

Featureform Host: featureform-${RESOURCE_TOKEN}.internal.${AZURE_LOCATION}.azurecontainerapps.io
Redis Host: redis-${RESOURCE_TOKEN}.${AZURE_LOCATION}.redisenterprise.cache.azure.net
EOF

echo "💾 Deployment info saved to: /tmp/finagentix-deployment-info.txt"
echo ""
