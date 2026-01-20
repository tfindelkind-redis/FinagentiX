#!/bin/bash
set -e

# Full Deployment Script for FinagentiX
# Supports selective step execution for redeployment scenarios

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
export AZURE_ENV_NAME="${AZURE_ENV_NAME:-dev}"
export AZURE_LOCATION="${AZURE_LOCATION:-westus3}"
export AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-finagentix-${AZURE_ENV_NAME}-rg}"

# Default: run all steps
START_STEP=1
END_STEP=8
SKIP_PROMPTS=false

# Parse arguments
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --step N         Run only step N"
    echo "  --from N         Start from step N (default: 1)"
    echo "  --to N           End at step N (default: 8)"
    echo "  --skip-prompts   Skip all confirmation prompts"
    echo "  --clean          Delete and recreate resource group first"
    echo "  -h, --help       Show this help message"
    echo ""
    echo "Steps:"
    echo "  1 - Deploy Infrastructure (VNet, Redis, OpenAI, Storage, API, Frontend)"
    echo "  2 - Deploy Featureform"
    echo "  3 - Deploy Debug VM (waits for SSH access)"
    echo "  4 - Upload Data to Azure Storage"
    echo "  5 - Apply Featureform Definitions"
    echo "  6 - Generate Embeddings (news, SEC filings)"
    echo "  7 - Load Market Data (stock prices)"
    echo "  8 - Verify Deployment"
    echo ""
    echo "Examples:"
    echo "  $0                     # Run all steps (1-8)"
    echo "  $0 --step 4            # Run only step 4 (upload data)"
    echo "  $0 --from 4            # Run steps 4-8"
    echo "  $0 --from 3 --to 5     # Run steps 3, 4, 5"
    echo "  $0 --step 6            # Regenerate embeddings only"
    echo "  $0 --step 7            # Load market data only"
    echo "  $0 --clean             # Full redeploy from scratch"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --step)
            START_STEP=$2
            END_STEP=$2
            shift 2
            ;;
        --from)
            START_STEP=$2
            shift 2
            ;;
        --to)
            END_STEP=$2
            shift 2
            ;;
        --skip-prompts)
            SKIP_PROMPTS=true
            shift
            ;;
        --clean)
            CLEAN_DEPLOY=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

echo "=========================================="
echo "🚀 FinagentiX Deployment"
echo "=========================================="
echo "Resource Group: $AZURE_RESOURCE_GROUP"
echo "Location: $AZURE_LOCATION"
echo "Environment: $AZURE_ENV_NAME"
echo "Steps: $START_STEP → $END_STEP"
echo ""

# Function to wait for resource group deletion
wait_for_deletion() {
    local rg=$1
    echo "⏳ Waiting for resource group deletion to complete..."
    local count=0
    while az group exists --name "$rg" 2>/dev/null | grep -q "true"; do
        count=$((count + 1))
        if [ $((count % 6)) -eq 0 ]; then
            echo "   Still deleting... $((count / 6)) minute(s) elapsed"
        fi
        sleep 10
    done
    echo "✅ Resource group deleted"
}

# Function to get deployment info
get_deployment_info() {
    # Try to get resource token from existing deployment
    RESOURCE_TOKEN=$(az deployment group list -g "$AZURE_RESOURCE_GROUP" \
        --query "[?contains(name, 'stage0')].properties.parameters.resourceToken.value | [0]" -o tsv 2>/dev/null || echo "")
    
    if [ -z "$RESOURCE_TOKEN" ]; then
        # Generate a new one if not found
        RESOURCE_TOKEN=$(openssl rand -hex 4)
    fi
    export RESOURCE_TOKEN
}

# Function to check if resource group exists
check_resource_group() {
    az group exists --name "$AZURE_RESOURCE_GROUP" 2>/dev/null | grep -q "true"
}

# Function to wait for VM to be accessible via SSH
wait_for_vm_ready() {
    local max_attempts=30
    local attempt=1
    local wait_seconds=20
    
    echo "⏳ Waiting for Debug VM to be fully accessible..."
    
    # First, wait for VM to be in running state
    while [ $attempt -le $max_attempts ]; do
        VM_STATE=$(az vm list -g "$AZURE_RESOURCE_GROUP" -d \
            --query "[?contains(name, 'debug')].powerState | [0]" -o tsv 2>/dev/null || echo "")
        
        if [ "$VM_STATE" = "VM running" ]; then
            echo "   ✅ VM is running"
            break
        fi
        
        echo "   Attempt $attempt/$max_attempts: VM state is '$VM_STATE', waiting..."
        sleep $wait_seconds
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        echo "   ❌ VM did not start within timeout"
        return 1
    fi
    
    # Get VM IP
    VM_PUBLIC_IP=$(az vm list -g "$AZURE_RESOURCE_GROUP" -d \
        --query "[?contains(name, 'debug')].publicIps | [0]" -o tsv 2>/dev/null)
    
    if [ -z "$VM_PUBLIC_IP" ]; then
        echo "   ❌ Could not get VM public IP"
        return 1
    fi
    
    echo "   VM IP: $VM_PUBLIC_IP"
    
    # Now wait for SSH to be accessible
    attempt=1
    echo "⏳ Waiting for SSH to be accessible..."
    
    while [ $attempt -le $max_attempts ]; do
        if ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
            "azureuser@${VM_PUBLIC_IP}" "exit" 2>/dev/null; then
            echo "   ✅ SSH is accessible"
            return 0
        fi
        
        echo "   Attempt $attempt/$max_attempts: SSH not ready, waiting ${wait_seconds}s..."
        sleep $wait_seconds
        attempt=$((attempt + 1))
    done
    
    echo "   ❌ SSH did not become accessible within timeout"
    return 1
}

# Clean deploy if requested
if [ "$CLEAN_DEPLOY" = true ]; then
    if check_resource_group; then
        echo "🗑️  Deleting existing resource group..."
        export SKIP_CONFIRM=1
        "$SCRIPT_DIR/cleanup.sh" || true
        wait_for_deletion "$AZURE_RESOURCE_GROUP"
    fi
fi

# Check if starting from step > 1 but resource group doesn't exist
if [ "$START_STEP" -gt 1 ] && ! check_resource_group; then
    echo "❌ Error: Resource group '$AZURE_RESOURCE_GROUP' does not exist"
    echo "   Cannot start from step $START_STEP without existing infrastructure"
    echo "   Run with --from 1 or without arguments to deploy from scratch"
    exit 1
fi

# Get deployment info for later steps
if [ "$START_STEP" -gt 1 ]; then
    get_deployment_info
fi

# ============================================
# Step 1: Deploy Infrastructure
# ============================================
if [ "$START_STEP" -le 1 ] && [ "$END_STEP" -ge 1 ]; then
    echo ""
    echo "=========================================="
    echo "Step 1/8: Deploying Infrastructure"
    echo "=========================================="
    
    # Check if resource group exists for fresh deploy
    if check_resource_group && [ "$START_STEP" -eq 1 ]; then
        if [ "$SKIP_PROMPTS" = true ]; then
            echo "⚠️  Resource group exists, skipping infrastructure (use --clean to redeploy)"
        else
            echo "⚠️  Resource group '$AZURE_RESOURCE_GROUP' already exists"
            read -p "Delete and recreate? (yes/no): " confirm
            if [ "$confirm" = "yes" ]; then
                export SKIP_CONFIRM=1
                "$SCRIPT_DIR/cleanup.sh"
                wait_for_deletion "$AZURE_RESOURCE_GROUP"
                "$SCRIPT_DIR/deploy.sh"
            else
                echo "   Skipping infrastructure deployment"
            fi
        fi
    else
        "$SCRIPT_DIR/deploy.sh"
    fi
    
    get_deployment_info
    
    # Update .env with deployed infrastructure values
    echo "📄 Updating .env with infrastructure values..."
    "$SCRIPT_DIR/update-env.sh" --all
    
    echo "✅ Step 1 complete"
fi

# ============================================
# Step 2: Deploy Featureform
# ============================================
if [ "$START_STEP" -le 2 ] && [ "$END_STEP" -ge 2 ]; then
    echo ""
    echo "=========================================="
    echo "Step 2/8: Deploying Featureform"
    echo "=========================================="
    "$SCRIPT_DIR/deploy-featureform.sh"
    echo "✅ Step 2 complete"
fi

# ============================================
# Step 3: Deploy Debug VM
# ============================================
if [ "$START_STEP" -le 3 ] && [ "$END_STEP" -ge 3 ]; then
    echo ""
    echo "=========================================="
    echo "Step 3/8: Deploying Debug VM"
    echo "=========================================="
    "$SCRIPT_DIR/deploy-debug-vm.sh"
    
    # Update .env with VM IP
    echo "📄 Updating .env with VM IP..."
    "$SCRIPT_DIR/update-env.sh" --vm
    
    # Wait for VM to be fully accessible
    if ! wait_for_vm_ready; then
        echo "⚠️  VM may not be fully ready"
        echo "   Subsequent steps may fail - retry with: $0 --from 4"
    fi
    
    echo "✅ Step 3 complete"
fi

# ============================================
# Step 4: Upload Data
# ============================================
if [ "$START_STEP" -le 4 ] && [ "$END_STEP" -ge 4 ]; then
    echo ""
    echo "=========================================="
    echo "Step 4/8: Uploading Data to Azure Storage"
    echo "=========================================="
    if [ -d "$SCRIPT_DIR/../../data" ]; then
        "$SCRIPT_DIR/upload-data.sh"
    else
        echo "⚠️  No local data/ directory found"
        echo "   Skipping data upload"
    fi
    echo "✅ Step 4 complete"
fi

# ============================================
# Step 5: Apply Featureform Definitions
# ============================================
if [ "$START_STEP" -le 5 ] && [ "$END_STEP" -ge 5 ]; then
    echo ""
    echo "=========================================="
    echo "Step 5/8: Applying Featureform Definitions"
    echo "=========================================="
    "$SCRIPT_DIR/connect-and-apply.sh" || {
        echo "⚠️  Featureform definitions application failed"
        echo "   This may be expected if Featureform is not yet ready"
        echo "   Retry with: $0 --step 5"
    }
    echo "✅ Step 5 complete"
fi

# ============================================
# Step 6: Generate Embeddings
# ============================================
if [ "$START_STEP" -le 6 ] && [ "$END_STEP" -ge 6 ]; then
    echo ""
    echo "=========================================="
    echo "Step 6/8: Generating Embeddings"
    echo "=========================================="
    
    # Ensure VM is ready before running embeddings
    if ! wait_for_vm_ready; then
        echo "⚠️  VM not accessible, cannot generate embeddings"
        echo "   Retry with: $0 --step 6"
    else
        "$SCRIPT_DIR/generate-embeddings.sh" --resume || {
            echo "⚠️  Embedding generation failed or incomplete"
            echo "   Retry with: $0 --step 6"
            echo "   Or manually: ./infra/scripts/generate-embeddings.sh --resume"
        }
    fi
    echo "✅ Step 6 complete"
fi

# ============================================
# Step 7: Load Market Data
# ============================================
if [ "$START_STEP" -le 7 ] && [ "$END_STEP" -ge 7 ]; then
    echo ""
    echo "=========================================="
    echo "Step 7/8: Loading Market Data (Stock Prices)"
    echo "=========================================="
    
    # Ensure VM is ready before loading market data
    if ! wait_for_vm_ready; then
        echo "⚠️  VM not accessible, cannot load market data"
        echo "   Retry with: $0 --step 7"
    else
        "$SCRIPT_DIR/load-market-data.sh" all || {
            echo "⚠️  Market data loading failed or incomplete"
            echo "   Retry with: $0 --step 7"
            echo "   Or manually: ./infra/scripts/load-market-data.sh all"
        }
    fi
    echo "✅ Step 7 complete"
fi

# ============================================
# Step 8: Verify Deployment
# ============================================
if [ "$START_STEP" -le 8 ] && [ "$END_STEP" -ge 8 ]; then
    echo ""
    echo "=========================================="
    echo "Step 8/8: Verifying Deployment"
    echo "=========================================="
    
    echo "🔍 Checking API health..."
    API_FQDN=$(az containerapp list -g "$AZURE_RESOURCE_GROUP" \
        --query "[?contains(name, 'agent-api')].properties.configuration.ingress.fqdn | [0]" -o tsv 2>/dev/null || echo "")
    
    if [ -n "$API_FQDN" ]; then
        echo "   API URL: https://$API_FQDN"
        # Wait for API to be healthy
        MAX_ATTEMPTS=30
        ATTEMPT=1
        while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://$API_FQDN/api/health" 2>/dev/null || echo "000")
            if [ "$HTTP_CODE" = "200" ]; then
                echo "   ✅ API is healthy (HTTP $HTTP_CODE)"
                break
            fi
            echo "   Attempt $ATTEMPT/$MAX_ATTEMPTS: API returned HTTP $HTTP_CODE, waiting..."
            sleep 10
            ATTEMPT=$((ATTEMPT + 1))
        done
        
        if [ $ATTEMPT -gt $MAX_ATTEMPTS ]; then
            echo "   ⚠️  API health check timed out"
        fi
    else
        echo "   ⚠️  Could not get API URL"
    fi
    
    echo ""
    echo "🔍 Checking Frontend health..."
    FRONTEND_FQDN=$(az containerapp list -g "$AZURE_RESOURCE_GROUP" \
        --query "[?contains(name, 'frontend')].properties.configuration.ingress.fqdn | [0]" -o tsv 2>/dev/null || echo "")
    
    if [ -n "$FRONTEND_FQDN" ]; then
        echo "   Frontend URL: https://$FRONTEND_FQDN"
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://$FRONTEND_FQDN" 2>/dev/null || echo "000")
        if [ "$HTTP_CODE" = "200" ]; then
            echo "   ✅ Frontend is healthy (HTTP $HTTP_CODE)"
        else
            echo "   ⚠️  Frontend returned HTTP $HTTP_CODE"
        fi
    else
        echo "   ⚠️  Could not get Frontend URL"
    fi
    
    echo ""
    echo "🔍 Checking Redis indexes..."
    if [ -n "$VM_PUBLIC_IP" ]; then
        # Try to check Redis via the VM
        REDIS_CLUSTER=$(az redisenterprise list -g "$AZURE_RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || echo "")
        if [ -n "$REDIS_CLUSTER" ]; then
            REDIS_HOST=$(az redisenterprise show -g "$AZURE_RESOURCE_GROUP" -n "$REDIS_CLUSTER" --query "hostName" -o tsv 2>/dev/null)
            REDIS_PASSWORD=$(az redisenterprise database list-keys -g "$AZURE_RESOURCE_GROUP" --cluster-name "$REDIS_CLUSTER" --query "primaryKey" -o tsv 2>/dev/null)
            
            # Check via API debug endpoint
            if [ -n "$API_FQDN" ]; then
                echo "   Checking indexes via API..."
                curl -s "https://$API_FQDN/api/debug/redis-indexes" 2>/dev/null | head -c 500 || echo "Could not query indexes"
            fi
        fi
    fi
    
    echo "✅ Step 8 complete"
fi

# ============================================
# Summary
# ============================================
echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo "Steps executed: $START_STEP → $END_STEP"
echo ""

# Get and display deployment info
get_deployment_info

# Get VM public IP if available
VM_PUBLIC_IP=$(az vm list -g "$AZURE_RESOURCE_GROUP" -d \
    --query "[?contains(name, 'debug')].publicIps | [0]" -o tsv 2>/dev/null || echo "N/A")

# Get Redis password if available
REDIS_CLUSTER=$(az redisenterprise list -g "$AZURE_RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || echo "")
if [ -n "$REDIS_CLUSTER" ]; then
    REDIS_PASSWORD=$(az redisenterprise database list-keys \
        -g "$AZURE_RESOURCE_GROUP" \
        --cluster-name "$REDIS_CLUSTER" \
        --query "primaryKey" -o tsv 2>/dev/null || echo "N/A")
    REDIS_HOST=$(az redisenterprise show -g "$AZURE_RESOURCE_GROUP" -n "$REDIS_CLUSTER" \
        --query "hostName" -o tsv 2>/dev/null || echo "N/A")
else
    REDIS_PASSWORD="N/A"
    REDIS_HOST="N/A"
fi

# Get Frontend URL
FRONTEND_URL=$(az containerapp list -g "$AZURE_RESOURCE_GROUP" \
    --query "[?contains(name, 'frontend')].properties.configuration.ingress.fqdn | [0]" -o tsv 2>/dev/null || echo "N/A")
API_URL=$(az containerapp list -g "$AZURE_RESOURCE_GROUP" \
    --query "[?contains(name, 'agent-api')].properties.configuration.ingress.fqdn | [0]" -o tsv 2>/dev/null || echo "N/A")

echo "📋 Deployment Information:"
echo "   Resource Group: $AZURE_RESOURCE_GROUP"
echo "   Location: $AZURE_LOCATION"
echo "   Debug VM IP: $VM_PUBLIC_IP"
echo "   Redis Host: $REDIS_HOST"
if [ "$FRONTEND_URL" != "N/A" ]; then
    echo "   Frontend URL: https://$FRONTEND_URL"
fi
if [ "$API_URL" != "N/A" ]; then
    echo "   API URL: https://$API_URL"
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

Redis Host: $REDIS_HOST
Redis Password: $REDIS_PASSWORD

Frontend URL: https://$FRONTEND_URL
API URL: https://$API_URL
EOF

echo "💾 Deployment info saved to: /tmp/finagentix-deployment-info.txt"
echo ""
echo "🔧 To redeploy specific steps:"
echo "   $0 --step N       # Run only step N"
echo "   $0 --from N       # Run from step N onwards"
echo "   $0 --from N --to M  # Run steps N through M"
echo ""
echo "📋 All Steps:"
echo "   1 - Infrastructure (VNet, Redis, OpenAI, Storage, API, Frontend)"
echo "   2 - Featureform"
echo "   3 - Debug VM (waits for SSH access)"
echo "   4 - Upload Data to Storage"
echo "   5 - Featureform Definitions"
echo "   6 - Generate Embeddings (news, SEC filings)"
echo "   7 - Load Market Data (stock prices)"
echo "   8 - Verify Deployment (health checks)"
echo ""
