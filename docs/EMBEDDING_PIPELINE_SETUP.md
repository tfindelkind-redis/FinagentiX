# Embedding Pipeline Setup Guide

> **Important:** Azure Managed Redis is deployed inside a VNet with private endpoints. You must run the embedding pipeline from the **Debug VM** to access Redis.

---

## 🔒 Network Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Azure VNet                              │
│                                                                 │
│  ┌─────────────────┐      ┌─────────────────────────────────┐  │
│  │   Debug VM      │      │  Azure Managed Redis Enterprise │  │
│  │  (Public IP)    │─────►│  (Private Endpoint Only)        │  │
│  │                 │      │  Port: 10000 (TLS)              │  │
│  └─────────────────┘      └─────────────────────────────────┘  │
│         ▲                                                       │
│         │ SSH                                                   │
└─────────│───────────────────────────────────────────────────────┘
          │
    ┌─────┴─────┐
    │ Your Mac  │  ← Cannot access Redis directly (not in VNet)
    └───────────┘
```

---

## 📋 Prerequisites

1. **Debug VM deployed** with public IP
2. **SSH access** to the Debug VM
3. **Azure credentials** for:
   - Azure Managed Redis (host, port, password)
   - Azure OpenAI (endpoint, API key, deployment names)
   - Azure Blob Storage (connection string)

---

## 🚀 Step-by-Step Setup

### Step 1: SSH into Debug VM

```bash
# Get Debug VM IP from Azure Portal or CLI
az vm show -g rg-finagentix-dev -n vm-debug-dev --show-details --query publicIps -o tsv

# SSH into the VM
ssh azureuser@<DEBUG_VM_PUBLIC_IP>
```

### Step 2: Clone Repository on Debug VM

```bash
# On Debug VM
cd ~
git clone https://github.com/tfindelkind-redis/FinagentiX.git
cd FinagentiX
```

### Step 3: Set Up Python Environment

```bash
# On Debug VM
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 4: Create .env File on Debug VM

```bash
# On Debug VM
cat > .env << 'EOF'
# =============================================================================
# Azure Managed Redis (Enterprise Tier - Inside VNet)
# =============================================================================
REDIS_HOST=<your-redis-name>.redis.cache.azure.com
REDIS_PORT=10000
REDIS_PASSWORD=<your-redis-access-key>
REDIS_SSL=true

# =============================================================================
# Azure OpenAI
# =============================================================================
AZURE_OPENAI_ENDPOINT=https://<your-openai>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-openai-api-key>
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Deployment names
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large

# =============================================================================
# Azure Blob Storage (for source data)
# =============================================================================
AZURE_STORAGE_CONNECTION_STRING=<your-storage-connection-string>
AZURE_STORAGE_CONTAINER=finagentix-data

# =============================================================================
# Feature Flags
# =============================================================================
ENABLE_SEMANTIC_CACHE=true
ENABLE_ROUTING_CACHE=true
ENABLE_TOOL_CACHE=true
EOF
```

### Step 5: Get Azure Credentials

```bash
# Get Redis access key
az redis list-keys \
  --resource-group rg-finagentix-dev \
  --name <your-redis-name> \
  --query primaryKey -o tsv

# Get Redis hostname
az redis show \
  --resource-group rg-finagentix-dev \
  --name <your-redis-name> \
  --query hostName -o tsv

# Get OpenAI key
az cognitiveservices account keys list \
  --resource-group rg-finagentix-dev \
  --name <your-openai-name> \
  --query key1 -o tsv

# Get Storage connection string
az storage account show-connection-string \
  --resource-group rg-finagentix-dev \
  --name <your-storage-name> \
  --query connectionString -o tsv
```

### Step 6: Test Redis Connectivity

```bash
# On Debug VM - test connection
python3 -c "
import redis
import os
from dotenv import load_dotenv

load_dotenv()

r = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=int(os.getenv('REDIS_PORT', 10000)),
    password=os.getenv('REDIS_PASSWORD'),
    ssl=os.getenv('REDIS_SSL', 'true').lower() == 'true',
    decode_responses=True
)

print('PING:', r.ping())
print('INFO server:', r.info('server')['redis_version'])
"
```

### Step 7: Run Embedding Pipeline

```bash
# On Debug VM
cd ~/FinagentiX
source .venv/bin/activate

# Test with a few documents first
python scripts/generate_embeddings_azure.py \
  --tickers AAPL MSFT \
  --limit 10 \
  --rate-limit 0.5

# Full run with resume capability
python scripts/generate_embeddings_azure.py --resume

# Refresh all embeddings
python scripts/generate_embeddings_azure.py --refresh
```

---

## 📊 Pipeline CLI Options

| Option | Description | Example |
|--------|-------------|---------|
| `--tickers` | Specific tickers to process | `--tickers AAPL MSFT GOOGL` |
| `--limit` | Max documents per ticker | `--limit 100` |
| `--resume` | Resume from last checkpoint | `--resume` |
| `--refresh` | Regenerate all embeddings | `--refresh` |
| `--skip-sec` | Skip SEC filings | `--skip-sec` |
| `--skip-news` | Skip news articles | `--skip-news` |
| `--rate-limit` | Seconds between API calls | `--rate-limit 0.5` |
| `--max-tokens` | Max tokens per chunk | `--max-tokens 8000` |

---

## 🔍 Verify Embeddings

```bash
# Check index info
python3 -c "
import redis
import os
from dotenv import load_dotenv

load_dotenv()

r = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=int(os.getenv('REDIS_PORT', 10000)),
    password=os.getenv('REDIS_PASSWORD'),
    ssl=True
)

# Check document index
try:
    info = r.ft('idx:documents').info()
    print(f'Documents indexed: {info[\"num_docs\"]}')
except:
    print('Document index not found')

# Check semantic cache index
try:
    info = r.ft('idx:semantic_cache').info()
    print(f'Cache entries: {info[\"num_docs\"]}')
except:
    print('Semantic cache index not found')
"
```

---

## ⚠️ Common Issues

### Issue: Connection Refused
```
Error: Connection refused to localhost:6379
```
**Solution:** Ensure `.env` has correct `REDIS_HOST` pointing to Azure Redis, not localhost.

### Issue: SSL Handshake Failed
```
Error: SSL handshake failed
```
**Solution:** Ensure `REDIS_PORT=10000` and `REDIS_SSL=true` for Azure Managed Redis Enterprise.

### Issue: Authentication Failed
```
Error: NOAUTH Authentication required
```
**Solution:** Check `REDIS_PASSWORD` in `.env` matches the access key from Azure Portal.

### Issue: Rate Limit Exceeded
```
Error: Rate limit exceeded (Azure OpenAI)
```
**Solution:** Use `--rate-limit 1.0` to add delay between API calls, or request quota increase.

---

## 📁 Data Source

The embedding pipeline reads from Azure Blob Storage:
- **Container:** `finagentix-data`
- **Structure:**
  ```
  finagentix-data/
  ├── stock_data/       # OHLCV price data
  ├── news/             # NewsAPI articles
  └── sec_filings/      # 10-K, 10-Q filings
  ```

**Current data:** ~423 files, ~226MB (28 tickers)

---

## 🔄 Alternative: SSH Tunnel (Local Development)

If you prefer running scripts locally with an SSH tunnel:

```bash
# From your Mac - create SSH tunnel
ssh -L 10000:<redis-private-ip>:10000 azureuser@<DEBUG_VM_PUBLIC_IP> -N

# In another terminal - update .env to use localhost
REDIS_HOST=localhost
REDIS_PORT=10000
REDIS_SSL=true

# Run pipeline locally through tunnel
python scripts/generate_embeddings_azure.py --tickers AAPL --limit 5
```

---

## ✅ Summary

| Step | Command | Where |
|------|---------|-------|
| 1. SSH to VM | `ssh azureuser@<VM_IP>` | Your Mac |
| 2. Clone repo | `git clone ...` | Debug VM |
| 3. Setup env | `python3 -m venv .venv` | Debug VM |
| 4. Create .env | `cat > .env << EOF ...` | Debug VM |
| 5. Test Redis | `python3 -c "import redis..."` | Debug VM |
| 6. Run pipeline | `python scripts/generate_embeddings_azure.py` | Debug VM |

**Key Point:** All scripts that access Azure Managed Redis must run from within the VNet (Debug VM) or through an SSH tunnel.
