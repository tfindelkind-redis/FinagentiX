#!/bin/bash

# FinagentiX Pre-Deployment Validator
# Validates that all prerequisites are met before deployment

set -e

echo "🔍 FinagentiX - Pre-Deployment Validation"
echo "=========================================="
echo ""

ERRORS=0

# Check Azure CLI
echo -n "✓ Checking Azure CLI... "
if command -v az &> /dev/null; then
  AZ_VERSION=$(az version -o tsv --query '"azure-cli"')
  echo "✅ Installed (v$AZ_VERSION)"
else
  echo "❌ Not installed"
  echo "  Install from: https://learn.microsoft.com/cli/azure/install-azure-cli"
  ERRORS=$((ERRORS + 1))
fi

# Check Azure Developer CLI
echo -n "✓ Checking Azure Developer CLI (azd)... "
if command -v azd &> /dev/null; then
  AZD_VERSION=$(azd version | head -n1)
  echo "✅ $AZD_VERSION"
else
  echo "❌ Not installed"
  echo "  Install from: https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd"
  ERRORS=$((ERRORS + 1))
fi

# Check Bicep CLI
echo -n "✓ Checking Bicep CLI... "
if command -v bicep &> /dev/null; then
  BICEP_VERSION=$(bicep --version | awk '{print $NF}')
  echo "✅ v$BICEP_VERSION"
elif az bicep version &> /dev/null; then
  BICEP_VERSION=$(az bicep version)
  echo "✅ $BICEP_VERSION (via Azure CLI)"
else
  echo "❌ Not installed"
  echo "  Install with: az bicep install"
  ERRORS=$((ERRORS + 1))
fi

# Check Azure login
echo -n "✓ Checking Azure login... "
if az account show &> /dev/null; then
  SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
  SUBSCRIPTION_ID=$(az account show --query id -o tsv)
  echo "✅ Logged in"
  echo "  Subscription: $SUBSCRIPTION_NAME"
  echo "  ID: $SUBSCRIPTION_ID"
else
  echo "❌ Not logged in"
  echo "  Run: az login"
  ERRORS=$((ERRORS + 1))
fi

# Check required environment variables
echo ""
echo "🔐 Environment Variables:"
if [ -z "$AZURE_LOCATION" ]; then
  echo "  ℹ️  AZURE_LOCATION not set (will default to 'eastus')"
else
  echo "  ✅ AZURE_LOCATION: $AZURE_LOCATION"
fi

# Check Bicep files
echo ""
echo "📁 Checking Bicep templates:"
FILES=(
  "main.bicep"
  "stages/stage0-foundation.bicep"
  "stages/stage1-data-platform.bicep"
  "stages/stage2-ai-services.bicep"
  "stages/stage3-data-ingestion.bicep"
  "stages/stage4-agent-runtime.bicep"
  "main.parameters.json"
)

for FILE in "${FILES[@]}"; do
  if [ -f "$FILE" ]; then
    echo "  ✅ $FILE"
  else
    echo "  ❌ $FILE (missing)"
    ERRORS=$((ERRORS + 1))
  fi
done

# Check azure.yaml
echo ""
echo -n "✓ Checking azure.yaml... "
if [ -f "../azure.yaml" ]; then
  echo "✅ Found"
else
  echo "❌ Not found"
  ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
  echo "✅ All checks passed! Ready to deploy."
  echo ""
  echo "Next steps:"
  echo "  1. Initialize environment: azd init"
  echo "  2. Deploy foundation: ./scripts/deploy-stage.sh foundation dev"
  echo "  3. Deploy data platform: ./scripts/deploy-stage.sh data-platform dev"
  echo "  4. Deploy remaining stages as needed"
  exit 0
else
  echo "❌ Found $ERRORS error(s). Please fix before deployment."
  exit 1
fi
