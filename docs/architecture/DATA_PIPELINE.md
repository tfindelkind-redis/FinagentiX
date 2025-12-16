# Data Pipeline Architecture for FinagentiX

## 🎯 Overview

This document describes the data pipeline architecture for FinagentiX, focusing on **one-time data ingestion** to populate the system with historical data. The pipeline gathers data from multiple sources, processes it, and stores it in Redis and Featureform for use by the AI agents.

### Scope
- **Primary Focus:** One-time historical data load (batch ingestion)
- **Secondary Discussion:** Continuous refresh patterns (for future phases)
- **Free Tier Constraints:** All data sources use free tiers/APIs to avoid costs

---

## 📋 Free Tier Data Sources & Limits

### Market Data
- **Source:** yfinance (Yahoo Finance Python library)
- **Cost:** Free, no API key required
- **Limits:** No hard rate limits, reasonable request spacing recommended
- **Data:** 1 year of daily OHLCV for 20-30 tickers (~5MB)

### News
- **Source:** NewsAPI (free tier)
- **Cost:** Free with API key
- **Limits:** 100 requests/day, 30 days historical max
- **Data:** 200-500 articles for 10 tickers (spread over 2-3 days)

### SEC Filings
- **Source:** SEC EDGAR
- **Cost:** Free, no API key required
- **Limits:** 10 requests/second
- **Data:** 5-10 recent 10-K filings (~5-10MB)

### Earnings Transcripts
- **Status:** SKIPPED in initial implementation
- **Reason:** Most sources (Seeking Alpha, etc.) require paid subscriptions
- **Alternative:** Use SEC filing MD&A sections for qualitative analysis

---

## 📊 One-Time Data Ingestion Architecture

### Phase 1: Initial Data Load (Primary Implementation)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL DATA SOURCES                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ Market Data  │  │ News Archives│  │   SEC/EDGAR  │  │  Earnings  │  │
│  │  Historical  │  │              │  │   Filings    │  │ Transcripts│  │
│  │              │  │              │  │              │  │            │  │
│  │ • Alpha Vant.│  │ • NewsAPI    │  │ • 10-K       │  │ • Seeking  │  │
│  │ • yfinance   │  │ • Archived   │  │ • 10-Q       │  │   Alpha    │  │
│  │ • Yahoo Fin. │  │   articles   │  │ • 8-K        │  │ • Archives │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │
│         │                 │                 │                │         │
└─────────┼─────────────────┼─────────────────┼────────────────┼─────────┘
          │                 │                 │                │
          ▼                 ▼                 ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                                 │
│                      (One-Time Batch Load)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │  1. HISTORICAL MARKET DATA INGESTION                       │         │
│  │                                                            │         │
│  │  Data Type: OHLCV bars (Open, High, Low, Close, Volume)   │         │
│  │  Time Range: 1 year historical data                       │         │
│  │  Granularity: Daily bars only                             │         │
│  │  Tickers: 20-30 stocks (major tech & finance stocks)      │         │
│  │  Sources:                                                  │         │
│  │    • yfinance Python library (free, no API key needed)    │         │
│  │  Estimated Volume: ~5MB for 30 tickers, 1 year           │         │
│  │  Rate Limits: No hard limits, reasonable request spacing  │         │
│  │  Output: → Redis Streams → RedisTimeSeries                │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │  2. NEWS ARTICLES INGESTION                                │         │
│  │                                                            │         │
│  │  Data Type: Historical news articles                       │         │
│  │  Time Range: Last 30 days (NewsAPI free tier limit)      │         │
│  │  Tickers: Top 10 stocks only (to stay within limits)     │         │
│  │  Sources:                                                  │         │
│  │    • NewsAPI (free tier: 100 requests/day, 1 month max)   │         │
│  │    • RSS feeds (free, no limits)                          │         │
│  │  Estimated Volume: 200-500 articles                       │         │
│  │  Rate Limits: 100 requests/day, spread over 2-3 days     │         │
│  │  Output: → Redis Streams → Processing                     │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │  3. SEC FILINGS INGESTION                                  │         │
│  │                                                            │         │
│  │  Data Type: SEC filings (10-K only for simplicity)        │         │
│  │  Time Range: Last 1 year (most recent annual report)     │         │
│  │  Companies: 5-10 major companies only                     │         │
│  │  Source: SEC EDGAR (free, no API key needed)             │         │
│  │  Estimated Volume: 5-10 filings                           │         │
│  │  File Types: HTML/XML parsed to text                      │         │
│  │  Rate Limits: 10 requests/second (easily respected)       │         │
│  │  Output: → Azure Blob Storage → Redis Streams             │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │  4. EARNINGS TRANSCRIPTS INGESTION (OPTIONAL - SKIP)      │         │
│  │                                                            │         │
│  │  Status: SKIPPED in initial implementation                │         │
│  │  Reason: Most sources require paid subscriptions          │         │
│  │  Alternative: Use SEC filings MD&A section for analysis   │         │
│  │                                                            │         │
│  │  If implemented later:                                     │         │
│  │    • Limit to 3-5 companies only                          │         │
│  │    • Use free publicly available archives                 │         │
│  │    • Estimated: 10-20 transcripts max                     │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    DATA PROCESSING LAYER                                │
│                      (Batch Processing)                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │  PROCESS 1: Market Data Validation & Storage               │         │
│  │                                                            │         │
│  │  Input: Raw OHLCV data from APIs                          │         │
│  │  Processing Steps:                                         │         │
│  │    1. Validate data quality (check for gaps, anomalies)   │         │
│  │    2. Calculate derived metrics (daily returns, volatility│         │
│  │    3. Normalize data formats                              │         │
│  │    4. Store in RedisTimeSeries                            │         │
│  │  Output: Time-series data ready for feature engineering   │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │  PROCESS 2: News Text Processing & Sentiment               │         │
│  │                                                            │         │
│  │  Input: Raw news articles                                  │         │
│  │  Processing Steps:                                         │         │
│  │    1. Clean text (remove ads, HTML, formatting)           │         │
│  │    2. Extract entities (ticker mentions, company names)   │         │
│  │    3. Generate sentiment scores (Azure OpenAI)            │         │
│  │    4. Store metadata in Redis Hashes                      │         │
│  │    5. Aggregate sentiment by ticker                       │         │
│  │  Output: Processed news with sentiment scores             │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │  PROCESS 3: Document Chunking & Embedding (RAG Prep)       │         │
│  │                                                            │         │
│  │  Input: SEC filings and earnings transcripts              │         │
│  │  Processing Steps:                                         │         │
│  │    1. Parse documents (extract text from HTML/PDF)        │         │
│  │    2. Chunk into ~500 token segments                      │         │
│  │    3. Generate embeddings (text-embedding-3-large)        │         │
│  │    4. Store embeddings in RediSearch HNSW index           │         │
│  │    5. Index metadata (ticker, date, document type)        │         │
│  │  Output: Searchable document chunks for RAG               │         │
│  │  Estimated Time: 2-4 hours for 1,000 documents            │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │  PROCESS 4: Feature Engineering                            │         │
│  │                                                            │         │
│  │  Input: Processed market data and sentiment scores         │         │
│  │  Processing Steps:                                         │         │
│  │    1. Compute technical indicators (RSI, MACD, Bollinger) │         │
│  │    2. Calculate moving averages (SMA, EMA)                │         │
│  │    3. Compute volatility metrics                          │         │
│  │    4. Aggregate sentiment features                        │         │
│  │    5. Store features in Featureform (Redis-backed)        │         │
│  │  Output: ML features ready for agent consumption          │         │
│  └────────────────────────────────────────────────────────────┘         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    DATA STORAGE LAYER                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────┐  ┌─────────────────────┐  ┌────────────────┐ │
│  │  RedisTimeSeries     │  │  RediSearch HNSW    │  │  Redis Hashes  │ │
│  │                      │  │                     │  │                │ │
│  │  • OHLCV bars        │  │  • Document vectors │  │  • News items  │ │
│  │  • Tick data         │  │  • Embeddings       │  │  • Metadata    │ │
│  │  • Volume            │  │  • 10-K chunks      │  │  • Raw data    │ │
│  │  • Technical indic.  │  │  • News chunks      │  │                │ │
│  └──────────────────────┘  └─────────────────────┘  └────────────────┘ │
│                                                                         │
│  ┌──────────────────────┐  ┌─────────────────────┐  ┌────────────────┐ │
│  │  Featureform         │  │  Azure Blob Storage │  │  Redis Hashes  │ │
│  │  (Redis Online)      │  │  (Archive Storage)  │  │  (Metadata)    │ │
│  │                      │  │                     │  │                │ │
│  │  • ML features       │  │  • Raw filings      │  │  • Job status  │ │
│  │  • Real-time serving │  │  • Historical docs  │  │  • Checkpoints │ │
│  │  • Feature registry  │  │  • Backups          │  │  • DLQ items   │ │
│  └──────────────────────┘  └─────────────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Ingestion Execution Strategy

### One-Time Batch Load (Primary Implementation)

The initial data load will be executed as a **single batch operation** that runs once to populate the system with historical data.

**Execution Approach:**
1. **Sequential Ingestion:** Process data sources one at a time to avoid API rate limits
2. **Parallel Processing:** Use multiple workers for processing (embeddings, sentiment analysis)
3. **Checkpoint System:** Track progress to allow resume if interrupted
4. **Estimated Duration:** 1-2 hours + 2-3 days for news (due to rate limits)

**Execution Order:**
1. **Market Data** (15-30 minutes)
   - Fetch 1 year of daily OHLCV for 20-30 tickers via yfinance
   - Store directly in RedisTimeSeries
   - ~30 API calls with reasonable spacing
   - yfinance is free, no API key needed

2. **News Articles** (2-3 days, spread out)
   - Fetch 30 days of news for 10 tickers
   - ~200-500 articles
   - NewsAPI free tier: 100 requests/day limit
   - Spread over 2-3 days to respect rate limits
   - Process sentiment in batches

3. **SEC Filings** (20-30 minutes)
   - Download 5-10 filings (10-K only)
   - Parse and store raw text in Azure Blob
   - Generate embeddings (small volume, fast)
   - Index in RediSearch
   - SEC EDGAR is free, 10 req/sec limit

4. **Earnings Transcripts** (SKIPPED)
   - Skipped to avoid paid subscription requirements
   - Alternative: Use SEC filing MD&A sections

5. **Feature Engineering** (10-20 minutes)
   - Compute technical indicators from market data
   - Aggregate sentiment scores (limited dataset)
   - Store in Featureform (Redis-backed)

---

## 📊 Data Storage Strategy

### Redis (Hot Storage)
> **Note:** Using **Azure Managed Redis** (NOT Azure Cache for Redis). Azure Managed Redis Enterprise tier SKUs (E5, E10, etc.) include RediSearch HNSW vectors, RedisTimeSeries, RedisJSON, and RedisBloom modules.

**Retention:** 1 year for historical data after initial load

| Data Type | Redis Structure | Size Estimate |
|-----------|----------------|---------------|
| Historical OHLCV (1 year) | RedisTimeSeries | ~5MB for 30 tickers (daily bars) |
| News articles (30 days) | Redis Hashes | ~10-20MB (500 articles) |
| Document embeddings (filings) | RediSearch HNSW vectors | ~50-100MB (10 documents) |
| Features | Redis Hashes (Featureform) | ~5-10MB |
| User context | RedisJSON | ~5MB (grows over time) |

**Total Initial Storage:** ~100-150MB (easily fits in free Redis tiers or smallest Azure Redis)

### Azure Blob Storage (Warm Storage)
**Purpose:** Archive storage for raw documents

- Full SEC filings (raw HTML/XML) - ~5-10MB (10 filings)
- Enables re-processing without re-fetching from sources
- Minimal cost (~$0.01/month or less)

### Azure Archive Storage (Cold Storage)
**Purpose:** Long-term compliance storage (optional, future phase)

- 7+ years of historical data
- Audit logs
- Regulatory compliance backups

---

## 🔄 Data Processing Workflows

### Workflow 1: Historical Market Data
```
Alpha Vantage / yfinance API
    ↓
Fetch 2-3 years of daily OHLCV
    ↓
Validate & normalize data
    ↓
Store in RedisTimeSeries
    ↓
Trigger feature computation
    ↓
Store features in Featureform (Redis Hashes)
```

### Workflow 2: News Articles → Sentiment
```
NewsAPI historical endpoint
    ↓
Fetch 90 days of news articles
    ↓
Clean text & extract entities
    ↓
Store metadata in Redis Hashes
    ↓
Sentiment analysis (Azure OpenAI)
    ↓
Aggregate sentiment by ticker
    ↓
Store as features in Featureform
```

### Workflow 3: SEC Filings → RAG
```
SEC EDGAR bulk download
    ↓
Parse HTML/XML to text
    ↓
Store raw in Azure Blob (archive)
    ↓
Chunk into ~500 token segments
    ↓
Generate embeddings (text-embedding-3-large)
    ↓
Index in RediSearch HNSW
    ↓
Ready for RAG retrieval by agents
```

---

## 🔌 Data Access Architecture for Agents

After the batch ingestion completes, the data needs to be accessible to the AI agents and services. Here's how the data access layer works:

### Data Access Patterns

**1. Feature Serving via Featureform**
```
Agent Request: "Get features for AAPL"
    ↓
Featureform Client Query
    ↓
Redis Hash Lookup: features:AAPL
    ↓
Return: {
  ticker: "AAPL",
  price_sma_20: 182.45,
  rsi_14: 58.3,
  sentiment_score: 0.65,
  volatility_30d: 0.23
}
```

**Use Case:** Technical Analysis Agent, Risk Assessment Agent

---

**2. Time-Series Data via RedisTimeSeries**
```
Agent Request: "Get last 30 days of AAPL prices"
    ↓
RedisTimeSeries Query: TS.RANGE ts:AAPL:close
    ↓
Return: Array of (timestamp, price) tuples
    ↓
Agent performs analysis (trend detection, pattern matching)
```

**Use Case:** Market Data Agent, Technical Analysis Agent

---

**3. Document Retrieval via RAG (RediSearch)**
```
Agent Query: "What did Apple's CEO say about AI investments?"
    ↓
Generate query embedding (Azure OpenAI)
    ↓
RediSearch Vector Similarity Search:
  FT.SEARCH idx:documents "@embedding:[VECTOR ...]"
    ↓
Return: Top 5 most relevant document chunks
    ↓
Agent uses chunks as context for response generation
```

**Use Case:** News & Research Agent

---

**4. Cached LLM Responses via Semantic Cache**
```
Agent generates LLM prompt
    ↓
Check semantic cache (RediSearch vector similarity)
    ↓
If similar query exists (similarity > 0.95):
  → Return cached response (sub-millisecond)
    ↓
Else:
  → Call Azure OpenAI
  → Cache response with embedding
  → Return new response
```

**Use Case:** All agents (30-70% cost savings)

---

**5. Contextual Memory via Redis Hashes**
```
User Session: user_123
    ↓
Load context: context:user_123
    ↓
Return: {
  previous_queries: ["AAPL analysis", "MSFT comparison"],
  portfolio: ["AAPL", "MSFT", "GOOGL"],
  risk_tolerance: "moderate",
  investment_horizon: "long-term"
}
    ↓
Agent uses context for personalized recommendations
```

**Use Case:** Orchestrator Agent, Portfolio Management Agent

---

### Data Access Service Architecture

**Recommended Pattern: Feature Store + Direct Redis Access**

```
┌─────────────────────────────────────────────────┐
│                AI Agents Layer                  │
│  (Orchestrator, Market Data, Technical, etc.)   │
└──────────────┬──────────────────┬───────────────┘
               │                  │
               │                  │
        ┌──────▼──────┐    ┌─────▼──────────┐
        │ Featureform │    │ Redis Client   │
        │   Client    │    │ (Direct Access)│
        └──────┬──────┘    └─────┬──────────┘
               │                  │
               └────────┬─────────┘
                        │
                 ┌──────▼──────────┐
                 │  Azure Managed  │
                 │ Redis Enterprise│
                 │   (E10 Tier)    │
                 └─────────────────┘
```

---

### Data Access Methods

**Option 1: Featureform SDK (Recommended for Features)**
- **Purpose:** Structured access to computed features
- **Benefits:** Type-safe, versioned, point-in-time consistency
- **Use Case:** When agents need real-time features (RSI, SMA, sentiment)

**Agents use Featureform client:**
```
featureform.get_online_features(
  features=["AAPL.price_sma_20", "AAPL.rsi_14"],
  entities={"ticker": "AAPL"}
)
```

**Option 2: Direct Redis Client (For Everything Else)**
- **Purpose:** Time-series queries, RAG retrieval, caching, context
- **Benefits:** Maximum flexibility, low latency, full Redis capabilities
- **Use Case:** When agents need raw time-series, document search, or custom queries

**Agents use Redis client directly:**
```
Redis commands via redis-py or redis-om:
- TS.RANGE for time-series
- FT.SEARCH for vector similarity
- HGET/HGETALL for features/context
- JSON.GET for complex objects
```

---

### Service Layer Design

**Approach 1: Agents with Embedded Data Access (Simpler)**
```
Each agent has:
  - Featureform client instance
  - Redis client instance
  - Direct access to data layer
  
Pros: Low latency, simple architecture
Cons: Each agent manages connections
```

**Approach 2: Dedicated Data Service API (More Scalable)**
```
┌──────────────┐
│  AI Agents   │
└──────┬───────┘
       │
       │ REST/gRPC calls
       │
┌──────▼────────────────┐
│  Data Access Service  │
│  - /features/{ticker} │
│  - /timeseries/{...}  │
│  - /rag/search        │
│  - /cache/lookup      │
└──────┬────────────────┘
       │
┌──────▼────────┐
│ Redis + Feat. │
└───────────────┘

Pros: Centralized access control, easier monitoring
Cons: Extra network hop, more complexity
```

**Recommendation for Phase 1:** Start with **Approach 1** (embedded access) for simplicity. Consider **Approach 2** if you need:
- Fine-grained access control
- Centralized rate limiting
- Multiple client languages
- Unified data access logs

---

### Example Agent Data Access Flow

**Scenario: User asks "Should I buy AAPL?"**

1. **Orchestrator Agent** receives query
   - Loads user context: `HGET context:user_123`
   - Routes to specialized agents

2. **Market Data Agent** fetches prices
   - Query: `TS.RANGE ts:AAPL:close (now-30d) now`
   - Returns 30 days of closing prices

3. **Technical Analysis Agent** gets features
   - Featureform query: `get_online_features(["AAPL.rsi_14", "AAPL.macd"])`
   - Returns computed indicators

4. **Sentiment Agent** performs RAG
   - Embeds query: "Recent Apple news sentiment"
   - RediSearch: `FT.SEARCH idx:news @ticker:AAPL @embedding:[VECTOR ...]`
   - Retrieves recent news with sentiment scores

5. **Risk Assessment Agent** checks risk metrics
   - Featureform: `get_online_features(["AAPL.volatility_30d"])`
   - Compares to user risk tolerance from context

6. **Orchestrator** aggregates results
   - Combines insights from all agents
   - Checks semantic cache (avoid duplicate LLM calls)
   - Generates final recommendation
   - Caches response for future similar queries

---

### Data Freshness & Staleness

**With One-Time Batch Load:**
- **Time-Series Data:** Static historical data (no staleness concern)
- **News Articles:** 90 days snapshot (becomes stale over time)
- **SEC Filings:** Historical filings (static, compliance-focused)
- **Features:** Computed from historical data (recalculate if needed)

**When to Refresh:**
- **Never (Phase 1):** Demo/POC with historical data is sufficient
- **Monthly:** If used for long-term analysis training
- **Daily/Hourly:** When continuous refresh is implemented (Phase 2+)

**Staleness Indicators:**
- Store ingestion timestamp: `SET metadata:last_refresh "2025-12-05T10:00:00Z"`
- Agents can check and warn users: "Data is 30 days old"

---

## 💡 Continuous Refresh Pattern (Future Phase - Not Implemented Initially)

While the initial implementation focuses on **one-time data load**, here's how continuous data refresh would work in future phases:

### Real-Time Market Data Streaming
**Pattern:** WebSocket connection to market data provider

```
Polygon.io / Alpha Vantage WebSocket
    ↓
Continuous stream of tick data & trades
    ↓
Buffer in Redis Streams
    ↓
Consumer workers process & validate
    ↓
Write to RedisTimeSeries
    ↓
Trigger real-time feature updates
```

**Implementation Considerations:**
- Requires persistent WebSocket connection (24/7)
- High throughput: 10K+ events/second during market hours
- Need failover & reconnection logic
- Cost: ~$50-200/month for real-time data feeds

---

### Scheduled Batch Refresh
**Pattern:** Cron-based periodic fetching

**Market Data Updates (Every 1-5 minutes):**
```
Scheduler triggers at fixed intervals
    ↓
Fetch latest OHLCV bars from REST API
    ↓
Append to existing RedisTimeSeries
    ↓
Update features incrementally
```

**News Updates (Every 5-10 minutes):**
```
Scheduler triggers news fetch
    ↓
Query NewsAPI for articles since last fetch
    ↓
Process new articles only
    ↓
Update sentiment scores
    ↓
Append to Redis storage
```

**SEC Filings Updates (Hourly or Daily):**
```
Scheduler checks for new filings
    ↓
Query SEC EDGAR API for recent submissions
    ↓
Download only new filings
    ↓
Process and index incrementally
```

---

### Change Data Capture (CDC) Pattern
**For incremental updates to Redis:**

```
New data arrives → Detect change → Update only affected records
    ↓
Example: New earnings report
    ↓
Index only new document chunks (not entire corpus)
    ↓
Update only affected ticker features
```

**Benefits:**
- Efficient: Only process new/changed data
- Low latency: Near real-time updates
- Cost-effective: Minimize redundant API calls

**Implementation Considerations:**
- Track last update timestamps in Redis
- Implement idempotency (avoid duplicate processing)
- Handle out-of-order data
- Requires stateful tracking in Redis Hashes or Sorted Sets

---

### Why Not Implement Continuous Refresh Initially?

**Reasons to start with batch load:**

1. **Simplicity:** One-time load is straightforward - run once and done
2. **Cost:** Real-time data feeds and continuous processing add ongoing costs
3. **Development Time:** Continuous systems require more error handling, monitoring, failover
4. **Sufficient for Demo/POC:** Historical data is enough to demonstrate agent capabilities
5. **Focus:** Allows focus on agent intelligence and Redis integration patterns

**When to Add Continuous Refresh:**
- **Phase 2-3:** After core agent functionality is proven
- **Production Deployment:** When serving real traders who need live data
- **Revenue:** When product generates revenue to justify ongoing data costs

---

## 🛠️ Checkpoint & Resume System

The batch ingestion process includes checkpoint capability to handle interruptions:

**Checkpoint Strategy:**
1. **Track Progress in Redis Hashes:**
   - `checkpoint:market_data` → Last processed ticker + date
   - `checkpoint:news` → Last processed article timestamp  
   - `checkpoint:sec_filings` → Last processed CIK + accession
   - **Storage:** Redis Hashes for structured checkpoint data
   - **Persistence:** Redis AOF/RDB ensures checkpoints survive restarts

2. **Resume Logic:**
   - On restart, check for existing checkpoints
   - Skip already-processed items
   - Continue from last known position

3. **Benefits:**
   - Resilient to network failures or API timeouts
   - Can pause and resume multi-hour ingestion
   - Avoid re-processing expensive operations (embeddings)

**Example Checkpoint Structure:**
```
checkpoint:market_data_fetch
  ticker: "MSFT"
  date: "2023-12-01"
  status: "in_progress"
  total_tickers: 200
  processed_tickers: 105
  
checkpoint:document_embedding
  doc_id: "10-K_AAPL_2023"
  chunk: 45
  total_chunks: 120
  status: "in_progress"
```

---

## 📈 Monitoring & Progress Tracking

### Metrics to Track During Batch Load

| Metric | Purpose | Alert Threshold |
|--------|---------|----------------|
| API call success rate | Detect API issues | <95% success |
| Processing throughput | Ensure steady progress | <100 docs/hour |
| Redis memory usage | Prevent OOM | >80% capacity |
| Error count | Catch systematic issues | >10 errors/minute |
| Embedding generation rate | Monitor bottleneck | <50 embeddings/min |

### Progress Dashboard
- **Total items:** 200 tickers, 10K news, 1K filings
- **Processed:** Updated in real-time
- **Estimated time remaining:** Based on current rate
- **Errors:** Count and list recent failures

---

## 🔒 Error Handling Strategy

### Retry with Exponential Backoff
- **Transient Failures:** Network timeouts, rate limits
- **Pattern:** Wait increasing intervals (1s, 2s, 4s, 8s, 16s)
- **Max Retries:** 3 attempts before moving to DLQ

### Dead Letter Queue (DLQ)
- **Failed Items:** Items that fail after all retries
- **Storage:** Redis List (`dlq:failed_items`) with item metadata as JSON
- **Manual Review:** Inspect using `LRANGE dlq:failed_items 0 -1` and re-process after fixing issues
- **Retention:** Keep failed items for 30 days for debugging

### Graceful Degradation
- **Partial Success:** If 1 ticker fails, continue with others
- **Skip & Log:** Record failures but don't halt entire pipeline
- **Post-Process:** Re-run failed items after main load completes

---

## 📋 Pre-Ingestion Checklist

Before running the batch load:

- [ ] **Azure Managed Redis deployed** (E10 tier minimum)
- [ ] **Redis modules enabled** (RedisTimeSeries, RediSearch, RedisJSON)
- [ ] **Azure Blob Storage container created** (for document archives)
- [ ] **API keys configured** (Alpha Vantage, NewsAPI, etc.)
- [ ] **Azure OpenAI endpoint ready** (for embeddings & sentiment)
- [ ] **Ticker list finalized** (100-200 symbols)
- [ ] **Company CIK mapping prepared** (for SEC filings)
- [ ] **Network connectivity tested** (API access from environment)
- [ ] **Redis indexes created** (for vector search)
- [ ] **Monitoring dashboard set up** (to track progress)

---

## 🚀 Execution Plan

### Step-by-Step Ingestion

**Day 1: Infrastructure Setup**
- Deploy Azure Managed Redis
- Configure Redis modules and indexes
- Set up Azure Blob Storage
- Configure monitoring

**Day 2: Market Data Ingestion**
- Run historical OHLCV fetch (2-3 years)
- Estimated: 2-3 hours for 200 tickers
- Validate data quality
- Compute derived metrics

**Day 3: News & Sentiment**
- Fetch 90 days of news articles
- Estimated: 1-2 hours for 10K articles
- Run sentiment analysis
- Aggregate by ticker

**Day 4: Document Processing (Part 1)**
- Fetch SEC filings (10-K, 10-Q)
- Parse and store raw text
- Estimated: 2-3 hours for 500 filings

**Day 5: Document Processing (Part 2)**
- Generate document embeddings
- Index in RediSearch HNSW
- Estimated: 3-4 hours (embedding is slow)

**Day 6: Feature Engineering**
- Compute technical indicators
- Aggregate sentiment features
- Store in Featureform
- Estimated: 1-2 hours

**Day 7: Validation & Testing**
- Verify data quality
- Test RAG retrieval
- Test feature serving
- Run sample agent queries

---

**Document Version:** 1.0  
**Last Updated:** December 5, 2025  
**Status:** Initial one-time batch ingestion focus
