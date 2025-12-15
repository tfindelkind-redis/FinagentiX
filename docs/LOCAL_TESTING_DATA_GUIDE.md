# Local Testing Guide

## Quick Answer: "What about the data?"

The agents need **market data in Redis TimeSeries** format to work. Your plugins read from Redis, not external APIs. Here are your options:

## Data Options

### Option A: Sample Data (5 minutes) ⭐ RECOMMENDED FOR FIRST TEST

**Pros:**
- No external dependencies
- Fast setup
- Works offline
- Perfect for testing agent logic

**Setup:**
```bash
# 1. Install and start Redis locally
brew install redis
redis-server &

# 2. Load sample data
python setup_local_testing.py

# 3. Start server
./start_server.sh
```

**What you get:**
- 7 tickers: AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META
- 30 days of OHLCV data
- Realistic price variations
- ~1,050 data points total

### Option B: Real Data with yfinance (30 minutes)

**Pros:**
- Real historical market data
- Free, no API key needed
- More realistic testing

**Setup:**
```bash
# 1. Create data ingestion script (see below)
python ingest_market_data.py --tickers AAPL,MSFT,GOOGL --days 365

# 2. Start server
./start_server.sh
```

**What you get:**
- Real Yahoo Finance data
- Configurable tickers
- 1-5 years of history
- Actual market events

### Option C: Azure Redis (When network is fixed)

**Pros:**
- Production data
- Already configured

**Cons:**
- Current network connectivity issue
- Needs VPN/firewall fix

**Setup:**
```bash
# In .env, use Azure Redis:
REDIS_HOST=redis-<RESOURCE_ID>.eastus.redis.azure.net
REDIS_PORT=10000
REDIS_PASSWORD=<your-redis-access-key>
```

## How Data Flows

```
┌──────────────────────────────────────────────────────────┐
│                    Data Ingestion                         │
│  (One-time setup - populates Redis)                       │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  yfinance/NewsAPI/SEC     → Redis TimeSeries              │
│  (External sources)          (Persistent storage)         │
│                                                            │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                    Agent Runtime                           │
│  (Your testing - reads from Redis)                        │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  market_data_plugin.py    → Redis TimeSeries              │
│  (Reads stock prices)        (Fast in-memory lookup)      │
│                                                            │
│  NO direct API calls!                                      │
│                                                            │
└──────────────────────────────────────────────────────────┘
```

## Redis Data Format

Your plugins expect data in this format:

```python
# Keys:
stock:AAPL:open      # Opening prices
stock:AAPL:high      # Daily highs
stock:AAPL:low       # Daily lows
stock:AAPL:close     # Closing prices
stock:AAPL:volume    # Trading volumes

# Commands used by plugins:
TS.GET stock:AAPL:close                    # Latest price
TS.RANGE stock:AAPL:close - +              # All historical data
TS.RANGE stock:AAPL:close 1640000000000 +  # Since timestamp
```

## Testing Workflow

### 1. Setup (One-time)
```bash
# Option A: Sample data
python setup_local_testing.py

# Option B: Real data
python ingest_market_data.py --tickers AAPL,MSFT --days 365
```

### 2. Start Server
```bash
./start_server.sh
```

### 3. Verify Data
```bash
# Check Redis has data
redis-cli
> KEYS stock:*
> TS.GET stock:AAPL:close

# Or use the API
curl http://localhost:8000/api/redis/status
```

### 4. Test Agents

**CLI:**
```bash
python cli.py "What's the current price of AAPL?"
python cli.py "Should I invest in AAPL?"
python cli.py "Compare AAPL and MSFT performance"
```

**API:**
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the price of AAPL?",
    "workflow_type": "direct"
  }'
```

### 5. Test RAG/Documents

**Ingest sample SEC filing:**
```bash
python ingest_sec_filing.py --ticker AAPL --sample
```

**Ask questions:**
```bash
python cli.py "/ask What are the key risks mentioned in AAPL's filing?"
```

## Current Azure Resources

You already have these deployed and configured:

| Resource | Status | Purpose |
|----------|--------|---------|
| **Azure OpenAI** | ✅ Working | LLM for agent responses |
| **Azure Redis Enterprise** | ❌ Network issue | Production data store |
| **Azure Storage** | ✅ Working | File storage |

**For local testing:** Use local Redis + Azure OpenAI (works fine!)

## What's Missing for Production

- [ ] Azure Redis network access (VPN/firewall)
- [ ] Container image build (Docker)
- [ ] Deploy Stage 4 (Agent Runtime on Container Apps)
- [ ] Production data ingestion pipeline
- [ ] Monitoring and alerting

## Recommended Path

**For your first test** (TODAY):
1. ✅ Run `python setup_local_testing.py` (sample data)
2. ✅ Run `./start_server.sh`
3. ✅ Test with `python cli.py "What's AAPL's price?"`
4. ✅ Verify all 4 workflows work
5. ✅ Test RAG with sample filing

**For comprehensive testing** (TOMORROW):
1. Build real data ingestion with yfinance
2. Load 1 year of data for 30 tickers
3. Run full workflow tests
4. Test caching/routing/memory features

**For production deployment** (NEXT WEEK):
1. Fix Azure Redis network access
2. Build container image: `docker build -t finagentix/agent-api .`
3. Push to ACR
4. Deploy Stage 4: `./infra/scripts/deploy-stage.sh 4`
5. Test production environment

## External API Usage

**Currently using:**
- ✅ Azure OpenAI (already working)
- ❌ No market data APIs in runtime code

**Available for data ingestion:**
- yfinance (free, no key needed)
- NewsAPI (free tier, 100 req/day)
- SEC EDGAR (free, 10 req/sec)

**Key insight:** Agents read from Redis, don't call external APIs. This is by design for performance and cost control.

## Need Help?

- Setup issues: `python setup_local_testing.py` shows diagnostics
- Server won't start: Check `./start_server.sh` output
- No data: `redis-cli KEYS stock:*` should show keys
- Connection issues: Check `.env` has `REDIS_HOST=localhost`
