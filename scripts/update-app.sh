#!/bin/bash
# FinagentiX Update Script
# Usage: ./scripts/update-app.sh [frontend|api|all] [OPTIONS]
#
# This script updates the FinagentiX application on Azure:
# - frontend: Updates the React frontend
# - api: Updates the FastAPI backend
# - all: Updates both frontend and API

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${ROOT_DIR}/.env"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
TARGET="${1:-all}"
shift 2>/dev/null || true

# Parse remaining arguments
SKIP_BUILD=false
SKIP_RESTART=false
VERBOSE=false
SYNC_ENV=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-restart)
            SKIP_RESTART=true
            shift
            ;;
        --sync-env)
            SYNC_ENV=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [TARGET] [OPTIONS]"
            echo ""
            echo "Update FinagentiX applications on Azure Container Apps"
            echo ""
            echo "Targets:"
            echo "  frontend         Update frontend only"
            echo "  api              Update API only"
            echo "  all              Update both frontend and API (default)"
            echo ""
            echo "Options:"
            echo "  --skip-build     Skip building container images"
            echo "  --skip-restart   Skip restarting container apps"
            echo "  --sync-env       Sync .env with Azure resources first"
            echo "  --verbose, -v    Show detailed output"
            echo "  --help, -h       Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 frontend                  # Update frontend"
            echo "  $0 api --skip-restart        # Update API, skip restart"
            echo "  $0 all --sync-env            # Sync env and update all"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

print_header() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}           ${BLUE}🚀 FinagentiX Application Update${NC}                 ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_header

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ .env file not found at $ENV_FILE${NC}"
    echo "   Run ./infra/scripts/update-env.sh --all first"
    exit 1
fi

# Sync environment if requested or if key vars are missing
if [ "$SYNC_ENV" = true ]; then
    echo -e "${BLUE}🔄 Syncing .env with Azure resources...${NC}"
    "${ROOT_DIR}/infra/scripts/update-env.sh" --all
    echo ""
fi

# Load environment variables from .env
echo "📄 Loading configuration from .env..."
set -a
source "$ENV_FILE"
set +a

# Check if we need to sync (missing vars)
NEED_SYNC=false
for var in AZURE_CONTAINER_REGISTRY_NAME AZURE_FRONTEND_APP_NAME AZURE_API_APP_NAME; do
    if [ -z "${!var}" ]; then
        NEED_SYNC=true
        break
    fi
done

if [ "$NEED_SYNC" = true ] && [ "$SYNC_ENV" = false ]; then
    echo -e "${YELLOW}⚠️  Some Azure variables missing from .env${NC}"
    echo "   Running update-env.sh to fetch latest values..."
    "${ROOT_DIR}/infra/scripts/update-env.sh" --all
    
    # Reload
    set -a
    source "$ENV_FILE"
    set +a
fi

# Print configuration summary
echo ""
echo "📋 Configuration Summary:"
echo "   ┌─────────────────────────────────────────────────────────────┐"
echo "   │ Resource Group:     ${AZURE_RESOURCE_GROUP:-<not set>}"
echo "   │ Container Registry: ${AZURE_CONTAINER_REGISTRY_NAME:-<not set>}"
echo "   │ Frontend App:       ${AZURE_FRONTEND_APP_NAME:-<not set>}"
echo "   │ Frontend URL:       ${AZURE_FRONTEND_URL:-<not set>}"
echo "   │ API App:            ${AZURE_API_APP_NAME:-<not set>}"
echo "   │ API URL:            ${AZURE_API_URL:-<not set>}"
echo "   └─────────────────────────────────────────────────────────────┘"
echo ""

# Build arguments for sub-scripts
EXTRA_ARGS=""
[ "$SKIP_BUILD" = true ] && EXTRA_ARGS="$EXTRA_ARGS --skip-build"
[ "$SKIP_RESTART" = true ] && EXTRA_ARGS="$EXTRA_ARGS --skip-restart"
[ "$VERBOSE" = true ] && EXTRA_ARGS="$EXTRA_ARGS --verbose"

# Execute based on target
case "$TARGET" in
    frontend)
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}📦 Updating Frontend${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        "${SCRIPT_DIR}/update-frontend.sh" $EXTRA_ARGS
        ;;
    api)
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}🔧 Updating API${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        "${SCRIPT_DIR}/update-api.sh" $EXTRA_ARGS
        ;;
    all)
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}📦 Updating Frontend${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        "${SCRIPT_DIR}/update-frontend.sh" $EXTRA_ARGS
        
        echo ""
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}🔧 Updating API${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        "${SCRIPT_DIR}/update-api.sh" $EXTRA_ARGS
        ;;
    *)
        echo -e "${RED}❌ Unknown target: $TARGET${NC}"
        echo "   Valid targets: frontend, api, all"
        exit 1
        ;;
esac

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}              ${GREEN}✅ Update Complete!${NC}                          ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "🌐 URLs:"
[ -n "$AZURE_FRONTEND_URL" ] && echo "   Frontend: $AZURE_FRONTEND_URL"
[ -n "$AZURE_API_URL" ] && echo "   API:      $AZURE_API_URL"
echo ""
