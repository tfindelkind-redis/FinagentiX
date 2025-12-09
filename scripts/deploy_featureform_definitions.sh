#!/bin/bash
# Deploy Featureform definitions to Azure
# This script applies feature definitions after infrastructure is deployed

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Featureform Definitions Deployment ===${NC}"

# Check if FEATUREFORM_HOST is set
if [ -z "$FEATUREFORM_HOST" ]; then
    echo -e "${YELLOW}FEATUREFORM_HOST not set. Getting from Azure...${NC}"
    
    # Get resource group from azd
    RESOURCE_GROUP=$(azd env get-values | grep AZURE_RESOURCE_GROUP | cut -d'=' -f2 | tr -d '"')
    
    if [ -z "$RESOURCE_GROUP" ]; then
        echo -e "${RED}Error: Could not find AZURE_RESOURCE_GROUP. Run 'azd up' first.${NC}"
        exit 1
    fi
    
    # Get Featureform host from deployment outputs
    FEATUREFORM_HOST=$(az deployment group show \
        --resource-group "$RESOURCE_GROUP" \
        --name main \
        --query "properties.outputs.FEATUREFORM_HOST.value" -o tsv 2>/dev/null)
    
    if [ -z "$FEATUREFORM_HOST" ]; then
        echo -e "${RED}Error: Featureform not deployed. Run 'azd up' first.${NC}"
        exit 1
    fi
    
    export FEATUREFORM_HOST
    echo -e "${GREEN}✓ Found Featureform host: $FEATUREFORM_HOST${NC}"
fi

# Set other Featureform environment variables
export FEATUREFORM_PORT=443
export FEATUREFORM_INSECURE=false

# Get Redis credentials from Azure
echo -e "${BLUE}Getting Redis credentials...${NC}"
REDIS_HOST=$(azd env get-values | grep REDIS_HOST | cut -d'=' -f2 | tr -d '"')
REDIS_PORT=$(azd env get-values | grep REDIS_PORT | cut -d'=' -f2 | tr -d '"')
REDIS_PASSWORD=$(azd env get-values | grep REDIS_PASSWORD | cut -d'=' -f2 | tr -d '"')

export REDIS_HOST
export REDIS_PORT
export REDIS_PASSWORD

echo -e "${GREEN}✓ Redis configuration loaded${NC}"

# Check if featureform CLI is installed
if ! command -v featureform &> /dev/null; then
    echo -e "${YELLOW}Featureform CLI not found. Install with:${NC}"
    echo -e "  ${BLUE}pip install featureform${NC}"
    echo -e "${YELLOW}Continuing with Python client...${NC}"
    
    # Use Python to apply definitions
    echo -e "${BLUE}Applying feature definitions via Python...${NC}"
    python3 << 'PYTHON_SCRIPT'
import os
import sys

try:
    import featureform as ff
except ImportError:
    print("Error: featureform package not installed")
    print("Install with: pip install featureform")
    sys.exit(1)

# Set client host
client = ff.Client(
    host=os.getenv("FEATUREFORM_HOST"),
    insecure=os.getenv("FEATUREFORM_INSECURE", "false").lower() == "true"
)

print(f"✓ Connected to Featureform: {os.getenv('FEATUREFORM_HOST')}")

# Apply definitions
print("Applying feature definitions from featureform/definitions.py...")
exec(open("featureform/definitions.py").read())

print("✓ Feature definitions applied successfully!")
PYTHON_SCRIPT

else
    # Use Featureform CLI
    echo -e "${BLUE}Applying feature definitions via CLI...${NC}"
    featureform apply featureform/definitions.py
fi

echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo -e "${BLUE}Featureform Dashboard:${NC} https://$FEATUREFORM_HOST"
echo -e "${BLUE}Verify features:${NC} featureform get features"
