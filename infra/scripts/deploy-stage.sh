#!/bin/bash

# FinagentiX Staged Deployment Script
# Usage: ./deploy-stage.sh [stage-name] [environment]
# Example: ./deploy-stage.sh foundation dev

set -e

STAGE=$1
ENVIRONMENT=${2:-dev}
LOCATION=${AZURE_LOCATION:-westus3}

if [ -z "$STAGE" ]; then
  echo "Usage: ./deploy-stage.sh [stage-name] [environment]"
  echo ""
  echo "Stages:"
  echo "  all              - Deploy all stages"
  echo "  foundation       - Stage 0: Networking and monitoring"
  echo "  data-platform    - Stage 1: Redis + Storage"
  echo "  ai-services      - Stage 2: Azure OpenAI"
  echo "  data-ingestion   - Stage 3: Data ingestion Container App"
  echo "  agent-runtime    - Stage 4: Agent API Container App"
  echo ""
  echo "Example: ./deploy-stage.sh foundation dev"
  exit 1
fi

echo "🚀 Deploying FinagentiX - Stage: $STAGE, Environment: $ENVIRONMENT"
echo ""

# Check if azd is installed
if ! command -v azd &> /dev/null; then
  echo "❌ Azure Developer CLI (azd) is not installed"
  echo "Install from: https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd"
  exit 1
fi

# Initialize azd if not already done
if [ ! -f ".azure/$ENVIRONMENT/.env" ]; then
  echo "📝 Initializing azd environment: $ENVIRONMENT"
  azd env new $ENVIRONMENT
  azd env set AZURE_LOCATION $LOCATION
fi

# Deploy based on stage
case $STAGE in
  all)
    echo "📦 Deploying all stages..."
    azd up --environment $ENVIRONMENT
    ;;
  foundation)
    echo "🌐 Deploying Stage 0: Foundation (Networking & Monitoring)..."
    az deployment sub create \
      --location $LOCATION \
      --template-file ./main.bicep \
      --parameters environmentName=$ENVIRONMENT deployStage=foundation
    ;;
  data-platform)
    echo "💾 Deploying Stage 1: Data Platform (Redis + Storage)..."
    REDIS_SKU=${REDIS_SKU:-Enterprise_E5}
    az deployment sub create \
      --location $LOCATION \
      --template-file ./main.bicep \
      --parameters environmentName=$ENVIRONMENT deployStage=data-platform redisSku=$REDIS_SKU
    ;;
  ai-services)
    echo "🤖 Deploying Stage 2: AI Services (Azure OpenAI)..."
    az deployment sub create \
      --location $LOCATION \
      --template-file ./main.bicep \
      --parameters environmentName=$ENVIRONMENT deployStage=ai-services
    ;;
  data-ingestion)
    echo "📥 Deploying Stage 3: Data Ingestion..."
    az deployment sub create \
      --location $LOCATION \
      --template-file ./main.bicep \
      --parameters environmentName=$ENVIRONMENT deployStage=data-ingestion
    ;;
  agent-runtime)
    echo "🎯 Deploying Stage 4: Agent Runtime..."
    az deployment sub create \
      --location $LOCATION \
      --template-file ./main.bicep \
      --parameters environmentName=$ENVIRONMENT deployStage=agent-runtime
    ;;
  *)
    echo "❌ Unknown stage: $STAGE"
    echo "Valid stages: all, foundation, data-platform, ai-services, data-ingestion, agent-runtime"
    exit 1
    ;;
esac

echo ""
echo "✅ Deployment complete!"
echo ""
echo "To view environment variables:"
echo "  azd env get-values --environment $ENVIRONMENT"
