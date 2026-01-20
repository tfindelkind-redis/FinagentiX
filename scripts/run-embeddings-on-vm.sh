#!/bin/bash
# ============================================================
# Run Embedding Generation on Debug VM
# ============================================================
# This script runs the embedding pipeline on the debug VM which
# is inside the VNet and can access Azure OpenAI without public access.
#
# Usage:
#   ./scripts/run-embeddings-on-vm.sh [--news-only] [--sec-only] [--refresh]
#
# Requirements:
#   - Azure CLI logged in
#   - SSH key configured for VM access
# ============================================================

set -e

# Configuration
RESOURCE_GROUP="finagentix-dev-rg"
VM_NAME="debug-vm-3ae172dc9e9da"
SCRIPT_PATH="/opt/finagentix/scripts/generate_embeddings_azure.py"

# Parse arguments
NEWS_ONLY=""
SEC_ONLY=""
REFRESH=""
TICKERS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --news-only)
            NEWS_ONLY="--skip-sec"
            shift
            ;;
        --sec-only)
            SEC_ONLY="--skip-news"
            shift
            ;;
        --refresh)
            REFRESH="--refresh"
            shift
            ;;
        --tickers)
            shift
            TICKERS="--tickers $1"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=============================================="
echo "🚀 Running Embedding Pipeline on Debug VM"
echo "=============================================="
echo ""

# Get VM public IP
echo "📍 Getting VM IP address..."
VM_IP=$(az vm list-ip-addresses \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --query "[0].virtualMachine.network.publicIpAddresses[0].ipAddress" \
    -o tsv 2>/dev/null)

if [ -z "$VM_IP" ]; then
    echo "❌ Could not get VM IP. VM might not have public IP or NSG rules may block access."
    echo ""
    echo "Alternative: Run commands via Azure Run Command..."
    
    # Use Azure Run Command instead
    CMD="cd /opt/finagentix && source venv/bin/activate && python scripts/generate_embeddings_azure.py $NEWS_ONLY $SEC_ONLY $REFRESH $TICKERS --verbose"
    
    echo "📤 Executing on VM via Run Command..."
    echo "   Command: $CMD"
    echo ""
    
    az vm run-command invoke \
        --resource-group "$RESOURCE_GROUP" \
        --name "$VM_NAME" \
        --command-id RunShellScript \
        --scripts "$CMD" \
        --query "value[0].message" \
        -o tsv
    
    exit 0
fi

echo "   VM IP: $VM_IP"
echo ""

# Check if we can SSH
echo "🔑 Testing SSH connection..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "azureuser@$VM_IP" exit 2>/dev/null; then
    echo "⚠️  Direct SSH not available. Using Azure Run Command..."
    
    CMD="cd /opt/finagentix && source venv/bin/activate && python scripts/generate_embeddings_azure.py $NEWS_ONLY $SEC_ONLY $REFRESH $TICKERS --verbose"
    
    echo "📤 Executing on VM..."
    echo "   Command: $CMD"
    echo ""
    
    az vm run-command invoke \
        --resource-group "$RESOURCE_GROUP" \
        --name "$VM_NAME" \
        --command-id RunShellScript \
        --scripts "$CMD" \
        --query "value[0].message" \
        -o tsv
    
    exit 0
fi

# SSH is available, sync code and run
echo "✅ SSH connection OK"
echo ""

# Sync the scripts to VM
echo "📂 Syncing scripts to VM..."
rsync -avz --progress \
    scripts/generate_embeddings_azure.py \
    "azureuser@$VM_IP:/opt/finagentix/scripts/"

# Sync .env file
rsync -avz --progress \
    .env \
    "azureuser@$VM_IP:/opt/finagentix/"

# Ensure dependencies are installed
echo "📦 Ensuring Python dependencies..."
ssh "azureuser@$VM_IP" "source /opt/finagentix/venv/bin/activate 2>/dev/null || (cd /opt/finagentix && python3 -m venv venv); source /opt/finagentix/venv/bin/activate && pip install -q openai azure-storage-blob redis python-dotenv numpy beautifulsoup4 lxml pandas pyarrow"

echo ""
echo "🚀 Running embedding pipeline..."
echo ""

# Run the embedding script
ssh "azureuser@$VM_IP" << EOF
cd /opt/finagentix
source venv/bin/activate
python scripts/generate_embeddings_azure.py $NEWS_ONLY $SEC_ONLY $REFRESH $TICKERS --verbose
EOF

echo ""
echo "✅ Embedding generation complete!"
