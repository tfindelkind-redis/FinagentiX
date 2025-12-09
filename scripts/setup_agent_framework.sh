#!/bin/bash
#
# Setup Microsoft Agent Framework for FinagentiX
# Phase 5.1: Infrastructure Setup
#

set -e

echo "============================================================"
echo "  FinagentiX - Agent Framework Setup"
echo "============================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Change to project root
cd "$(dirname "$0")/.."

echo "${BLUE}📦 Step 1: Installing Agent Framework packages...${NC}"
source venv/bin/activate
pip install -r requirements-agents.txt --quiet
echo "${GREEN}✅ Agent Framework packages installed${NC}"
echo ""

echo "${BLUE}📁 Step 2: Creating directory structure...${NC}"
mkdir -p src/agents
mkdir -p src/tools
mkdir -p src/workflows
mkdir -p src/api
mkdir -p tests
mkdir -p logs/agents

touch src/__init__.py
touch src/agents/__init__.py
touch src/tools/__init__.py
touch src/workflows/__init__.py
touch src/api/__init__.py
touch tests/__init__.py

echo "${GREEN}✅ Directory structure created${NC}"
echo ""

echo "${BLUE}🔧 Step 3: Verifying Azure OpenAI connection...${NC}"
python3 << 'PYEOF'
import os
from dotenv import load_dotenv
load_dotenv()

# Check required environment variables
required_vars = [
    'AZURE_OPENAI_ENDPOINT',
    'AZURE_OPENAI_KEY',
    'REDIS_HOST',
    'REDIS_PASSWORD'
]

missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    print(f"❌ Missing environment variables: {', '.join(missing)}")
    print("   Please set them in .env file")
    exit(1)
else:
    print("✅ All required environment variables are set")
    print(f"   Azure OpenAI: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    print(f"   Redis: {os.getenv('REDIS_HOST')}")
PYEOF
echo ""

echo "${BLUE}🧪 Step 4: Testing Agent Framework installation...${NC}"
python3 << 'PYEOF'
try:
    # Test imports
    from agent_framework import ChatAgent
    from agent_framework.azure import AzureOpenAIChatClient
    from azure.identity import DefaultAzureCredential
    print("✅ Agent Framework imports successful")
    
    # Test basic setup
    import asyncio
    async def test():
        # This doesn't actually call the API, just tests setup
        print("✅ Async setup working")
    
    asyncio.run(test())
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
PYEOF
echo ""

echo "${GREEN}============================================================${NC}"
echo "${GREEN}✅ Agent Framework setup complete!${NC}"
echo "${GREEN}============================================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Review the agent structure in src/agents/"
echo "  2. Run: python src/agents/config.py (to verify config)"
echo "  3. Continue to Phase 5.2: Create Core Agent Definitions"
echo ""
