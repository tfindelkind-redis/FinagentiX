#!/bin/bash
# Full Update Script - Updates API, Frontend, and Embeddings
# Usage: ./scripts/full-update.sh [--skip-embeddings] [--skip-api] [--skip-frontend]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
SKIP_EMBEDDINGS=false
SKIP_API=false
SKIP_FRONTEND=false
EMBEDDING_ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-embeddings)
            SKIP_EMBEDDINGS=true
            shift
            ;;
        --skip-api)
            SKIP_API=true
            shift
            ;;
        --skip-frontend)
            SKIP_FRONTEND=true
            shift
            ;;
        --refresh-embeddings)
            EMBEDDING_ARGS="--refresh"
            shift
            ;;
        --news-only)
            EMBEDDING_ARGS="$EMBEDDING_ARGS --skip-sec"
            shift
            ;;
        --sec-only)
            EMBEDDING_ARGS="$EMBEDDING_ARGS --skip-news"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Full update script for FinagentiX"
            echo ""
            echo "Options:"
            echo "  --skip-embeddings    Skip embedding generation"
            echo "  --skip-api           Skip API update"
            echo "  --skip-frontend      Skip frontend update"
            echo "  --refresh-embeddings Delete and regenerate all embeddings"
            echo "  --news-only          Only process news articles"
            echo "  --sec-only           Only process SEC filings"
            echo "  --help, -h           Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=========================================="
echo -e "${BLUE}🚀 FinagentiX Full Update${NC}"
echo "=========================================="
echo ""

# Load environment
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Step 1: Update API (fast mode)
if [ "$SKIP_API" = false ]; then
    echo -e "${BLUE}Step 1/3: Updating API (fast mode)...${NC}"
    "$SCRIPT_DIR/update-api-fast.sh" || {
        echo -e "${YELLOW}⚠️  Fast API update failed, trying standard update...${NC}"
        "$SCRIPT_DIR/update-api.sh" || {
            echo -e "${YELLOW}⚠️  API update failed, continuing...${NC}"
        }
    }
    echo ""
else
    echo -e "${YELLOW}Step 1/3: Skipping API update${NC}"
fi

# Step 2: Update Frontend
if [ "$SKIP_FRONTEND" = false ]; then
    echo -e "${BLUE}Step 2/3: Updating Frontend...${NC}"
    "$SCRIPT_DIR/quick-frontend-update.sh" || {
        echo -e "${YELLOW}⚠️  Frontend update failed, continuing...${NC}"
    }
    echo ""
else
    echo -e "${YELLOW}Step 2/3: Skipping Frontend update${NC}"
fi

# Step 3: Generate Embeddings (on Debug VM)
if [ "$SKIP_EMBEDDINGS" = false ]; then
    echo -e "${BLUE}Step 3/3: Generating Embeddings (on Debug VM)...${NC}"
    echo "   Running embeddings on VM (VNet access, no public endpoint needed)..."
    
    # Use VM-based embedding generation
    "$SCRIPT_DIR/run-embeddings-on-vm.sh" $EMBEDDING_ARGS || {
        echo -e "${YELLOW}⚠️  VM embedding generation failed, trying locally...${NC}"
        
        # Fallback to local execution
        if [ ! -d "$PROJECT_ROOT/venv" ]; then
            echo "   Creating virtual environment..."
            python3 -m venv "$PROJECT_ROOT/venv"
            source "$PROJECT_ROOT/venv/bin/activate"
            pip install -q -r "$PROJECT_ROOT/requirements.txt"
        else
            source "$PROJECT_ROOT/venv/bin/activate"
        fi
        
        python "$PROJECT_ROOT/scripts/generate_embeddings_azure.py" --resume $EMBEDDING_ARGS || {
            echo -e "${YELLOW}⚠️  Local embedding generation also failed${NC}"
            echo "   This may require enabling public access on Azure OpenAI temporarily."
        }
    }
    echo ""
else
    echo -e "${YELLOW}Step 3/3: Skipping Embedding generation${NC}"
fi

# Summary
echo "=========================================="
echo -e "${GREEN}✅ Full Update Complete!${NC}"
echo "=========================================="
echo ""
echo "🌐 Frontend: ${AZURE_FRONTEND_URL:-https://ca-frontend-xxx.azurecontainerapps.io}"
echo "🔌 API: ${AZURE_API_URL:-https://ca-agent-api-xxx.azurecontainerapps.io}"
echo ""
echo "To monitor embeddings: tail -f /tmp/embeddings.log"
