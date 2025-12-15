#!/bin/bash

# Script to connect to debug VM and apply Featureform definitions
# Run this from your local machine

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================="
echo "Connect to VM and Apply Definitions"
echo "========================================="
echo ""

# Get configuration from azd or environment
AZURE_ENV_NAME="${AZURE_ENV_NAME:-dev}"
LOCATION=$(azd env get-value AZURE_LOCATION 2>/dev/null || echo "${AZURE_LOCATION:-westus3}")
RESOURCE_GROUP="finagentix-${AZURE_ENV_NAME}-rg"

# Get resource token from deployed resources (extract from VM name)
RESOURCE_TOKEN=$(az vm list -g "$RESOURCE_GROUP" --query "[?starts_with(name, 'debug-vm-')].name" -o tsv 2>/dev/null | sed 's/debug-vm-//' | head -n 1)

if [ -z "$RESOURCE_TOKEN" ]; then
  echo "❌ Could not find resource token from deployed resources"
  echo "   Make sure the debug VM is deployed"
  exit 1
fi

echo "📋 Configuration:"
echo "  Resource Token: $RESOURCE_TOKEN"
echo "  Location: $LOCATION"
echo "  Resource Group: $RESOURCE_GROUP"
echo ""

# Resolve Featureform endpoint
FEATUREFORM_HOST=$(az containerapp show -g "$RESOURCE_GROUP" -n "featureform-${RESOURCE_TOKEN}" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
STATIC_IP=$(az containerapp env show -g "$RESOURCE_GROUP" -n "cae-${RESOURCE_TOKEN}" --query "properties.staticIp" -o tsv 2>/dev/null || echo "")

if [ -n "$FEATUREFORM_HOST" ] && [ "$FEATUREFORM_HOST" != "null" ]; then
  echo "✅ Featureform host detected: https://$FEATUREFORM_HOST"
else
  FEATUREFORM_HOST="featureform-${RESOURCE_TOKEN}.internal.${LOCATION}.azurecontainerapps.io"
  echo "⚠️  Falling back to internal Featureform host: https://$FEATUREFORM_HOST"
fi

if [ -n "$STATIC_IP" ] && [ "$STATIC_IP" != "null" ]; then
  echo "✅ Featureform static IP: $STATIC_IP"
else
  echo "⚠️  Could not determine static IP for Container Apps environment"
fi
echo ""

# Get Redis password
echo "🔑 Retrieving Redis password..."
REDIS_PASSWORD=$(az redisenterprise database list-keys \
  -g "$RESOURCE_GROUP" \
  --cluster-name "redis-${RESOURCE_TOKEN}" \
  --query "primaryKey" -o tsv)

if [ -z "$REDIS_PASSWORD" ]; then
  echo "❌ Failed to retrieve Redis password"
  exit 1
fi

echo "✅ Redis password retrieved"
echo ""

# Get VM public IP
echo "🔍 Getting VM public IP..."
VM_IP=$(az vm show -g "$RESOURCE_GROUP" -n "debug-vm-${RESOURCE_TOKEN}" -d \
  --query "publicIps" -o tsv)

if [ -z "$VM_IP" ]; then
  echo "❌ Failed to retrieve VM IP"
  exit 1
fi

echo "✅ VM IP: $VM_IP"

# Ensure SSH key is set up
echo ""
echo "🔐 Checking SSH setup..."
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no "azureuser@${VM_IP}" "exit" 2>/dev/null; then
    echo "⚠️  Passwordless SSH not configured. Setting up..."
    if ! "$SCRIPT_DIR/setup-ssh-key.sh"; then
        echo "❌ SSH setup failed"
        exit 1
    fi
fi
echo "✅ SSH configured"
echo ""

# Create temporary script to run on VM
TEMP_SCRIPT=$(mktemp)
cat > "$TEMP_SCRIPT" << 'EOFSCRIPT'
#!/bin/bash
set -e

RESOURCE_TOKEN="__RESOURCE_TOKEN__"
REDIS_PASSWORD="__REDIS_PASSWORD__"
LOCATION="__LOCATION__"

echo "========================================="
echo "Running on VM: Applying Definitions"
echo "========================================="
echo ""

# Environment variables
export FEATUREFORM_HOST="__FEATUREFORM_HOST__"
export FEATUREFORM_STATIC_IP="__FEATUREFORM_STATIC_IP__"
if [ -n "$FEATUREFORM_STATIC_IP" ]; then
  if ! grep -q "$FEATUREFORM_HOST" /etc/hosts; then
    echo "🛠️  Adding hosts entry for $FEATUREFORM_HOST"
    sudo sh -c "echo '${FEATUREFORM_STATIC_IP} ${FEATUREFORM_HOST}' >> /etc/hosts"
  fi
fi
export REDIS_HOST="redis-${RESOURCE_TOKEN}.${LOCATION}.redisenterprise.cache.azure.net"
export REDIS_PORT="10000"
export REDIS_PASSWORD="${REDIS_PASSWORD}"

echo "📋 Configuration:"
echo "  Featureform: $FEATUREFORM_HOST"
echo "  Redis: $REDIS_HOST:$REDIS_PORT"
echo ""

# Clone or update repository
if [ -d "/tmp/FinagentiX" ]; then
  echo "🔄 Updating repository..."
  cd /tmp/FinagentiX
  git pull
else
  echo "📥 Cloning repository..."
  git clone https://github.com/tfindelkind-redis/FinagentiX.git /tmp/FinagentiX
  cd /tmp/FinagentiX
fi

echo ""
echo "🚀 Applying Featureform definitions..."
python3 featureform/definitions.py

echo ""
echo "✅ Definitions applied successfully!"
echo ""
echo "📊 Verifying features..."
python3 << 'EOF'
import featureform as ff
import os

try:
    client = ff.Client(host=os.getenv("FEATUREFORM_HOST"))
    features = client.list_features()
    print(f"✅ Registered {len(features)} features")
    if len(features) > 0:
        print("\nTop 10 features:")
        for f in features[:10]:
            print(f"  • {f.name}")
    else:
        print("⚠️  No features found - definitions may not have been applied")
except Exception as e:
    print(f"❌ Error verifying features: {e}")
EOF

echo ""
echo "🎉 Done!"
EOFSCRIPT

# Replace placeholders
sed -i '' "s/__RESOURCE_TOKEN__/${RESOURCE_TOKEN}/g" "$TEMP_SCRIPT"
sed -i '' "s/__REDIS_PASSWORD__/${REDIS_PASSWORD}/g" "$TEMP_SCRIPT"
sed -i '' "s/__LOCATION__/${LOCATION}/g" "$TEMP_SCRIPT"
sed -i '' "s/__FEATUREFORM_HOST__/${FEATUREFORM_HOST}/g" "$TEMP_SCRIPT"
sed -i '' "s/__FEATUREFORM_STATIC_IP__/${STATIC_IP}/g" "$TEMP_SCRIPT"

echo "🚀 Connecting to VM and running setup..."
echo ""
# Copy script to VM and execute
scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  "$TEMP_SCRIPT" "azureuser@${VM_IP}:/tmp/apply-definitions.sh"

ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  "azureuser@${VM_IP}" "chmod +x /tmp/apply-definitions.sh && /tmp/apply-definitions.sh"

# Cleanup
rm "$TEMP_SCRIPT"

echo ""
echo "========================================="
echo "✅ Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Verify features are working in your agent code"
echo "  2. Test feature retrieval"
echo ""
echo "To SSH to the VM manually:"
echo "  ssh azureuser@${VM_IP}"
echo ""
