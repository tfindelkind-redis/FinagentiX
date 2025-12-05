# Redis Integration Guide for FinagentiX

## 🎯 Redis AI Vision Implementation

This document details how FinagentiX leverages Redis following the **Redis AI Vision** architecture pattern.

---

## 1️⃣ Semantic Routing & LongCache

### Purpose
Reduce LLM costs by 30-70% through intelligent query caching

### How It Works
```
User Query
    ↓
Embed query (text-embedding-3-large)
    ↓
Search Redis Vector Index for similar queries
    ↓
    ├─→ [Similarity > 0.92] → Return cached response (137x cheaper!)
    │
    └─→ [New query] → Call Azure OpenAI GPT-4
                          ↓
                      Store response + embedding in Redis
```

### Redis Components
- **RediSearch** with HNSW vector index
- **Index:** `idx:semantic_cache`
- **Schema:**
  ```
  query_embedding: VECTOR (HNSW, dim=3072)
  query_text: TEXT
  response: TEXT
  timestamp: NUMERIC
  usage_count: NUMERIC
  ```

### Code Pattern
```python
from redis import Redis
from redis.commands.search.field import VectorField, TextField
from redis.commands.search.indexDefinition import IndexDefinition

# Create semantic cache index
client = Redis(host='your-redis-host', port=6379)
schema = [
    VectorField("query_embedding", "HNSW", {
        "TYPE": "FLOAT32",
        "DIM": 3072,
        "DISTANCE_METRIC": "COSINE"
    }),
    TextField("query_text"),
    TextField("response")
]
client.ft("idx:semantic_cache").create_index(schema)

# Query semantic cache
def get_cached_response(query_embedding, threshold=0.92):
    results = client.ft("idx:semantic_cache").search(
        Query(f"*=>[KNN 1 @query_embedding $vec AS score]")
        .sort_by("score")
        .dialect(2),
        query_params={"vec": query_embedding}
    )
    if results.docs and float(results.docs[0].score) >= threshold:
        return results.docs[0].response
    return None
```

### Performance
- **Latency:** <10ms for similarity search
- **Cost Savings:** 30-70% on LLM calls
- **Hit Rate:** 80-85% achievable
- **Storage:** ~4KB per cached query+response

---

## 2️⃣ Contextual Memory (Agentic Memory)

### Purpose
Maintain conversation context and user state with ~53% memory savings

### How It Works
```
User Interaction
    ↓
Extract: preferences, actions, portfolio state
    ↓
Store in Redis (JSON, Hashes, Sorted Sets)
    ↓
Retrieve context for next interaction
```

### Redis Components

#### User Profile (RedisJSON)
```json
{
  "user_id": "u123",
  "preferences": {
    "risk_tolerance": "moderate",
    "trading_style": "swing",
    "sectors": ["tech", "healthcare"]
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

#### Conversation History (Sorted Set)
```python
# Store conversation with timestamp scores
client.zadd("chat:u123", {
    "User: What's AAPL price?": time.time(),
    "Agent: AAPL is at $195.30": time.time() + 1
})

# Retrieve last N messages
messages = client.zrevrange("chat:u123", 0, 50, withscores=True)
```

#### Session Data (Hash)
```python
client.hset("session:u123", mapping={
    "active_ticker": "AAPL",
    "last_query": "technical analysis",
    "query_count": 42
})
```

### Performance
- **Memory Savings:** ~53% vs uncompressed JSON
- **Recall:** 95%+ for relevant context
- **Latency:** <1ms for context retrieval

---

## 3️⃣ Document Knowledge Base (RAG)

### Purpose
Q&A on financial documents (10-K, earnings, news) with <10ms retrieval

### How It Works
```
Financial Document (10-K filing)
    ↓
Chunk into passages (~500 tokens each)
    ↓
Embed each chunk (text-embedding-3-large)
    ↓
Store in Redis Vector Index
    ↓
User asks: "What is Apple's revenue guidance?"
    ↓
Embed query → Search Redis → Return top K chunks
    ↓
Pass chunks to LLM for answer generation
```

### Redis Components
- **RediSearch** HNSW index
- **Index:** `idx:documents`
- **Schema:**
  ```
  doc_embedding: VECTOR (HNSW, dim=3072)
  doc_text: TEXT
  source: TEXT (10-K, 10-Q, news, etc.)
  ticker: TAG
  date: NUMERIC
  chunk_id: NUMERIC
  ```

### Code Pattern
```python
# Create document index
schema = [
    VectorField("doc_embedding", "HNSW", {
        "TYPE": "FLOAT32",
        "DIM": 3072,
        "DISTANCE_METRIC": "COSINE"
    }),
    TextField("doc_text"),
    TagField("ticker"),
    TagField("source"),
    NumericField("date")
]
client.ft("idx:documents").create_index(schema)

# RAG retrieval
def retrieve_context(query_embedding, ticker=None, top_k=5):
    query = Query(f"@ticker:{{{ticker}}}=>[KNN {top_k} @doc_embedding $vec AS score]") \
        .sort_by("score") \
        .return_fields("doc_text", "source", "score") \
        .dialect(2)
    
    results = client.ft("idx:documents").search(
        query,
        query_params={"vec": query_embedding}
    )
    return [doc.doc_text for doc in results.docs]
```

### Performance
- **Latency:** <10ms for retrieval
- **Capacity:** 10M+ document vectors
- **Accuracy:** Top-5 recall >90%

---

## 4️⃣ Featureform Integration

### Purpose
Real-time feature serving for ML/trading features backed by Redis

### How It Works
```
Raw Market Data (prices, news, etc.)
    ↓
Featureform Transformation Pipeline (Redis Streams)
    ↓
Compute Features:
  - Technical: RSI, MACD, Bollinger Bands
  - Sentiment: News sentiment scores
  - Risk: VaR, beta, correlation
    ↓
Store in Redis (Hashes, TimeSeries)
    ↓
Agents request features → <1ms response
```

### Redis Components

#### Feature Serving (Hashes)
```python
# Store features for AAPL
client.hset("features:AAPL", mapping={
    "price": 195.30,
    "rsi_14": 58.2,
    "macd": 2.15,
    "bb_upper": 198.50,
    "bb_lower": 192.10,
    "sentiment_score": 0.72,
    "volume_ratio": 1.3
})

# Retrieve all features
features = client.hgetall("features:AAPL")
```

#### Time-Series Features (RedisTimeSeries)
```python
# Create time-series for price
client.ts().create("ts:AAPL:price", retention_msecs=86400000)

# Add price data points
client.ts().add("ts:AAPL:price", timestamp, 195.30)

# Query aggregated data (5-min average)
data = client.ts().range("ts:AAPL:price", from_time, to_time, 
                         aggregation_type="avg", bucket_size_msec=300000)
```

#### Feature Pipeline (Streams)
```python
# Add feature computation job to stream
client.xadd("stream:feature_jobs", {
    "ticker": "AAPL",
    "feature_type": "technical",
    "timestamp": time.time()
})

# Consumer group processes jobs
client.xreadgroup("feature_workers", "worker1", 
                  {"stream:feature_jobs": ">"})
```

### Featureform Config
```yaml
# Featureform with Redis online store
redis:
  host: your-redis-host
  port: 6379
  db: 0

features:
  - name: rsi_14
    source: market_data
    transformation: compute_rsi
    online_store: redis
    
  - name: sentiment_score
    source: news_data
    transformation: sentiment_analysis
    online_store: redis
```

### Performance
- **Latency:** <1ms for feature retrieval
- **Throughput:** 100K+ features/sec
- **Features:** 100+ features per ticker

---

## 5️⃣ Quantization (Triggers & Alerts)

### Purpose
Real-time event detection and workflow automation

### How It Works
```
Market Event (price crosses threshold)
    ↓
Redis monitors Sorted Set or Stream
    ↓
Trigger detected
    ↓
Publish alert via Pub/Sub
    ↓
Agents receive and process
```

### Redis Components

#### Price Alerts (Sorted Sets)
```python
# Set price alert: "Alert when AAPL > 200"
client.zadd("alerts:price:AAPL:above", {
    "user123:200.00": 200.00
})

# Check alerts when price updates
current_price = 201.50
triggered = client.zrangebyscore("alerts:price:AAPL:above", 
                                 "-inf", current_price)
for alert in triggered:
    user_id, threshold = alert.split(":")
    client.publish(f"alerts:{user_id}", f"AAPL crossed ${threshold}")
```

#### Event Stream (Redis Streams)
```python
# Add market event
client.xadd("stream:market_events", {
    "type": "price_spike",
    "ticker": "AAPL",
    "change_pct": 5.2,
    "timestamp": time.time()
})

# Process events
while True:
    events = client.xreadgroup("event_processors", "worker1",
                               {"stream:market_events": ">"})
    for event in events:
        process_event(event)
```

#### Real-time Pub/Sub
```python
# Subscribe to alerts
pubsub = client.pubsub()
pubsub.subscribe("alerts:user123")

for message in pubsub.listen():
    send_notification(message["data"])
```

### Performance
- **Latency:** <1ms for event detection
- **Throughput:** 1M+ events/sec
- **Alerts:** 10K+ concurrent alerts

---

## 6️⃣ Tool Caching

### Purpose
Speed up agent workflows by caching tool outputs

### How It Works
```
Agent calls external API (e.g., Alpha Vantage)
    ↓
Check Redis cache
    ↓
    ├─→ [Cache hit] → Return cached result (95% of the time!)
    │
    └─→ [Cache miss] → Call API
                          ↓
                      Store result in Redis with TTL
```

### Redis Components
```python
# Cache API response
def get_market_data(ticker, use_cache=True):
    cache_key = f"api:market:{ticker}"
    
    if use_cache:
        cached = client.get(cache_key)
        if cached:
            return json.loads(cached)
    
    # Call external API
    data = alpha_vantage_api.get_quote(ticker)
    
    # Cache for 5 minutes
    client.setex(cache_key, 300, json.dumps(data))
    
    return data

# Cache sentiment analysis
def get_sentiment(text, use_cache=True):
    text_hash = hashlib.md5(text.encode()).hexdigest()
    cache_key = f"tool:sentiment:{text_hash}"
    
    cached = client.get(cache_key)
    if cached:
        return float(cached)
    
    sentiment = sentiment_model.predict(text)
    client.setex(cache_key, 3600, sentiment)  # 1 hour TTL
    
    return sentiment
```

### Performance
- **Hit Rate:** 95%+ for repeated queries
- **Latency:** <1ms cache access
- **Savings:** Avoid 95% of external API calls

---

## 7️⃣ Time-Series Data

### Purpose
Store and query OHLCV market data efficiently

### Redis Components

#### RedisTimeSeries Setup
```python
# Create time-series for AAPL OHLCV
for metric in ["open", "high", "low", "close", "volume"]:
    client.ts().create(
        f"ts:AAPL:{metric}",
        retention_msecs=31536000000,  # 1 year
        labels={"ticker": "AAPL", "metric": metric}
    )

# Add compaction rules (5-min, 1-hour, 1-day aggregates)
client.ts().createrule(
    "ts:AAPL:close",
    "ts:AAPL:close:5m",
    aggregation_type="avg",
    bucket_size_msec=300000
)
```

#### Ingestion
```python
# Ingest real-time data
def ingest_tick(ticker, price, volume, timestamp):
    client.ts().add(f"ts:{ticker}:price", timestamp, price)
    client.ts().add(f"ts:{ticker}:volume", timestamp, volume)

# Batch ingestion
def ingest_bars(ticker, bars):
    pipeline = client.pipeline()
    for bar in bars:
        pipeline.ts().add(f"ts:{ticker}:open", bar.timestamp, bar.open)
        pipeline.ts().add(f"ts:{ticker}:high", bar.timestamp, bar.high)
        pipeline.ts().add(f"ts:{ticker}:low", bar.timestamp, bar.low)
        pipeline.ts().add(f"ts:{ticker}:close", bar.timestamp, bar.close)
        pipeline.ts().add(f"ts:{ticker}:volume", bar.timestamp, bar.volume)
    pipeline.execute()
```

#### Querying
```python
# Get last 100 data points
data = client.ts().range(f"ts:AAPL:close", "-", "+", count=100)

# Get 5-minute aggregates for last 24 hours
start = int(time.time() * 1000) - 86400000
end = int(time.time() * 1000)
data = client.ts().range(
    f"ts:AAPL:close:5m",
    start, end
)

# Multi-series query (fetch multiple tickers)
data = client.ts().mrange(
    start, end,
    filters=["metric=close", "ticker=(AAPL|MSFT|GOOGL)"]
)
```

### Performance
- **Ingestion:** 1M+ points/sec
- **Query:** <10ms for 1K points
- **Compression:** 90%+ with compaction
- **Retention:** Years of data

---

## 🎯 Redis Configuration for FinagentiX

### Azure Managed Redis

> **Product Specification:**  
> - Service: **Azure Managed Redis** (`Microsoft.Cache/redisEnterprise`)  
> - ⚠️ **NOT** "Azure Cache for Redis" (`Microsoft.Cache/Redis`)  
> - Enterprise tier SKUs (E5, E10, E20, etc.) include: RediSearch, RedisTimeSeries, RedisJSON, RedisBloom  
> - "Azure Cache for Redis" lacks these critical modules

```yaml
Tier: Enterprise E10
Modules:
  - RediSearch (REQUIRED - vector search, full-text search)
  - RedisJSON (REQUIRED - complex objects)
  - RedisTimeSeries (REQUIRED - OHLCV market data)
  - RedisBloom (optional - probabilistic data structures)

Memory: 12 GB
Clustering: 2 shards
Replication: Active-Active
Persistence: AOF + RDB
TLS: 1.3
```

### Index Configuration
```python
# Semantic cache index
SEMANTIC_CACHE_INDEX = {
    "name": "idx:semantic_cache",
    "prefix": "cache:",
    "schema": [
        VectorField("query_embedding", "HNSW", {...}),
        TextField("query_text"),
        TextField("response"),
        NumericField("timestamp"),
        NumericField("usage_count")
    ]
}

# Document index
DOCUMENT_INDEX = {
    "name": "idx:documents",
    "prefix": "doc:",
    "schema": [
        VectorField("doc_embedding", "HNSW", {...}),
        TextField("doc_text"),
        TagField("ticker"),
        TagField("source"),
        NumericField("date")
    ]
}
```

---

## 📊 Expected Performance

| Component | Metric | Target |
|-----------|--------|--------|
| Semantic Cache | Hit Rate | 80-85% |
| Semantic Cache | Latency | <10ms |
| Agentic Memory | Retrieval | <1ms |
| RAG Retrieval | Latency | <10ms |
| Feature Serving | Latency | <1ms |
| Tool Caching | Hit Rate | 95%+ |
| Time-Series Ingest | Throughput | 1M+ points/sec |
| Alerts | Latency | <1ms |

---

## 🔗 Integration Points

### 1. **Agent ↔ Redis**
Agents use Redis for:
- Semantic routing decisions
- Context retrieval (memory)
- Feature fetching (Featureform)
- Tool output caching
- RAG document retrieval

### 2. **Featureform ↔ Redis**
Featureform uses Redis as:
- Online store for real-time features
- Stream processor for transformations
- Time-series storage for temporal features

### 3. **Azure OpenAI ↔ Redis**
Redis sits between agents and OpenAI:
- Cache LLM responses (LongCache)
- Store embeddings for similarity search
- Reduce API calls by 30-70%

---

**Document Version:** 1.0  
**Last Updated:** December 5, 2025
