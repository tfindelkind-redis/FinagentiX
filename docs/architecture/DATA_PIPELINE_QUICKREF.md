# Data Pipeline Quick Reference

## 📊 Data Sources & Update Frequency

| Source | Type | Update Frequency | Storage | Purpose |
|--------|------|-----------------|---------|---------|
| **Polygon.io WebSocket** | Real-time | Continuous | RedisTimeSeries | Live prices, trades |
| **Alpha Vantage** | REST API | Every 1 min | RedisTimeSeries | OHLCV bars |
| **NewsAPI** | REST API | Every 5 min | Redis Hashes + Streams | News articles |
| **Twitter/Reddit** | REST API | Every 2 min | Redis Hashes + Streams | Social sentiment |
| **SEC EDGAR** | REST API | Every 1 hour | Azure Blob + RediSearch | 10-K/Q filings |
| **Earnings Transcripts** | Web Scraping | Daily | Azure Blob + RediSearch | Earnings calls |

---

## 🔄 Data Flow Summary

### 1. **Real-Time Flow** (Milliseconds)
```
Polygon WebSocket → Redis Streams → RedisTimeSeries → Featureform → Agents
```

### 2. **Batch Flow** (Minutes)
```
API Call → Redis Streams → Processing Worker → Redis Storage → Featureform
```

### 3. **Document Flow** (Hours)
```
SEC EDGAR → Azure Blob → Chunking → Embedding → RediSearch → RAG
```

---

## 🗂️ Storage Strategy

### Hot Storage (Redis) - 7 days to 90 days
- **RedisTimeSeries:** Tick data, OHLCV bars
- **RediSearch HNSW:** Document embeddings, semantic cache
- **Redis Hashes:** News, features, metadata
- **Redis Streams:** Processing queues
- **RedisJSON:** User profiles, portfolio state

### Warm Storage (Azure Blob) - 2 years
- Historical daily bars
- Full SEC filings (raw)
- Archived news

### Cold Storage (Azure Archive) - 7+ years
- Compliance data
- Audit logs

---

## 🚀 Services Overview

### Real-Time Services (Always Running)
1. **market_data_streamer.py** - WebSocket connection to Polygon
2. **stream_processors/** - 5 workers processing Redis Streams

### Scheduled Services (Cron/APScheduler)
1. **market_data_fetcher.py** - Every 1 min (OHLCV bars)
2. **news_scraper.py** - Every 5 min (News articles)
3. **social_media_collector.py** - Every 2 min (Twitter/Reddit)
4. **sec_filings_fetcher.py** - Every 1 hour (SEC filings)
5. **earnings_transcripts_scraper.py** - Daily (Earnings calls)

### On-Demand Services
1. **historical_data_backfiller.py** - Initial data load

---

## 📈 Scalability

| Component | Current | Scale To | Method |
|-----------|---------|----------|--------|
| Tickers | 100 | 1,000+ | Add more WebSocket connections |
| Stream Workers | 5 | 20+ | Kubernetes horizontal scaling |
| Redis Memory | 12GB | 50GB+ | Upgrade to E20 tier |
| Processing Rate | 10K/sec | 100K/sec | More consumer groups |

---

## 🔧 Key Configuration Files

```
services/
├── ingestion/
│   ├── market_data_streamer.py      # Real-time WebSocket
│   ├── market_data_fetcher.py       # Scheduled OHLCV fetch
│   ├── news_scraper.py              # News ingestion
│   ├── social_media_collector.py    # Twitter/Reddit
│   ├── sec_filings_fetcher.py       # SEC filings
│   └── historical_data_backfiller.py # Backfill historical
│
├── processing/
│   ├── market_data_processor.py     # Process market data
│   ├── news_processor.py            # Sentiment analysis
│   ├── document_processor.py        # Chunking + embedding
│   └── feature_engineer.py          # Compute features
│
└── config/
    ├── data_sources.yaml            # Data source config
    ├── tickers.txt                  # Ticker list
    └── schedules.yaml               # Cron schedules
```

---

## 🎯 Quick Start Commands

### Deploy All Services
```bash
# Deploy to Kubernetes
kubectl apply -f k8s/ingestion/
kubectl apply -f k8s/processing/
```

### Run Historical Backfill
```bash
# Backfill 2 years of data for 100 tickers
python services/ingestion/historical_data_backfiller.py \
  --tickers-file config/tickers.txt \
  --years 2 \
  --parallel 10
```

### Monitor Pipeline
```bash
# Check stream queue sizes
redis-cli XLEN stream:raw_market_data
redis-cli XLEN stream:raw_news
redis-cli XLEN stream:raw_documents

# Check RedisTimeSeries
redis-cli TS.INFO ts:AAPL:price

# Check processing lag
kubectl logs -f deployment/stream-processors
```

### Test Individual Services
```bash
# Test market data fetcher
python services/ingestion/market_data_fetcher.py --test --ticker AAPL

# Test news scraper
python services/ingestion/news_scraper.py --test --ticker MSFT
```

---

## 🔍 Troubleshooting

### Issue: Stream Queue Growing
```bash
# Check consumer lag
redis-cli XPENDING stream:raw_market_data processing_group

# Scale up workers
kubectl scale deployment stream-processors --replicas=10
```

### Issue: API Rate Limits
```python
# Adjust rate limiting in config
rate_limit:
  alpha_vantage: 5  # calls per minute
  newsapi: 100      # calls per day
```

### Issue: High Redis Memory
```bash
# Check memory usage by key pattern
redis-cli --bigkeys

# Adjust TTLs in code
redis_client.setex(key, ttl=86400)  # 1 day instead of 7
```

---

**See [DATA_PIPELINE.md](./DATA_PIPELINE.md) for complete details**
