#!/bin/bash

# Script to apply Featureform definitions from inside the debug VM
# This runs on the VM which has access to the internal Featureform server
# Usage: ./apply-definitions-on-vm.sh <resource-token> <redis-password> <location>

set -e

# Get parameters
RESOURCE_TOKEN="${1}"
REDIS_PASSWORD="${2}"
LOCATION="${3}"

if [ -z "$RESOURCE_TOKEN" ] || [ -z "$REDIS_PASSWORD" ] || [ -z "$LOCATION" ]; then
    echo "Usage: $0 <resource-token> <redis-password> <location>"
    echo "Example: $0 abc123def4567 mypassword westus3"
    exit 1
fi

echo "========================================="
echo "Applying Featureform Definitions"
echo "========================================="

# Environment variables - dynamically built based on region
export FEATUREFORM_HOST="featureform-${RESOURCE_TOKEN}.internal.${LOCATION}.azurecontainerapps.io"
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

client = ff.Client(host=os.getenv("FEATUREFORM_HOST"), insecure=True)
features = client.list_features()
print(f"✅ Registered {len(features)} features")
for f in features[:10]:
    print(f"  • {f.name}")
EOF

echo ""
echo "🎉 Done!"
