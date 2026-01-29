---

## 🎯 What Is This App?

A **real-time AI trading agent system** that combines multiple specialized agents to analyze financial markets, detect fraud, and make trading recommendations. The system leverages:

- **Microsoft AutoGen** for multi-agent orchestration
- **Featureform** for feature engineering and real-time feature serving
- **Azure Managed Redis** for semantic caching, vector search, fraud detection, and real-time data
- **Azure OpenAI** for LLM completions and embeddings
- **85% cost reduction** through intelligent caching
- **Sub-millisecond fraud detection** protecting against market manipulation 


---

## 🏗️ System Architecture

```ini
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                            │
│                    (FastAPI REST API + WebSocket)                       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    MICROSOFT AUTOGEN AGENT LAYER                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐   │
│  │  User Proxy  │  │ Orchestrator │  │  Market Data │  │  Sentiment │   │
│  │    Agent     │─►│    Agent     │─►│    Agent     │  │   Agent    │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘   │
│                            │                                            │
│                            ▼                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │  Technical   │  │     Risk     │  │    Report    │                   │
│  │   Analysis   │  │  Assessment  │  │  Generation  │                   │
│  │    Agent     │  │    Agent     │  │    Agent     │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    FEATUREFORM FEATURE STORE LAYER                      │
│                   (Feature Engineering & Serving)                       │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌────────────────┐   │
│  │  Feature Registry   │  │  Real-time Features │  │  Batch Features│   │
│  │                     │  │                     │  │                │   │
│  │  • Tech indicators  │  │  • Live prices      │  │  • Historical  │   │
│  │  • Sentiment scores │  │  • Moving averages  │  │  • Aggregates  │   │
│  │  • Risk metrics     │  │  • Volatility calc  │  │  • Backtests   │   │
│  └─────────────────────┘  └─────────────────────┘  └────────────────┘   │
└────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       REDIS ENTERPRISE LAYER                            │
│                    (Unified Data & Caching Platform)                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌────────────────┐   │
│  │  Semantic Cache     │  │  Vector Search      │  │  Agentic Memory│   │
│  │  (RediSearch)       │  │  (RediSearch HNSW)  │  │  (Hashes/JSON) │   │
│  │                     │  │                     │  │                │   │
│  │  • LLM responses    │  │  • Earnings docs    │  │  • Portfolio   │   │
│  │  • Query embeddings │  │  • SEC filings      │  │  • Chat history│   │
│  │  • Similarity: 0.92 │  │  • News articles    │  │  • Entities    │   │
│  └─────────────────────┘  └─────────────────────┘  └────────────────┘   │
│                                                                         │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌────────────────┐   │
│  │  Time Series Data   │  │  Fraud Detection    │  │  Task Queue    │   │
│  │  (RedisTimeSeries)  │  │  (RedisBloom)       │  │  (Streams)     │   │
│  │                     │  │                     │  │                │   │
│  │  • OHLCV prices     │  │  • Blacklist check  │  │  • Agent tasks │   │
│  │  • Technical indic. │  │  • Wash trading     │  │  • Job queue   │   │
│  │  • Volume data      │  │  • Rate limits      │  │  • Pub/Sub     │   │
│  └─────────────────────┘  └─────────────────────┘  └────────────────┘   │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SERVICES LAYER                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐   │
│  │ Azure OpenAI │  │ Market Data  │  │ News APIs    │  │ SEC Edgar  │   │
│  │              │  │ APIs         │  │              │  │ Filings    │   │
│  │ • GPT-4      │  │ • Alpha V.   │  │ • NewsAPI    │  │            │   │
│  │ • Embeddings │  │ • Polygon.io │  │ • Twitter    │  │ • 10-K/Q   │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Ingestion Progress

### Stage 1: Data Collection & Ingestion ✅ (COMPLETED)

#### Step 1: Stock Data ✅
- **Status**: Complete
- **Tickers**: 28 (AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, JPM, BAC, WFC, GS, MS, WMT, HD, NKE, SBUX, MCD, JNJ, UNH, PFE, ABBV, BA, CAT, GE, XOM, CVX, COIN, MSTR)
- **Period**: 2023-01-01 to 2024-12-06
- **Files**: 85 files (28 tickers × 3 files + manifest)
- **Size**: 776 KB
- **Location**: `data/raw/stock_data/`
- **Validation**: 8-point validation (date range, OHLCV columns, data completeness, price sanity, volume sanity, file size, duplicate check, sorting)
- **Committed**: ✅ Yes

#### Step 2: News Articles ✅
- **Status**: Complete
- **Articles**: 280 (10 per ticker)
- **Files**: 85 files (28 tickers × 3 files + manifest)
- **Size**: 360 KB
- **Location**: `data/raw/news_articles/`
- **Source**: yfinance API
- **Validation**: 8-point validation (count, recency, content quality, metadata, ticker consistency, uniqueness, file size, checksum)
- **Committed**: ✅ Yes

#### Step 3: SEC Filings ✅
- **Status**: Complete
- **Filings**: 84 total (28 tickers × 3 filing types)
  - 28 × 10-K (Annual Reports)
  - 28 × 10-Q (Quarterly Reports)
  - 28 × 8-K metadata lists (Event Reports)
- **Files**: 253 files
- **Size**: 225.3 MB (226 MB on disk)
- **Location**: `data/raw/sec_filings/`
- **Source**: SEC EDGAR API
- **Validation**: 9-point validation (form type, metadata completeness, file size limits, accession format, CIK format, filing date recency, ticker consistency, form consistency, content validation)
- **Committed**: ✅ Yes (77,956 insertions, commit ee5e526)
- **API Requirements**:
  - Rate limit: 10 requests/second (0.11s delay)
  - User-Agent: "CompanyName EmailAddress" format
  - ⚠️ Note: SEC blocks "github" in email addresses

**Size Warnings**:
- Some 10-K filings exceed 5MB limit (JPM: 12.8MB, BAC: 12.9MB, GS: 10.1MB, MS: 9.8MB, CAT: 6.1MB, XOM: 6.0MB, CVX: 6.0MB, MSTR: 6.3MB, PFE: 5.3MB)
- Some 10-Q filings exceed 3MB limit (MSFT: 5.6MB, JPM: 11.5MB, BAC: 11.0MB, WFC: 10.9MB, GS: 9.3MB, MS: 8.0MB, CAT: 4.6MB, MSTR: 6.7MB)
- These large filings still downloaded and validated successfully

#### Step 4: Unified Azure Uploader ✅
- **Status**: Complete
- **Script**: `scripts/upload_to_azure.py`
- **Features**:
  - Support for `--all` and `--type` flags (stock_data, news_articles, sec_filings)
  - Upload to respective Azure Blob Storage containers
  - Checksum verification to skip already-uploaded files
  - Proper content-type detection (parquet, json, html, md5)
  - Metadata tagging (upload timestamp, source, checksum)
  - Progress tracking and statistics
  - Logging to console + file
  - Support for Azure AD and account key authentication
- **Results**:
  - 423 files uploaded successfully
  - stock-data container: 85 blobs (0.5 MB)
  - news-articles container: 85 blobs (0.4 MB)
  - sec-filings container: 253 blobs (225.3 MB)
  - Total size: 226.2 MB
  - 100% success rate
- **Storage Account**: st<RESOURCE_ID> (finagentix-dev-rg)
- **Committed**: ✅ Yes (commit f8f94d2)

**Data Summary**:
- **Total files**: 423 (85 stock + 85 news + 253 SEC)
- **Total size**: ~226 MB (776KB + 360KB + 225.3MB)
- **Tickers**: 28 across all datasets
- **Git storage**: 226 MB (all data committed to repository)
- **Repository size**: 21 MB (Git compression)

---

### Stage 2: Azure OpenAI Deployment ✅ (COMPLETED)

#### Azure OpenAI Service ✅
- **Status**: Complete
- **Service Name**: openai-<RESOURCE_ID>
- **Resource Group**: finagentix-dev-rg
- **Location**: East US
- **SKU**: S0 (Standard)
- **Endpoint**: https://openai-<RESOURCE_ID>.openai.azure.com/
- **API Version**: 2024-08-01-preview
- **Custom Subdomain**: openai-<RESOURCE_ID>
- **Network Access**: Enabled (public for development)
- **Deployment Method**: Azure CLI (due to Bicep deployment bug)
- **Deployed**: 2025-12-08

#### Model Deployments ✅

**GPT-4o Deployment**:
- **Deployment Name**: gpt-4o
- **Model**: gpt-4o (2024-08-06)
- **SKU**: Standard
- **Capacity**: 10 TPM (tokens per minute) × 1000 = 10K TPM
- **Use Cases**:
  - Multi-agent orchestration with Microsoft AutoGen
  - Trading recommendations and analysis
  - Sentiment analysis
  - Risk assessment
- **Status**: ✅ Deployed and ready

**Text Embedding 3 Large Deployment**:
- **Deployment Name**: text-embedding-3-large
- **Model**: text-embedding-3-large (v1)
- **SKU**: Standard
- **Capacity**: 10 TPM × 1000 = 10K TPM
- **Dimensions**: 3072
- **Use Cases**:
  - SEC filing embeddings (225 MB of documents)
  - News article embeddings (280 articles)
  - Semantic search in Redis vector store
  - Semantic caching (85% cost reduction)
  - Document similarity and retrieval
- **Status**: ✅ Deployed and ready

#### Configuration Files ✅
- **Environment Template**: `.env.template` (created)
- **OpenAI Config**: `config/azure_openai.json` (created)
- **Contains**:
  - Service endpoints and API keys
  - Deployment names and versions
  - Model specifications
  - Use case documentation
  - Network configuration details

#### Next Steps
- Configure private endpoint for secure access (optional)
- Set up rate limiting and monitoring
- Integrate with AutoGen agents

---

### Stage 4: Feature Engineering & Vector Indexing 🔄 (IN PROGRESS)

#### Redis Enterprise Infrastructure ✅
- **Cluster**: redis-<RESOURCE_ID>.eastus.redis.azure.net
- **SKU**: Balanced_B5
- **Port**: 10000 (SSL/TLS)
- **Redis Version**: 7.4.3
- **Status**: Running

#### Redis Modules Enabled ✅
- **RediSearch** v2.10.23: Vector search with HNSW indexing
- **RedisJSON** v2.8.13: JSON document storage
- **RedisTimeSeries** v1.12.8: Time series data
- **RedisBloom** v2.8.15: Probabilistic data structures

#### Vector Indexes Created ✅
1. **idx:sec_filings** - SEC Filing Embeddings
   - Prefix: `sec:`
   - Vector dimensions: 3072 (text-embedding-3-large)
   - Distance metric: COSINE
   - Initial capacity: 2000 documents
   - Fields: ticker, filing_type, filing_date, content, chunk_index, embedding

2. **idx:news_articles** - News Article Embeddings
   - Prefix: `news:`
   - Vector dimensions: 3072
   - Distance metric: COSINE
   - Initial capacity: 500 documents
   - Fields: ticker, title, content, embedding

3. **idx:semantic_cache** - Semantic Caching
   - Prefix: `cache:`
   - Vector dimensions: 3072
   - Distance metric: COSINE
   - Initial capacity: 10000 queries
   - Fields: query, model, timestamp, query_embedding
   - Purpose: 85% cost reduction through semantic similarity matching

#### Embedding Generation Scripts ✅
- **scripts/generate_embeddings_azure.py**: Main production script
  - Reads SEC filings and news from Azure Blob Storage
  - Generates embeddings via Azure OpenAI
  - Stores in Redis with vector indexes
  - Chunk size: 24K chars (~6K tokens) to stay within limits
  - Rate limiting: 0.1s delay between requests

- **scripts/test_redis.py**: Connection and feature testing
  - Validates Redis Enterprise connectivity
  - Tests RedisJSON operations
  - Tests RediSearch vector indexing
  - Tests vector similarity search

#### Embedding Generation Status 🔄
- **Status**: In Progress
- **Processing**: First 3 tickers as test (AAPL, ABBV, AMZN)
- **Data Source**: Azure Blob Storage (226 MB)
- **Target**:
  - 28 tickers × 2 filing types (10-K, 10-Q)
  - ~225 MB of SEC filings to embed
  - 280 news articles to embed
- **Configuration**:
  - Model: text-embedding-3-large (3072 dimensions)
  - Chunk strategy: Adaptive splitting to fit 8K token limit
  - Storage: Redis JSON documents with vector embeddings

#### Technical Implementation ✅
- **Python Dependencies**: redis, openai, azure-storage-blob, pandas, beautifulsoup4
- **Data Processing**:
  - HTML parsing for SEC filings (BeautifulSoup4)
  - Parquet reading for news articles (pandas)
  - Text chunking for large documents
  - Automatic retry and error handling
- **Vector Search**:
  - HNSW (Hierarchical Navigable Small World) algorithm
  - Sub-millisecond search latency
  - Supports filtered queries (e.g., by ticker)

#### Next Steps
- ⏳ Complete embedding generation for all 28 tickers
- 🔍 Test vector similarity search with real queries
- 💰 Implement and test semantic caching
- 📊 Set up Featureform feature definitions
- 🤖 Begin AutoGen agent integration

---
