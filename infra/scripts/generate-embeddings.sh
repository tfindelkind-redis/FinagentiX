#!/bin/bash
set -e

# Generate embeddings from Azure Storage and index in Redis
# This script runs the embedding pipeline on the Debug VM

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-rg-finagentix-dev}"

echo "=========================================="
echo "🧮 FinagentiX - Embedding Generation"
echo "=========================================="

# Parse arguments
RESUME_FLAG=""
REFRESH_FLAG=""
TICKERS_ARG=""
LIMIT_ARG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --resume)
            RESUME_FLAG="--resume"
            shift
            ;;
        --refresh)
            REFRESH_FLAG="--refresh"
            shift
            ;;
        --tickers)
            TICKERS_ARG="--tickers $2"
            shift 2
            ;;
        --limit)
            LIMIT_ARG="--limit $2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Get Debug VM IP
VM_PUBLIC_IP=$(az vm show -g "$AZURE_RESOURCE_GROUP" -n "vm-debug-*" -d --query "publicIps" -o tsv 2>/dev/null || \
    az vm list -g "$AZURE_RESOURCE_GROUP" -d --query "[?contains(name, 'debug')].publicIps | [0]" -o tsv 2>/dev/null)

if [ -z "$VM_PUBLIC_IP" ]; then
    echo "❌ Debug VM not found in resource group $AZURE_RESOURCE_GROUP"
    echo "   Please deploy the debug VM first: ./infra/scripts/deploy-debug-vm.sh"
    exit 1
fi

echo "🖥️  Debug VM: $VM_PUBLIC_IP"

# Get Azure credentials
echo ""
echo "📋 Getting Azure credentials..."

# Storage account
STORAGE_ACCOUNT=$(az storage account list -g "$AZURE_RESOURCE_GROUP" --query "[0].name" -o tsv)
STORAGE_KEY=$(az storage account keys list -g "$AZURE_RESOURCE_GROUP" -n "$STORAGE_ACCOUNT" --query "[0].value" -o tsv)

# OpenAI
OPENAI_NAME=$(az cognitiveservices account list -g "$AZURE_RESOURCE_GROUP" --query "[0].name" -o tsv)
OPENAI_ENDPOINT=$(az cognitiveservices account show -g "$AZURE_RESOURCE_GROUP" -n "$OPENAI_NAME" --query "properties.endpoint" -o tsv)
OPENAI_KEY=$(az cognitiveservices account keys list -g "$AZURE_RESOURCE_GROUP" -n "$OPENAI_NAME" --query "key1" -o tsv)

# Redis - find the Enterprise cluster
REDIS_CLUSTER=$(az redisenterprise list -g "$AZURE_RESOURCE_GROUP" --query "[0].name" -o tsv)
REDIS_HOST=$(az redisenterprise show -g "$AZURE_RESOURCE_GROUP" -n "$REDIS_CLUSTER" --query "hostName" -o tsv)
REDIS_PASSWORD=$(az redisenterprise database list-keys -g "$AZURE_RESOURCE_GROUP" --cluster-name "$REDIS_CLUSTER" --query "primaryKey" -o tsv)

# Try to get private IP for Redis
REDIS_PRIVATE_IP=$(az network private-endpoint show \
    -g "$AZURE_RESOURCE_GROUP" \
    -n "pe-redis-*" \
    --query "customDnsConfigs[0].ipAddresses[0]" -o tsv 2>/dev/null || echo "")

if [ -n "$REDIS_PRIVATE_IP" ]; then
    echo "   Using Redis private IP: $REDIS_PRIVATE_IP"
    REDIS_HOST_TO_USE="$REDIS_PRIVATE_IP"
else
    echo "   Using Redis hostname: $REDIS_HOST"
    REDIS_HOST_TO_USE="$REDIS_HOST"
fi

echo ""
echo "🔗 Connecting to Debug VM..."

# Create remote script
REMOTE_SCRIPT=$(cat <<'SCRIPT_EOF'
#!/bin/bash
set -e

echo "Setting up environment on Debug VM..."

# Clone or update repo
if [ -d ~/FinagentiX ]; then
    cd ~/FinagentiX
    git pull --quiet
else
    git clone https://github.com/tfindelkind-redis/FinagentiX.git ~/FinagentiX
    cd ~/FinagentiX
fi

# Setup Python environment
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

# Create .env file
cat > .env <<EOF
AZURE_OPENAI_ENDPOINT=$OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY=$OPENAI_KEY
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large

REDIS_HOST=$REDIS_HOST
REDIS_PORT=10000
REDIS_PASSWORD=$REDIS_PASSWORD

AZURE_STORAGE_ACCOUNT_NAME=$STORAGE_ACCOUNT
AZURE_STORAGE_ACCOUNT_KEY=$STORAGE_KEY
EOF

echo "Running embedding pipeline..."
python scripts/generate_embeddings_azure.py $PIPELINE_ARGS

echo "Done!"
SCRIPT_EOF
)

# Run on remote VM
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 "azureuser@$VM_PUBLIC_IP" \
    "OPENAI_ENDPOINT='$OPENAI_ENDPOINT' \
     OPENAI_KEY='$OPENAI_KEY' \
     REDIS_HOST='$REDIS_HOST_TO_USE' \
     REDIS_PASSWORD='$REDIS_PASSWORD' \
     STORAGE_ACCOUNT='$STORAGE_ACCOUNT' \
     STORAGE_KEY='$STORAGE_KEY' \
     PIPELINE_ARGS='$RESUME_FLAG $REFRESH_FLAG $TICKERS_ARG $LIMIT_ARG' \
     bash -s" <<< "$REMOTE_SCRIPT"

echo ""
echo "=========================================="
echo "✅ Embedding Generation Complete!"
echo "=========================================="
