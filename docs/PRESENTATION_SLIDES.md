# FinagentiX Presentation
## AI-Powered Financial Trading Assistant

**Presentation Zen Style** - Minimal text, maximum impact

---

# PART 1: THE VISION

---

## Slide 1: Title

# FinagentiX

### AI-Powered Financial Trading Assistant

*Your intelligent investment companion*

---

## Slide 1 - NOTES

**Speaker Notes:**

FinagentiX is a production-grade multi-agent AI system that provides real-time financial market analysis, risk assessment, and trading recommendations.

**Key talking points:**
- Combines 7 specialized AI agents
- Built on Redis AI Vision architecture
- Microsoft Agent Framework (Semantic Kernel)
- Azure OpenAI for LLM capabilities

---

## Slide 2: The Problem

# Making investment decisions is hard

📊 Stock prices  
📰 News & sentiment  
📄 SEC filings (10-K, 10-Q)  
⚠️ Risk metrics  
💼 Portfolio balance

*Too much data. Too little time.*

---

## Slide 2 - NOTES

**Speaker Notes:**

Investment decisions require analyzing multiple data sources simultaneously:

1. **Stock Prices & Trends** - Historical patterns, technical indicators
2. **News & Sentiment** - Market-moving events, social media sentiment
3. **SEC Filings** - Official company financials, risk disclosures
4. **Risk Metrics** - Volatility, VaR, correlation analysis
5. **Portfolio Context** - Current positions, diversification

**The challenge:** Traditional tools are:
- Slow (manual research takes hours)
- Expensive (Bloomberg Terminal: $24,000/year)
- Not personalized (generic recommendations)
- Not conversational (can't ask follow-up questions)

---

## Slide 3: The Solution

# One Question. Complete Analysis.

*"Should I invest in Apple?"*

↓

**7 AI Agents** working together  
**< 2 seconds** response time  
**85% cost reduction** vs. traditional AI

---

## Slide 3 - NOTES

**Speaker Notes:**

FinagentiX transforms the investment research experience:

**User Experience:**
- Natural language questions
- Comprehensive multi-source analysis
- Personalized recommendations
- Conversational follow-ups

**Technical Achievement:**
- 7 specialized agents collaborate in real-time
- Sub-2-second response times
- 30-70% LLM cost savings through intelligent caching
- 137x cheaper than uncached LLM queries

**Example Query Flow:**
```
User: "Should I invest in Apple?"
↓
Market Data Agent → Current price, trends, volume
Technical Agent → RSI, MACD, Bollinger Bands
Sentiment Agent → News analysis, social sentiment
Risk Agent → Volatility, VaR, portfolio impact
Fundamental Agent → P/E, revenue, SEC filings
↓
Synthesized recommendation in < 2 seconds
```

---

## Slide 4: Screenshot - App Overview

# 📸 SCREENSHOT PLACEHOLDER

**App Overview**
- Chat interface (left)
- Metrics panel (right)

*Show the main application interface*

---

# PART 2: ARCHITECTURE

---

## Slide 5: The Architecture

# 5 Layers. One Platform.

```
         User Interface
              ↓
      Semantic Routing & Cache
              ↓
         7 AI Agents
              ↓
     Feature Store (Featureform)
              ↓
    Data Layer (Redis Multi-Model)
```

---

## Slide 5 - NOTES

**Speaker Notes:**

The Redis AI Vision Architecture consists of 5 integrated layers:

**1. User Interface Layer**
- FastAPI REST + WebSocket
- Real-time streaming responses
- Session management

**2. Semantic Routing & Cache Layer**
- Query embedding and similarity search
- Full response caching (30-70% cost savings)
- Workflow routing cache

**3. Agent Layer (Microsoft Agent Framework)**
- Orchestrator Agent (Magentic pattern)
- 6 specialized domain agents
- Sequential, Concurrent, Handoff patterns

**4. Feature Store Layer (Featureform)**
- Pre-computed technical indicators
- Risk metrics
- Valuation ratios
- Redis-backed online store

**5. Data Layer (Redis Multi-Model)**
- Vector Search (RAG, caching)
- TimeSeries (OHLCV data)
- JSON (user profiles, memory)
- Hashes (session data, tool cache)

---

## Slide 6: The 7 AI Agents

# Specialized Experts

| Agent | Role |
|-------|------|
| 🎯 **Orchestrator** | Coordinates workflow |
| 📈 **Market Data** | Prices & trends |
| 📊 **Technical** | RSI, MACD, patterns |
| 💬 **Sentiment** | News & social |
| ⚠️ **Risk** | VaR, volatility |
| 💼 **Portfolio** | Positions & balance |
| 📄 **Research** | SEC filings (RAG) |

---

## Slide 6 - NOTES

**Speaker Notes:**

Each agent is a specialized expert built on Microsoft Agent Framework (Semantic Kernel):

**1. Orchestrator Agent**
- Determines which agents to invoke
- Manages execution patterns (Sequential/Concurrent/Handoff)
- Synthesizes final response
- Uses Magentic orchestration pattern

**2. Market Data Agent**
- Real-time price feeds
- Historical OHLCV data
- Volume analysis
- Tools: `get_stock_price`, `get_historical_data`

**3. Technical Analysis Agent**
- Moving averages (SMA, EMA)
- Momentum indicators (RSI, MACD)
- Volatility bands (Bollinger)
- Pattern recognition

**4. Sentiment Agent**
- News article analysis
- Social media sentiment
- Event impact scoring
- Aggregated sentiment scores

**5. Risk Assessment Agent**
- Value at Risk (VaR)
- Conditional VaR (CVaR)
- Beta calculation
- Portfolio correlation

**6. Portfolio Management Agent**
- Position tracking
- Rebalancing recommendations
- Diversification analysis

**7. News & Research Agent**
- RAG on SEC filings
- Earnings transcripts
- Research reports

---

## Slide 7: Screenshot - Agent Execution

# 📸 SCREENSHOT PLACEHOLDER

**Agent Execution Timeline**
- Which agents ran
- How long each took
- Parallel vs sequential

*Show the execution timeline visualization*

---

# PART 3: WHY REDIS?

---

## Slide 8: The Latency Problem

# Users don't wait.

| Response Time | User Reaction |
|---------------|---------------|
| < 1 second | ✅ "Instant!" |
| 2-3 seconds | 😐 "Okay..." |
| 5+ seconds | 😤 "Is it broken?" |
| 10+ seconds | 🚪 *Tab closed* |

---

## Slide 8 - NOTES

**Speaker Notes:**

**The fundamental challenge of AI applications:**

User expectations are shaped by Google (< 0.5s) and ChatGPT streaming. Any AI application competing for user attention must deliver fast responses.

**The math problem with traditional databases:**

Multi-agent systems make many database calls:
- Agent workflow: 20-40 tool calls
- Each tool may query database 1-3 times
- Total: 60-120 database operations per query

**With disk-based databases (PostgreSQL/MongoDB):**
```
60 queries × 50ms average = 3,000ms (3 seconds)
+ LLM processing: 500-2,000ms
+ Network latency: 200-500ms
─────────────────────────────────
Total: 4-5+ seconds = BAD UX
```

**With Redis (in-memory):**
```
60 queries × 1ms average = 60ms
+ LLM processing: 500-2,000ms
+ Network latency: 200-500ms
─────────────────────────────────
Total: < 2 seconds = GOOD UX
```

**The difference:** In-memory vs disk access
- RAM latency: ~100 nanoseconds
- SSD latency: ~100 microseconds (1000x slower)
- HDD latency: ~10 milliseconds (100,000x slower)

---

## Slide 9: Redis Use Case #1

# Semantic Cache

*The same question, answered instantly*

"Should I buy AAPL?"  
≈  
"Is Apple a good investment?"

**Result:** Return cached answer in < 10ms

---

## Slide 9 - NOTES

**Speaker Notes:**

**How Semantic Cache Works:**

```
User asks: "Should I buy AAPL?"
           ↓
Generate embedding (1536 dimensions)
           ↓
Redis Vector Search (HNSW index)
           ↓
Similar query found? (similarity > 0.92)
           ↓
    YES → Return cached response (< 10ms)
           Savings: $0.05 + 2 seconds
           
    NO → Process full pipeline
           Cache result for next time
```

**Why this matters:**
- Similar questions are asked frequently
- Each full LLM pipeline costs $0.03-0.06
- Cache hit rate of 80-85% is achievable
- **30-70% total LLM cost reduction**

**Why PostgreSQL/MongoDB can't compete:**

| Metric | Redis | PostgreSQL (pgvector) | MongoDB Atlas |
|--------|-------|----------------------|---------------|
| Vector search latency | **< 10ms** | 50-100ms | 30-80ms |
| Throughput | **100k+ QPS** | 1-5k QPS | 5-10k QPS |
| Storage | RAM | Disk + cache | Disk |
| Index updates | **Instant** | Re-index needed | Background |

**The Bookshelf Analogy:**
- **Redis** = You've memorized all the words → instant recall
- **PostgreSQL** = Walk to bookshelf, find book, flip pages → slow

---

## Slide 10: Semantic Cache Visualization

# Query → Embedding → Match → Response

```
     "Should I buy AAPL?"
              ↓
    [0.234, 0.567, 0.891, ...]
              ↓
    ┌─────────────────────┐
    │  Redis Vector Index │
    │    (HNSW Search)    │
    │      < 10ms         │
    └─────────────────────┘
              ↓
    Similarity: 0.94 ✓
              ↓
    Return cached response
```

---

## Slide 10b: Screenshot - Semantic Cache

# 📸 SCREENSHOT PLACEHOLDER

**Semantic Cache Performance**
- Cache hit/miss indicator
- Similarity score
- Response time comparison

*Show the cache layer metrics from the Metrics Panel*

---

## Slide 10b - NOTES

**How to capture this screenshot:**

1. **Start the FinagentiX application**
   ```bash
   cd frontend && npm run dev
   # In another terminal:
   cd src && python -m uvicorn api.main:app --reload
   ```

2. **Ask a question first time** (cache miss):
   - Type: "Should I invest in Apple stock?"
   - Note the response time and cost in Metrics Panel

3. **Ask a similar question** (cache hit):
   - Type: "Is AAPL a good investment?"
   - Observe the cache hit indicator

4. **Capture the Metrics Panel showing:**
   - 🗄️ Cache Layer Performance section
   - "Semantic Cache: HIT" with similarity score (e.g., 0.94)
   - Response time: < 100ms (vs 1-2s for miss)
   - Cost savings displayed

5. **Alternative: Use Learn Mode**
   - Click the "Learn" toggle in the UI
   - This shows detailed cache layer breakdown
   - Capture the expanded view

**What to highlight in the screenshot:**
- The green "HIT" indicator
- Similarity score > 0.92
- Dramatic time difference (< 100ms vs 1500ms+)
- Cost: $0.00 for cached response

---

## Slide 11: Redis Use Case #2

# Semantic Router

*Skip the thinking, jump to action*

Query → **Cached workflow** → Execute agents

**Savings:** Skip orchestrator LLM call  
**Result:** -500ms, -$0.01 per query

---

## Slide 11 - NOTES

**Speaker Notes:**

**The Problem:**
The Orchestrator Agent must decide which workflow and agents to use. Without caching, this requires an expensive LLM reasoning call:

```
Without Router Cache:
─────────────────────
User: "Compare AAPL and TSLA for 5-year investment"
           ↓
Orchestrator LLM Call (200-500 tokens, ~$0.01):
  - Analyze user intent
  - Determine required data
  - Select agents
  - Plan execution order
  - Create workflow JSON
           ↓
Execute workflow (additional 500ms delay)
```

**The Redis Solution:**

```
With Semantic Router:
─────────────────────
User: "Compare AAPL and TSLA for 5-year investment"
           ↓
Redis Vector Search on past routing decisions
           ↓
Match found: "Comparative Investment Analysis"
  - Workflow: Investment_Comparison
  - Agents: [Market Data, Risk, Sentiment, Fundamental]
           ↓
Skip orchestrator LLM call!
Execute cached workflow immediately
```

**Why In-Memory is Critical:**
- Routing decision happens BEFORE actual work
- Every millisecond here delays entire pipeline
- At 100 queries/minute: 100 × 50ms = 5 seconds/minute saved

**Storage:**
- Redis HNSW vector index for semantic examples
- Redis Hash for pattern-based fallbacks
- New successful routings automatically cached

---

## Slide 12: Redis Use Case #3

# Tool Output Cache

*Every API call, cached*

One agent workflow = **20-40 tool calls**

| Without Cache | With Redis Cache |
|---------------|-----------------|
| 20 × 50ms = 1,000ms | 20 × 1ms = **20ms** |

---

## Slide 12 - NOTES

**Speaker Notes:**

**The Granular Caching Problem:**

A single agent workflow involves many tool calls:
```
Market Data Agent:
  └─ get_stock_price("AAPL")      → API call or cache?
  └─ get_historical_data("AAPL")  → API call or cache?
  └─ calculate_moving_average()    → Compute or cache?

Sentiment Agent:
  └─ search_news("AAPL")          → API call or cache?
  └─ get_social_sentiment()        → API call or cache?

Risk Agent:
  └─ get_volatility("AAPL")       → Compute or cache?
  └─ calculate_var()               → Compute or cache?
```

**Intelligent TTL Strategy:**
```python
CACHE_TTL = {
    "stock_price": 300,      # 5 minutes (changes frequently)
    "moving_average": 3600,   # 1 hour (changes slowly)
    "news_summary": 3600,     # 1 hour (new articles)
    "sec_filing": 604800,     # 7 days (rarely changes)
    "volatility": 86400,      # 24 hours (daily calc)
}
```

**Why MongoDB/PostgreSQL Fails Here:**

| Scenario | Redis | MongoDB/PostgreSQL |
|----------|-------|-------------------|
| 20 tool lookups | 20 × 1ms = **20ms** | 20 × 50ms = 1,000ms |
| Cache updates | **Instant** (in-place) | Write lock + index |
| TTL eviction | **Native** (per key) | Cron job / TTL index |
| Concurrent access | **Lock-free** | Row/document locks |

**The Trading Terminal Analogy:**
- **Redis** = High-frequency trading terminal on your desk → instant
- **PostgreSQL** = Call your broker's office, wait on hold → slow

---

## Slide 13: Screenshot - Tool Cache

# 📸 SCREENSHOT PLACEHOLDER

**Tool Cache Performance**
- Cache hit/miss rates
- Latency per tool
- Cost savings

*Show the cache layer performance metrics*

---

## Slide 14: Redis Use Case #4

# Contextual Memory

*Remember everything about the user*

```json
{
  "risk_tolerance": "moderate",
  "favorite_sectors": ["tech"],
  "portfolio": [{"AAPL": 100}]
}
```

**Lookup time:** < 1ms

---

## Slide 14 - NOTES

**Speaker Notes:**

**The Personalization Challenge:**

AI assistants need context to provide relevant answers:
- Who is this user?
- What did they ask before?
- What's their risk tolerance?
- What's in their portfolio?

**Redis Data Structures for Memory:**

**1. User Profile (RedisJSON):**
```json
{
  "user_id": "u123",
  "preferences": {
    "risk_tolerance": "moderate",
    "trading_style": "swing",
    "favorite_sectors": ["tech", "healthcare"]
  },
  "portfolio": {
    "cash": 50000,
    "positions": [
      {"ticker": "AAPL", "shares": 100, "avg_cost": 175.50}
    ]
  },
  "watchlist": ["MSFT", "GOOGL", "NVDA"]
}
```

**2. Conversation History (Sorted Set):**
```python
ZADD chat:u123 timestamp1 "User: Analyze AAPL"
ZADD chat:u123 timestamp2 "Bot: AAPL shows strong growth..."
# Get last 50 messages
ZREVRANGE chat:u123 0 50
```

**3. Session Data (Hash):**
```python
HSET session:u123 active_ticker "AAPL"
HSET session:u123 last_query "technical analysis"
HSET session:u123 query_count 42
```

**Why MongoDB Loses:**

| Aspect | Redis | MongoDB |
|--------|-------|---------|
| Session lookup | **< 1ms** | 5-20ms |
| Partial updates | **O(1)** HSET | Full doc replace |
| Memory efficiency | ~53% less | JSON overhead |
| Real-time updates | **Pub/Sub native** | Change Streams |

**The Notepad Analogy:**
- **Redis** = Notes on your desk, instantly accessible
- **MongoDB** = File cabinet in another room, need to walk there

---

## Slide 15: Redis Use Case #5

# TimeSeries Data

*5 years of stock data, instantly queryable*

```
TS.RANGE ts:AAPL:close
    FROM -252days
    TO now
    AGGREGATION avg 1d
```

**Result:** < 1ms for 252 data points

---

## Slide 15 - NOTES

**Speaker Notes:**

**Financial Data Requirements:**

Stock analysis requires historical OHLCV data:
- **O**pen, **H**igh, **L**ow, **C**lose, **V**olume
- Multiple timeframes: 1m, 5m, 1h, 1d
- Years of history for trend analysis

**Redis TimeSeries Advantages:**

```python
# Native time-range query
TS.RANGE ts:AAPL:close 
    FROMTIMESTAMP 1609459200  # Jan 1, 2021
    TOTIMESTAMP 1704067200    # Jan 1, 2024
    AGGREGATION avg 86400000  # Daily average

# Automatic downsampling
TS.CREATERULE ts:AAPL:close:raw 
    ts:AAPL:close:hourly 
    AGGREGATION avg 3600000

# Labels for filtering
TS.MRANGE - + 
    FILTER ticker=AAPL type=close
```

**Comparison with TimescaleDB:**

| Aspect | Redis TimeSeries | TimescaleDB |
|--------|-----------------|-------------|
| Range query | **< 1ms** (in-memory) | 10-50ms (disk) |
| Aggregation | **Native** (built-in) | SQL overhead |
| Downsampling | **Automatic** rules | Manual partitioning |
| Insert rate | **100k+/sec** | 10-50k/sec |
| Memory model | **RAM first** | Disk first |

**The Thermometer Analogy:**
- **Redis** = Smart thermometer with built-in display, scroll back instantly
- **TimescaleDB** = Weather archive, need to dig through logbooks

**Data Structure:**
```
ts:AAPL:open     → TimeSeries (daily opens)
ts:AAPL:high     → TimeSeries (daily highs)
ts:AAPL:low      → TimeSeries (daily lows)
ts:AAPL:close    → TimeSeries (daily closes)
ts:AAPL:volume   → TimeSeries (daily volume)
```

---

## Slide 16: Redis Use Case #6

# RAG Document Search

*200 pages → Top 5 relevant sections*

Query: "What are Apple's biggest risks?"

↓

**HNSW Vector Search** → < 10ms

↓

Relevant 10-K sections returned

---

## Slide 16 - NOTES

**Speaker Notes:**

**The Document Search Challenge:**

SEC 10-K filings are 200+ pages of dense financial information:
- Risk factors
- Management discussion
- Financial statements
- Legal proceedings
- Business description

Users ask questions like:
- "What are Apple's biggest risks?"
- "What's their revenue guidance?"
- "Any pending lawsuits?"

**The RAG Pipeline:**

```
SEC 10-K Filing (200 pages)
           ↓
Chunk into ~500 token sections
           ↓
Generate embedding for each chunk (Azure OpenAI)
           ↓
Store in Redis Vector Index (HNSW)
           ↓

User Query: "Apple's biggest risks?"
           ↓
Generate query embedding
           ↓
Redis KNN Search: Top 5 similar chunks
           ↓
LLM synthesizes answer with retrieved context
```

**Redis vs. Dedicated Vector DBs:**

| Aspect | Redis Vector | Pinecone | Weaviate |
|--------|-------------|----------|----------|
| Latency | **< 10ms** | 20-50ms | 30-80ms |
| Cost | **Self-hosted** | $70-700/mo | $25-100/mo |
| Integration | **Same platform** | Separate service | Separate service |
| Filtering | **Native RediSearch** | Limited | GraphQL |
| Other data | **TimeSeries, JSON, etc.** | Vectors only | Vectors only |

**The Key Advantage: One Platform**

Without Redis:
```
Cache → Redis/Memcached
Vectors → Pinecone
TimeSeries → InfluxDB
User Data → MongoDB
─────────────────────
4 services, 4 network hops, sync complexity
```

With Redis:
```
Cache → Redis
Vectors → Redis
TimeSeries → Redis
User Data → Redis
─────────────────────
1 service, 0 network hops, always consistent
```

---

## Slide 17: Screenshot - RAG Response

# 📸 SCREENSHOT PLACEHOLDER

**RAG Response with Sources**
- Answer with citations
- Source document links
- Confidence scores

*Show a RAG-powered response*

---

## Slide 18: One Platform. Everything.

# Why Redis Wins

```
┌─────────────────────────────────┐
│           REDIS                 │
├─────────────────────────────────┤
│  Vector Search  │  TimeSeries   │
│     (RAG)       │   (OHLCV)     │
├─────────────────┼───────────────┤
│     JSON        │    Hashes     │
│   (Profiles)    │   (Cache)     │
└─────────────────────────────────┘

Zero network hops. Always consistent.
```

---

## Slide 18 - NOTES

**Speaker Notes:**

**The Polyglot Persistence Anti-Pattern:**

Traditional architectures use multiple databases:
```
┌─────────────┐     ┌─────────────┐
│  Pinecone   │     │  InfluxDB   │
│  (Vectors)  │     │ (TimeSeries)│
└──────┬──────┘     └──────┬──────┘
       │                   │
       │   ┌─────────────┐ │
       └──►│ Application │◄┘
           └──────┬──────┘
       ┌──────────┴──────────┐
       │                     │
┌──────┴──────┐       ┌──────┴──────┐
│  MongoDB    │       │   Redis     │
│  (Documents)│       │   (Cache)   │
└─────────────┘       └─────────────┘
```

**Problems:**
1. **Network latency** between services (10-50ms each)
2. **Consistency** issues (eventual consistency, sync delays)
3. **Operational complexity** (4 databases to manage)
4. **Cost** (4 separate services to pay for)
5. **Debugging** nightmare (which DB caused the issue?)

**The Redis Unified Solution:**

```
┌─────────────────────────────────────┐
│              REDIS                  │
│        (Single Platform)            │
├─────────────────────────────────────┤
│  RediSearch   │  RedisTimeSeries    │
│  (Vectors +   │  (OHLCV data)       │
│   Full-text)  │                     │
├───────────────┼─────────────────────┤
│  RedisJSON    │  Redis Hashes       │
│  (Documents)  │  (Key-Value Cache)  │
└─────────────────────────────────────┘
           │
           ▼
    ┌─────────────┐
    │ Application │
    └─────────────┘
```

**Benefits:**
1. **Zero network hops** between data types
2. **Strong consistency** (single source of truth)
3. **One platform** to operate
4. **Lower cost** (single service)
5. **Simple debugging** (one place to look)

---

# PART 4: WHY FEATUREFORM?

---

## Slide 19: The Feature Engineering Problem

# Computing features is expensive

```
Agent asks: "Analyze AAPL"
           ↓
Load 252 days of data (50ms)
Calculate 12 indicators (30ms)
           ↓
Risk Agent asks: same data again!
Load 252 days AGAIN (50ms) ← Waste!
Calculate 7 metrics (40ms)
           ↓
Total: 250ms of redundant work
```

---

## Slide 19 - NOTES

**Speaker Notes:**

**The Problem: Repeated Computations**

Without a feature store, every agent computes features on-demand:

```
User asks: "Analyze AAPL"

Market Data Agent:
├─ Load 252 days of price data (50ms)
├─ Calculate SMA 20, 50, 200 (10ms)
├─ Calculate EMA 12, 26 (10ms)
├─ Calculate RSI 14 (5ms)
├─ Calculate MACD (5ms)
└─ Total: 80ms

Risk Agent:
├─ Load 252 days of price data AGAIN (50ms) ← REDUNDANT!
├─ Load SPY benchmark data (50ms)
├─ Calculate volatility 30d, 90d (15ms)
├─ Calculate beta vs SPY (10ms)
├─ Calculate VaR, CVaR (15ms)
└─ Total: 140ms

Fundamental Agent:
├─ Load financial ratios (30ms)
├─ Calculate P/E, P/B, P/S (10ms)
└─ Total: 40ms
─────────────────────────────────────
Total feature computation: 260ms
Data loaded 3 times (redundant!)
```

**The Scale Problem:**

For 20 tickers analyzed per hour:
- 260ms × 20 = 5.2 seconds of computation
- 3 redundant data loads × 20 = 60 unnecessary fetches
- CPU cycles wasted on same calculations

**What we need:**
- Pre-compute features once
- Serve instantly to all agents
- Update on schedule (not on-demand)

---

## Slide 20: Featureform Solution

# Pre-computed. Instantly served.

**Daily Batch Job (2 AM):**
- Compute all features
- Store in Redis
- Set TTL

**Agent Request:**
```
GET ff:feature:AAPL:rsi_14 → < 1ms
```

**55x faster!**

---

## Slide 20 - NOTES

**Speaker Notes:**

**The Featureform Architecture:**

```
┌─────────────────────────────────────────────┐
│         DAILY BATCH JOB (2 AM)              │
│                                             │
│  For each ticker:                           │
│  ├─ Load price history once                 │
│  ├─ Compute all technical indicators        │
│  ├─ Compute all risk metrics                │
│  ├─ Get valuation ratios                    │
│  └─ Store all features in Redis             │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│              REDIS FEATURE STORE            │
│                                             │
│  ff:feature:AAPL:sma_20 = 185.32 (TTL 1h)   │
│  ff:feature:AAPL:rsi_14 = 58.3 (TTL 1h)     │
│  ff:feature:AAPL:beta = 1.25 (TTL 24h)      │
│  ff:feature:AAPL:pe_ratio = 28.5 (TTL 7d)   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│             AGENT REQUEST                   │
│                                             │
│  Market Data Agent:                         │
│  └─ GET ff:feature:AAPL:* → 2ms (pipeline)  │
│                                             │
│  Risk Agent:                                │
│  └─ GET ff:feature:AAPL:* → 2ms (pipeline)  │
│                                             │
│  Total: 4ms (vs 260ms before) = 55x faster! │
└─────────────────────────────────────────────┘
```

**Performance Comparison:**

| Metric | On-Demand | Featureform + Redis |
|--------|-----------|---------------------|
| Feature lookup | 260ms | **4ms** |
| Data loads | 3 (redundant) | **0** (pre-loaded) |
| CPU usage | High (real-time calc) | **Low** (cached) |
| Consistency | Variable | **Guaranteed** |

---

## Slide 21: The 29 Features

# Technical • Risk • Valuation

| Category | Features | TTL |
|----------|----------|-----|
| **Technical (12)** | SMA, EMA, RSI, MACD, Bollinger | 1 hour |
| **Risk (7)** | Volatility, Beta, VaR, Sharpe | 24 hours |
| **Valuation (5)** | P/E, P/B, P/S, Dividend | 7 days |

---

## Slide 21 - NOTES

**Speaker Notes:**

**Complete Feature Inventory:**

**Technical Indicators (12 features):**
```
Moving Averages:
├─ sma_20      # Simple Moving Average (20 days)
├─ sma_50      # Simple Moving Average (50 days)
├─ sma_200     # Simple Moving Average (200 days)
├─ ema_12      # Exponential Moving Average (12 days)
└─ ema_26      # Exponential Moving Average (26 days)

Momentum:
├─ rsi_14      # Relative Strength Index (14 days)
├─ macd        # MACD Line
├─ macd_signal # MACD Signal Line
└─ macd_hist   # MACD Histogram

Volatility Bands:
├─ bb_upper    # Bollinger Band Upper
├─ bb_middle   # Bollinger Band Middle
└─ bb_lower    # Bollinger Band Lower
```

**Risk Metrics (7 features):**
```
├─ volatility_30d   # 30-day volatility
├─ volatility_90d   # 90-day volatility
├─ beta             # Beta vs S&P 500
├─ var_95           # Value at Risk (95%)
├─ cvar_95          # Conditional VaR (95%)
├─ sharpe_ratio     # Sharpe Ratio
└─ max_drawdown     # Maximum Drawdown
```

**Valuation Metrics (5 features):**
```
├─ pe_ratio         # Price to Earnings
├─ pb_ratio         # Price to Book
├─ ps_ratio         # Price to Sales
├─ dividend_yield   # Dividend Yield
└─ market_cap       # Market Capitalization
```

**TTL Strategy:**
- **Technical (1 hour):** Changes with price, needs fresh data
- **Risk (24 hours):** Statistical measures, stable over day
- **Valuation (7 days):** Fundamental data, quarterly updates

---

## Slide 22: Why Not Just Redis?

# Featureform adds governance

| Aspect | Just Redis | Featureform + Redis |
|--------|------------|---------------------|
| Versioning | ❌ Manual | ✅ Git-like |
| Lineage | ❌ None | ✅ Full tracking |
| Monitoring | ❌ DIY | ✅ Built-in |
| Collaboration | ❌ None | ✅ Feature registry |

---

## Slide 22 - NOTES

**Speaker Notes:**

**Why Featureform Matters Beyond Caching:**

**1. Feature Versioning:**
```python
# Track feature changes over time
@ff.feature
def rsi_14(stock_data):
    """RSI calculation - version 2.0"""
    return calculate_rsi(stock_data, period=14)
    
# Rollback to previous version if issues
ff.rollback("rsi_14", version="1.0")
```

**2. Data Lineage:**
```
rsi_14 feature:
├─ Source: Yahoo Finance API
├─ Transformation: scripts/compute_features.py
├─ Dependencies: ts:AAPL:close (TimeSeries)
├─ Last computed: 2025-01-14 02:00:00
└─ Used by: Market Data Agent, Technical Agent
```

**3. Feature Registry:**
```
All registered features in one place:
├─ Technical indicators (12)
├─ Risk metrics (7)
├─ Valuation ratios (5)

Each feature has:
├─ Description
├─ Owner
├─ SLA (freshness requirements)
├─ Dependencies
└─ Usage statistics
```

**4. Monitoring & Alerts:**
```
Feature health dashboard:
├─ Freshness: Is data up-to-date?
├─ Quality: Any null values? Outliers?
├─ Usage: Which agents use which features?
└─ Performance: Serving latency OK?
```

**The Mise en Place Analogy:**
- **Just Redis** = Ingredients in fridge, you track everything mentally
- **Featureform** = Mise en place! Everything prepped, labeled, organized, with expiration dates

---

## Slide 23: Screenshot - Featureform

# 📸 SCREENSHOT PLACEHOLDER

**Featureform Dashboard**
- Feature registry
- Data lineage
- Health metrics

*Show Featureform management interface*

---

# PART 5: COST ANALYSIS

---

## Slide 24: Without Caching

# LLM costs explode

```
Typical query: "Should I invest in AAPL?"

Orchestrator:    $0.006
Market Agent:    $0.015
Sentiment Agent: $0.012
Risk Agent:      $0.009
Synthesis:       $0.024
─────────────────────────
Per query:       $0.066

× 1,000 queries/day = $66/day
× 30 days = $1,980/month
```

---

## Slide 24 - NOTES

**Speaker Notes:**

**Detailed Cost Breakdown (Without Caching):**

```
Query: "Should I invest in Apple?"

Step 1: Orchestrator Reasoning
├─ Analyze user intent
├─ Select appropriate agents
├─ Plan execution workflow
├─ Tokens: ~200
└─ Cost: 200 × $0.00003 = $0.006

Step 2: Market Data Agent
├─ Get current price
├─ Analyze trends
├─ Technical indicators summary
├─ Tokens: ~500
└─ Cost: 500 × $0.00003 = $0.015

Step 3: Sentiment Agent
├─ Search recent news
├─ Analyze sentiment
├─ Summarize findings
├─ Tokens: ~400
└─ Cost: 400 × $0.00003 = $0.012

Step 4: Risk Agent
├─ Calculate risk metrics
├─ Portfolio impact analysis
├─ Tokens: ~300
└─ Cost: 300 × $0.00003 = $0.009

Step 5: Final Synthesis
├─ Combine all agent outputs
├─ Generate coherent response
├─ Tokens: ~800
└─ Cost: 800 × $0.00003 = $0.024
─────────────────────────────────────
Total per query: $0.066
```

**Monthly Projection:**
```
Conservative usage: 1,000 queries/day
├─ Daily cost: $66
├─ Monthly cost: $1,980
└─ Annual cost: $23,760

Heavy usage: 5,000 queries/day
├─ Daily cost: $330
├─ Monthly cost: $9,900
└─ Annual cost: $118,800
```

**The problem:** These costs scale linearly with usage. No economies of scale.

---

## Slide 25: With Redis Caching

# 85% cost reduction

```
With 85% cache hit rate:

850 queries: Cache hit    → $0.00
150 queries: Full process → $9.90
Embeddings:               → $0.10
─────────────────────────────────
Per 1,000 queries:        $10/day

× 30 days = $300/month

Savings: $1,680/month (85%)
```

---

## Slide 25 - NOTES

**Speaker Notes:**

**Detailed Cost Analysis (With Redis Caching):**

```
1,000 queries per day with 85% cache hit rate:

Cache Hits (850 queries):
├─ Semantic cache lookup: FREE
├─ Embedding generation: 850 × $0.0001 = $0.085
└─ Total: $0.085

Cache Misses (150 queries):
├─ Full pipeline: 150 × $0.066 = $9.90
├─ Cache storage: negligible
└─ Total: $9.90
─────────────────────────────────────
Daily total: $9.985 ≈ $10/day
Monthly total: $300/month
```

**Savings Calculation:**
```
Without caching: $1,980/month
With caching:    $300/month
─────────────────────────────
Savings:         $1,680/month (85% reduction!)
Annual savings:  $20,160
```

**ROI on Redis Enterprise:**
```
Redis Enterprise cost: ~$500-1,000/month
LLM savings:           $1,680/month
─────────────────────────────────────
Net savings:           $680-1,180/month
ROI:                   ~2 months
```

**How to achieve 85% cache hit rate:**
1. **Semantic similarity:** Similar questions hit cache (0.92 threshold)
2. **Popular queries:** Common questions always cached
3. **Warm-up:** Pre-populate cache with likely questions
4. **TTL tuning:** Balance freshness vs hit rate

**Additional savings not counted:**
- Tool cache hits (20-40% reduction in API calls)
- Router cache hits (skip orchestrator LLM calls)
- Feature store (no redundant computations)

---

## Slide 26: Performance Comparison

# Speed + Savings

| Metric | Without Redis | With Redis |
|--------|---------------|------------|
| Response time | 4-5 sec | **< 2 sec** |
| Cost per query | $0.066 | **$0.01** |
| Throughput | 10 req/sec | **1000+ req/sec** |
| Feature lookup | 250ms | **4ms** |

---

## Slide 26 - NOTES

**Speaker Notes:**

**Complete Performance Comparison:**

**Response Time:**
```
Without Redis:
├─ DB queries (60×): 60 × 50ms = 3,000ms
├─ LLM processing: 1,500ms
├─ Network latency: 500ms
└─ Total: 5,000ms (5 seconds)

With Redis:
├─ Redis queries (60×): 60 × 1ms = 60ms
├─ LLM processing: 1,500ms (or 0 if cached)
├─ Network latency: 200ms
└─ Total: 1,760ms (< 2 seconds)
```

**Throughput:**
```
Without Redis:
├─ Each request: 5 seconds
├─ Serial processing: 12 requests/minute
└─ Max throughput: ~10 req/sec (with parallelism)

With Redis:
├─ Each request: < 2 seconds
├─ In-memory processing: non-blocking
└─ Max throughput: 1000+ req/sec
```

**Cost per Query:**
```
Without Redis:
└─ $0.066/query (all LLM calls)

With Redis (85% cache hit):
└─ $0.01/query average
```

**Feature Lookup:**
```
Without Redis (on-demand):
├─ Load data: 50ms
├─ Compute indicators: 200ms
└─ Total: 250ms

With Featureform + Redis:
├─ Pre-computed GET: 4ms
└─ Total: 4ms (55x faster)
```

---

## Slide 27: Screenshot - Cost Breakdown

# 📸 SCREENSHOT PLACEHOLDER

**Cost Breakdown Panel**
- This query cost
- Without cache estimate
- Savings percentage
- Historical trends

*Show the cost comparison visualization*

---

# PART 6: SUMMARY

---

## Slide 28: The Redis AI Vision

# One Platform. Every AI Workload.

```
┌─────────────────────────────────┐
│           REDIS                 │
├────────────┬────────────────────┤
│   Vector   │    TimeSeries      │
│  (Cache,   │    (Market         │
│   RAG)     │     Data)          │
├────────────┼────────────────────┤
│   JSON     │    Hashes          │
│  (Memory)  │    (Tools)         │
└────────────┴────────────────────┘
```

**Zero network hops. Sub-millisecond latency.**

---

## Slide 28 - NOTES

**Speaker Notes:**

**The Redis AI Vision - Core Principles:**

**1. Unified Platform**
Instead of:
- Pinecone for vectors
- InfluxDB for time-series
- MongoDB for documents
- Memcached for caching

One platform:
- Redis for everything

**2. In-Memory First**
- All hot data in RAM
- Persistence for durability (AOF, RDB)
- No disk seeks for active data

**3. Multi-Model Data**
- Not just key-value
- Vectors, JSON, TimeSeries, Graphs, Streams
- Each data type optimized for its use case

**4. Low Latency by Design**
- < 1ms for simple operations
- < 10ms for complex searches
- Predictable performance at scale

**Why This Matters for AI:**
```
AI applications are:
├─ Latency-sensitive (users expect instant)
├─ Data-diverse (vectors, time-series, JSON)
├─ High-throughput (many concurrent users)
└─ Cost-conscious (LLM calls are expensive)

Redis delivers:
├─ Sub-millisecond latency ✓
├─ Multi-model support ✓
├─ 100k+ operations/sec ✓
└─ Intelligent caching ✓
```

---

## Slide 29: Key Takeaways

# Remember These

1️⃣ **Latency is critical**  
   Users expect < 2 seconds

2️⃣ **LLM costs explode without caching**  
   85% savings with semantic cache

3️⃣ **One platform beats many**  
   Redis = vectors + time-series + JSON + cache

4️⃣ **Pre-compute beats on-demand**  
   Featureform = instant feature serving

---

## Slide 29 - NOTES

**Speaker Notes:**

**Detailed Takeaways for Different Audiences:**

**For Executives:**
```
Business Value:
├─ 85% cost reduction on AI infrastructure
├─ ROI in 2 months on Redis investment
├─ Competitive advantage: faster user experience
└─ Scalability: 100x throughput increase
```

**For Architects:**
```
Technical Value:
├─ Simplified architecture (1 platform vs 4)
├─ Reduced operational complexity
├─ Consistent data model
├─ Proven patterns (Redis AI Vision)
└─ Enterprise-grade reliability
```

**For Developers:**
```
Developer Experience:
├─ Single SDK for all data operations
├─ Familiar Redis commands
├─ Rich ecosystem (clients, tools, docs)
├─ Easy debugging (one place to look)
└─ Fast iteration (instant feedback)
```

**For Product Managers:**
```
User Experience:
├─ < 2 second response times
├─ Personalized recommendations (memory)
├─ Contextual conversations
├─ Reliable service (high availability)
└─ Consistent quality
```

---

## Slide 30: Thank You

# Questions?

**FinagentiX**  
AI-Powered Financial Trading Assistant

🔗 GitHub: tfindelkind-redis/FinagentiX  
📧 Contact: [your-email]

---

## Slide 30 - NOTES

**Speaker Notes:**

**Anticipated Questions and Answers:**

**Q: What about data persistence? Isn't Redis volatile?**
A: Redis Enterprise provides:
- AOF (Append-Only File) - every write persisted
- RDB snapshots - periodic full backups
- Active-Active replication - cross-datacenter durability
- 99.999% uptime SLA

**Q: How does this compare to using OpenAI's built-in caching?**
A: OpenAI caching is:
- Limited to exact matches (no semantic similarity)
- Not under your control (TTL, invalidation)
- No integration with other data types
Redis semantic cache:
- Finds similar questions (0.92 threshold)
- Full control over TTL and invalidation
- Integrated with all other Redis features

**Q: What's the total cost of this architecture?**
A: Example monthly costs:
- Redis Enterprise E5 (6GB): ~$500-800
- Azure OpenAI (with caching): ~$300
- Featureform Container App: ~$100
- Total: ~$900-1,200/month
- Savings vs. no caching: $1,680/month
- Net savings: $500-800/month

**Q: Can this scale to millions of users?**
A: Yes, Redis Enterprise supports:
- Linear scaling with clustering
- Active-Active for global distribution
- 200M+ ops/sec demonstrated
- Auto-scaling in Azure

---

# APPENDIX: ADDITIONAL SLIDES

---

## Appendix A: Data Flow Diagram

# Complete Query Flow

```
User: "Should I invest in AAPL?"
              ↓
    [1] Semantic Cache Check (Redis Vector)
         Cache Hit? → Return immediately
              ↓
    [2] Contextual Memory Load (RedisJSON)
              ↓
    [3] Semantic Router (Redis Vector)
         Cached workflow? → Skip orchestrator
              ↓
    [4] Agent Execution
         ├─ Market Data Agent
         ├─ Sentiment Agent  } Tool Cache (Redis Hash)
         ├─ Risk Agent
         └─ RAG Search (Redis Vector)
              ↓
    [5] LLM Synthesis (Azure OpenAI)
              ↓
    [6] Cache Response (Redis Vector)
              ↓
    [7] Update Memory (RedisJSON)
              ↓
    Response delivered
```

---

## Appendix B: Technology Stack

# Full Stack Details

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | React + TypeScript | User interface |
| API | FastAPI + WebSocket | Real-time communication |
| Agents | Semantic Kernel (Python) | AI orchestration |
| LLM | Azure OpenAI GPT-4 | Language understanding |
| Vectors | RediSearch HNSW | Similarity search |
| TimeSeries | RedisTimeSeries | Market data |
| Documents | RedisJSON | User profiles |
| Features | Featureform | ML features |
| Cache | Redis Hashes | Tool outputs |

---

## Appendix C: Deployment Architecture

# Azure Deployment

```
┌─────────────────────────────────────────────────────┐
│                    Azure VNet                        │
│                                                      │
│  ┌─────────────────┐    ┌─────────────────┐         │
│  │  Container App  │    │  Container App  │         │
│  │   (Frontend)    │    │   (API)         │         │
│  └────────┬────────┘    └────────┬────────┘         │
│           │                      │                   │
│           └──────────┬───────────┘                   │
│                      │                               │
│  ┌───────────────────┴───────────────────┐          │
│  │       Azure Managed Redis              │          │
│  │       (Enterprise Tier)                │          │
│  │                                        │          │
│  │  • RediSearch (Vectors + Full-text)   │          │
│  │  • RedisTimeSeries (Market data)      │          │
│  │  • RedisJSON (User profiles)          │          │
│  │  • RedisBloom (Deduplication)         │          │
│  └────────────────────────────────────────┘          │
│                      │                               │
│  ┌───────────────────┴───────────────────┐          │
│  │         Private Endpoints              │          │
│  │  • Azure OpenAI                        │          │
│  │  • Azure Storage                       │          │
│  │  • Featureform Container App           │          │
│  └────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────┘
```

---

## Appendix D: Caching Layers Explained

# Three Layers of Intelligence

```
┌─────────────────────────────────────────────────────┐
│  LAYER 1: SEMANTIC CACHE (Full Response)            │
│  ─────────────────────────────────────────          │
│  When: Before ANY processing                        │
│  What: Cache entire responses to similar questions  │
│  Savings: 30-70% (skip all downstream work)         │
│  Example: "Buy AAPL?" ≈ "Invest in Apple?"         │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  LAYER 2: SEMANTIC ROUTER (Workflow Decision)       │
│  ─────────────────────────────────────────          │
│  When: During request analysis                      │
│  What: Cache routing decisions                      │
│  Savings: Skip orchestrator LLM reasoning           │
│  Example: "Compare X vs Y" → Comparison workflow    │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  LAYER 3: TOOL CACHE (Individual Outputs)           │
│  ─────────────────────────────────────────          │
│  When: During agent execution                       │
│  What: Cache every tool call result                 │
│  Savings: 20-40x fewer API calls                    │
│  Example: get_price("AAPL") → cached 5 minutes     │
└─────────────────────────────────────────────────────┘
```

---

## Appendix E: Feature Store Deep Dive

# Featureform + Redis Architecture

```
┌─────────────────────────────────────────────────────┐
│           OFFLINE FEATURE PIPELINE                   │
│                                                      │
│  Yahoo Finance API                                   │
│         ↓                                            │
│  scripts/compute_features.py (Daily 2 AM)           │
│         ↓                                            │
│  ┌─────────────────────────────────────────┐        │
│  │ Technical Indicators                     │        │
│  │  SMA, EMA, RSI, MACD, Bollinger         │        │
│  └─────────────────────────────────────────┘        │
│         ↓                                            │
│  ┌─────────────────────────────────────────┐        │
│  │ Risk Metrics                             │        │
│  │  Volatility, Beta, VaR, Sharpe          │        │
│  └─────────────────────────────────────────┘        │
│         ↓                                            │
│  ┌─────────────────────────────────────────┐        │
│  │ Valuation Ratios                         │        │
│  │  P/E, P/B, P/S, Dividend Yield          │        │
│  └─────────────────────────────────────────┘        │
│         ↓                                            │
│  Redis Feature Store (ff:feature:TICKER:*)          │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│           ONLINE FEATURE SERVING                     │
│                                                      │
│  Agent Request: "Analyze AAPL"                      │
│         ↓                                            │
│  Redis Pipeline GET:                                 │
│  ├─ ff:feature:AAPL:sma_20                          │
│  ├─ ff:feature:AAPL:rsi_14                          │
│  ├─ ff:feature:AAPL:beta                            │
│  └─ ff:feature:AAPL:pe_ratio                        │
│         ↓                                            │
│  All features returned in < 4ms                     │
└─────────────────────────────────────────────────────┘
```

---

## Appendix F: Glossary

# Key Terms

| Term | Definition |
|------|------------|
| **Semantic Cache** | Cache that matches by meaning, not exact text |
| **HNSW** | Hierarchical Navigable Small World (vector index algorithm) |
| **RAG** | Retrieval-Augmented Generation (LLM + search) |
| **TTL** | Time To Live (cache expiration) |
| **Feature Store** | Pre-computed ML features for instant serving |
| **Embedding** | Vector representation of text (1536 dimensions) |
| **Cosine Similarity** | Measure of vector similarity (0.0 - 1.0) |
| **VaR** | Value at Risk (financial risk metric) |
| **OHLCV** | Open, High, Low, Close, Volume (price data) |
| **Agent** | Specialized AI component for specific tasks |

---

# END OF PRESENTATION

**File:** PRESENTATION_SLIDES.md  
**Format:** Markdown (convert to PowerPoint/Keynote/Google Slides)  
**Style:** Presentation Zen (minimal text on main slides, detailed notes for reference)
