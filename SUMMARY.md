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
- **Storage Account**: st545d8fdb508d4 (finagentix-dev-rg)
- **Committed**: ✅ Yes (commit f8f94d2)

**Data Summary**:
- **Total files**: 423 (85 stock + 85 news + 253 SEC)
- **Total size**: ~226 MB (776KB + 360KB + 225.3MB)
- **Tickers**: 28 across all datasets
- **Git storage**: 226 MB (all data committed to repository)
- **Repository size**: 21 MB (Git compression)

---
