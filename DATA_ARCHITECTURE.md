# Data Ingestion & Metadata Architecture

## Overview

FinagentiX uses a **two-layer data architecture** that separates cold storage (Azure Blob Storage) from hot metadata indexing (Redis). This approach enables fast semantic search over datasets while maintaining cost-effective storage for large historical data.

---

## Architecture Layers

### Layer 1: Cold Storage (Azure Blob Storage)
**Purpose**: Persistent storage for raw and processed financial data

```
stock-data/                          # Container
├── AAPL/                            # Ticker-based partitioning
│   ├── 1d/                          # Interval (daily)
│   │   └── 2025/                    # Year
│   │       └── 12/                  # Month
│   │           └── 05.parquet       # Day (with blob metadata)
│   └── 5m/                          # 5-minute intervals
│       └── 2025/12/05.parquet
├── MSFT/...
├── GOOGL/...
└── manifest.json                    # Central data catalog
```

**Blob Metadata** (Azure native, stored with each file):
```json
{
  "ticker": "AAPL",
  "data_type": "ohlcv",
  "interval": "1d",
  "record_count": "1256",
  "start_date": "2020-12-07",
  "end_date": "2025-12-05",
  "source": "yahoo_finance",
  "ingestion_time": "2025-12-08T07:00:00Z",
  "completeness_score": "100.0",
  "schema_version": "1.0",
  "checksum": "abc123def456"
}
```

**Benefits**:
- Cost-effective storage for large datasets
- Built-in metadata filtering
- Hierarchical partitioning for efficient queries
- Data integrity via checksums

---

### Layer 2: Hot Index (Redis)
**Purpose**: Fast metadata search and semantic discovery

#### Redis JSON Documents
Each dataset stored as a rich JSON document:
```json
{
  "dataset_id": "AAPL_1d_2025_12_05",
  "blob_path": "AAPL/1d/2025/12/05.parquet",
  "description": "AAPL stock price data with 1d intervals from 2020-12-07 to 2025-12-05...",
  
  "ticker": "AAPL",
  "interval": "1d",
  "source": "yahoo_finance",
  "asset_class": "equity",
  "market": "us",
  
  "record_count": 1256,
  "file_size_bytes": 52428,
  "completeness_score": 100.0,
  
  "start_timestamp": 1607299200,
  "end_timestamp": 1733356800,
  "ingestion_timestamp": 1733644800,
  
  "description_vector": [0.234, 0.456, ...],  // 1536-dim embedding
  
  "columns": ["Open", "High", "Low", "Close", "Volume"],
  "schema_version": "1.0",
  "quality_checks": {
    "has_duplicates": false,
    "price_anomalies": false
  }
}
```

#### RediSearch Index
Full-text and field-based search capabilities:
```python
# Index schema
- TextField: description (searchable text)
- TagField: ticker, interval, source, asset_class
- NumericField: record_count, file_size_bytes, timestamps, completeness_score
- VectorField: description_vector (HNSW, 1536 dimensions, COSINE)
```

**Benefits**:
- Sub-millisecond metadata queries
- No need to scan Azure Storage
- Rich filtering and aggregation
- Foundation for semantic search

---

## Data Ingestion Pipeline

### Step 1: Download from Yahoo Finance
```python
# Using yfinance library
stock = yf.Ticker("AAPL")
df = stock.history(period="5y", interval="1d")
```

**Available Data**:
- **Historical**: Up to max available (e.g., AAPL since 1980)
- **Intervals**: 1m, 5m, 1h, 1d
- **OHLCV**: Open, High, Low, Close, Volume, Dividends, Stock Splits
- **Fundamentals**: Income statement, balance sheet, cash flow
- **News**: Recent articles (10+ per ticker)

### Step 2: Store in Azure Blob Storage
```python
# Convert to Parquet format (efficient columnar storage)
parquet_data = df.to_parquet(compression="snappy")

# Generate partitioned path
blob_path = f"{ticker}/{interval}/{year}/{month:02d}/{day:02d}.parquet"

# Create comprehensive metadata
metadata = {
    "ticker": ticker,
    "record_count": str(len(df)),
    "start_date": df.index[0].strftime("%Y-%m-%d"),
    "end_date": df.index[-1].strftime("%Y-%m-%d"),
    "ingestion_time": datetime.utcnow().isoformat(),
    "completeness_score": str(completeness),
    "checksum": md5_hash,
    # ... more fields
}

# Upload with metadata
blob_client.upload_blob(
    parquet_data,
    metadata=metadata,
    content_settings=ContentSettings(content_type="application/octet-stream")
)
```

### Step 3: Index in Redis
```python
# Generate description for semantic search
description = (
    f"{ticker} stock price data with {interval} intervals "
    f"from {start_date} to {end_date}, containing {records} records. "
    f"Includes OHLCV data for financial analysis."
)

# Generate embedding using Azure OpenAI
embedding = openai.embeddings.create(
    model="text-embedding-3-large",
    input=description
).data[0].embedding

# Store in Redis JSON with vector
redis.json().set(f"dataset:{dataset_id}", "$", {
    "blob_path": blob_path,
    "description": description,
    "description_vector": embedding,
    "ticker": ticker,
    # ... all metadata fields
})
```

### Step 4: Update Manifest
```python
manifest = {
    "version": "1.0",
    "generated_at": datetime.utcnow().isoformat(),
    "total_files": len(files),
    "files": [
        {
            "blob_path": "AAPL/1d/2025/12/05.parquet",
            "checksum": "abc123",
            "metadata": {...},
            "quality_checks": {...}
        }
    ],
    "statistics": {
        "total_records": 6280,
        "total_size_bytes": 262144,
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "date_range": {
            "earliest": "2020-12-07",
            "latest": "2025-12-05"
        }
    }
}

# Store manifest in Azure Storage
blob_client.upload_blob("manifest.json", json.dumps(manifest))
```

---

## Search & Query Patterns

### 1. Ticker-Based Search
**Use Case**: "What Apple data do we have?"

```python
# Redis query
results = redis.ft("idx:datasets").search(
    Query("@ticker:{AAPL}").return_fields("blob_path", "record_count")
)
```

**Returns**: All AAPL datasets with paths and record counts

---

### 2. Date Range Query
**Use Case**: "Find data from Q4 2024"

```python
start_ts = datetime(2024, 10, 1).timestamp()
end_ts = datetime(2024, 12, 31).timestamp()

results = redis.ft("idx:datasets").search(
    Query(f"@start_timestamp:[{start_ts} {end_ts}]")
)
```

**Returns**: Datasets with data in that time period

---

### 3. Semantic Search (Vector Similarity)
**Use Case**: "Find recent volatility data" (natural language)

```python
# 1. Generate query embedding
query_embedding = openai.embeddings.create(
    model="text-embedding-3-large",
    input="recent volatility data"
).data[0].embedding

# 2. KNN vector search in Redis
query_vector = np.array(query_embedding, dtype=np.float32).tobytes()

results = redis.ft("idx:datasets").search(
    Query("*=>[KNN 5 @description_vector $vec AS score]")
        .sort_by("score")
        .dialect(2),
    query_params={"vec": query_vector}
)
```

**Returns**: Top 5 semantically similar datasets

---

### 4. Hybrid Search
**Use Case**: "TSLA intraday data from last week"

```python
# Combine filters + vector search
results = redis.ft("idx:datasets").search(
    Query("@ticker:{TSLA} @interval:{5m}=>[KNN 10 @description_vector $vec]")
        .dialect(2),
    query_params={"vec": query_embedding}
)
```

**Returns**: TSLA 5-minute data, ranked by semantic relevance

---

## Agent Integration

### Market Data Agent Workflow

```python
# Agent receives user query
user_query = "Show me Apple's price trend for last year"

# 1. Generate embedding of query
query_embedding = generate_embedding(user_query)

# 2. Search Redis metadata index
datasets = redis_catalog.semantic_search(
    query_embedding=query_embedding,
    filters={"ticker": "AAPL", "interval": "1d"},
    top_k=1
)

# 3. Get blob path from result
blob_path = datasets[0]["blob_path"]  # "AAPL/1d/2025/12/05.parquet"

# 4. Fetch actual data from Azure Storage (only when needed)
blob_client = storage.get_blob_client("stock-data", blob_path)
parquet_data = blob_client.download_blob().readall()
df = pd.read_parquet(BytesIO(parquet_data))

# 5. Perform analysis and return to user
trend = calculate_trend(df)
return trend
```

**Performance**:
- Redis metadata search: **< 10ms**
- Azure blob download: **100-500ms** (only when data needed)
- Total: **< 1 second** for full data retrieval + analysis

---

## Metadata Best Practices

### 1. Data Lineage
Track the origin and processing of each dataset:
- **source**: yahoo_finance, polygon.io, etc.
- **ingestion_script**: stock_data_ingestion.py
- **ingestion_version**: 1.0.0
- **ingestion_time**: 2025-12-08T07:00:00Z

### 2. Data Quality
Monitor and track quality metrics:
- **completeness_score**: % of non-null values
- **has_nulls**: Boolean flag
- **quality_checks**: Duplicates, anomalies, gaps
- **data_age_hours**: Freshness indicator

### 3. Schema Versioning
Handle schema evolution:
- **schema_version**: 1.0
- **columns**: List of column names
- **data_type**: ohlcv, fundamentals, news

### 4. Data Integrity
Ensure data hasn't been corrupted:
- **checksum**: MD5 hash of file contents
- **file_size_bytes**: Expected size

### 5. Business Context
Add domain-specific metadata:
- **asset_class**: equity, bond, commodity
- **market**: us, eu, asia
- **currency**: usd, eur, jpy

---

## Benefits Summary

| Feature | Without Redis Index | With Redis Index |
|---------|-------------------|-----------------|
| **Dataset Discovery** | Scan all blobs | < 10ms semantic search |
| **Filtering** | Download & check | Instant tag/field filters |
| **Natural Language** | Not possible | Vector similarity search |
| **Query Cost** | High (storage egress) | Low (metadata only) |
| **Agent Speed** | Slow (must scan) | Fast (pre-indexed) |

---

## Future Enhancements

### 1. Real-Time Data Streaming
- Ingest market data via WebSocket/Kafka
- Update Redis index in real-time
- Store in Redis TimeSeries for instant access

### 2. Automated Quality Monitoring
- Scheduled quality checks on datasets
- Alert on anomalies or missing data
- Track quality trends over time

### 3. Data Versioning
- Store multiple versions of same dataset
- Track schema migrations
- Enable rollback to previous versions

### 4. Multi-Source Aggregation
- Combine data from Yahoo Finance, Polygon, Bloomberg
- Resolve conflicts and merge
- Track source reliability

### 5. Incremental Updates
- Only download new data (not full history)
- Append to existing Parquet files
- Update Redis index incrementally

---

## Implementation Checklist

- [ ] Set up Azure Storage Account with containers
- [ ] Deploy Azure Managed Redis (Balanced_B5)
- [ ] Install Python dependencies (yfinance, azure-storage-blob, redis)
- [ ] Implement data ingestion script
- [ ] Create RediSearch index with vector field
- [ ] Generate embeddings using Azure OpenAI
- [ ] Build manifest file generator
- [ ] Implement search functions (ticker, date, semantic, hybrid)
- [ ] Create data quality validators
- [ ] Set up scheduled ingestion jobs (Container Apps)
- [ ] Build agent integration layer
- [ ] Add monitoring and alerts

---

## Related Files

- `scripts/evaluate_yahoo_finance.py` - Data source evaluation
- `scripts/stock_data_ingestion.py` - Full ingestion pipeline with metadata
- `scripts/redis_metadata_index.py` - Redis indexing and search
- `infra/stages/stage1a-storage-only.bicep` - Azure Storage deployment
- `infra/stages/stage1b-redis-only.bicep` - Azure Managed Redis deployment
