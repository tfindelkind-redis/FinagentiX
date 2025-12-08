# Stock Data Ingestion

Robust stock market data downloader with validation, retry logic, and resume capability.

## Features

- **30 S&P 500 tickers** from diversified sectors (tech, finance, consumer, healthcare, industrial, energy)
- **1 year historical data** (daily OHLCV format)
- **Exponential backoff retry** (5 retries: 2s → 4s → 8s → 16s → 32s → 60s)
- **8-point data validation**:
  - OHLC relationship checks (High ≥ Low, Close/Open within range)
  - Null percentage validation (<5% threshold)
  - Completeness score (>90% required)
  - Extreme value detection (>50% daily change warnings)
  - Zero/negative price checks
  - Record count validation (>200 records)
  - Date range verification
  - MD5 checksum generation
- **Progress tracking** with `manifest.json`
- **Resume capability** for interrupted downloads
- **Background execution** support
- **Comprehensive logging** (file + console)

## Installation

```bash
# Install dependencies
pip install -r scripts/requirements.txt
```

## Usage

### Basic Usage

```bash
# Fresh download (all 30 tickers)
python scripts/download_stock_data.py

# Resume from previous run (skip completed tickers)
python scripts/download_stock_data.py --resume

# Download specific tickers
python scripts/download_stock_data.py --tickers AAPL MSFT GOOGL

# Enable debug logging
python scripts/download_stock_data.py --log-level DEBUG
```

### Background Execution

```bash
# Start download in background
nohup python scripts/download_stock_data.py > ingestion.out 2>&1 &
echo $! > ingestion.pid

# Monitor progress
tail -f ingestion.out

# Check status
cat data/raw/stock_data/manifest.json | jq '.entries | group_by(.status) | map({status: .[0].status, count: length})'

# View live file count
watch -n 5 'find data/raw/stock_data -name "*.parquet" | wc -l'

# Stop gracefully
kill $(cat ingestion.pid)
```

## Output Structure

```
data/raw/stock_data/
├── manifest.json                    # Progress tracking
├── AAPL/
│   ├── daily_1y.parquet            # OHLCV data (Snappy compressed)
│   ├── metadata.json               # Validation results
│   └── checksum.md5                # Data integrity hash
├── MSFT/
│   ├── daily_1y.parquet
│   ├── metadata.json
│   └── checksum.md5
└── ... (30 tickers total)
```

## manifest.json Format

```json
{
  "metadata": {
    "created_at": "2025-01-03T10:30:00Z",
    "updated_at": "2025-01-03T10:45:00Z"
  },
  "entries": [
    {
      "ticker": "AAPL",
      "status": "SUCCESS",
      "start_time": "2025-01-03T10:30:15Z",
      "end_time": "2025-01-03T10:30:22Z",
      "duration_seconds": 7.2,
      "file_path": "data/raw/stock_data/AAPL/daily_1y.parquet",
      "file_size_bytes": 15234,
      "record_count": 252,
      "completeness_score": 1.0,
      "null_percentage": 0.0,
      "checksum": "a1b2c3d4e5f6...",
      "error_message": null,
      "retry_count": 0
    }
  ]
}
```

## metadata.json Format

```json
{
  "ticker": "AAPL",
  "period": "1y",
  "interval": "1d",
  "download_timestamp": "2025-01-03T10:30:22Z",
  "record_count": 252,
  "date_range": ["2024-01-03", "2025-01-03"],
  "completeness_score": 1.0,
  "null_percentage": 0.0,
  "checksum": "a1b2c3d4e5f6...",
  "file_path": "data/raw/stock_data/AAPL/daily_1y.parquet",
  "file_size_bytes": 15234
}
```

## Monitoring Progress

### Quick Status Check
```bash
# Summary by status
cat data/raw/stock_data/manifest.json | jq '.entries | group_by(.status) | map({status: .[0].status, count: length})'

# List failed tickers
cat data/raw/stock_data/manifest.json | jq '.entries[] | select(.status=="FAILED") | .ticker'

# Calculate success rate
cat data/raw/stock_data/manifest.json | jq '[.entries[] | select(.status=="SUCCESS")] | length'
```

### Live Monitoring
```bash
# Watch progress in real-time
watch -n 5 'cat data/raw/stock_data/manifest.json | jq ".entries | group_by(.status) | map({status: .[0].status, count: length})"'

# Tail log file
tail -f logs/ingestion_*.log | grep -E "(Processing|Successfully|ERROR)"
```

## Configuration

Edit `scripts/ingestion/config.py` to customize:

- **Tickers**: Modify `tickers` list (default: 30 S&P 500 stocks)
- **Period**: Change `period` (default: "1y", options: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
- **Interval**: Change `interval` (default: "1d", options: "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo")
- **Retry settings**: Adjust `max_retries` and `retry_delays`
- **Validation thresholds**: Modify `validation_thresholds` dict

## Expected Performance

- **Duration**: 15-30 minutes for 30 tickers (with 1s rate limiting + retries)
- **Data size**: ~50-100MB total (compressed Parquet)
- **Success rate**: ~95-100% (Yahoo Finance API reliability)

## Troubleshooting

### No data returned
- Check internet connection
- Verify ticker symbols are valid
- Check Yahoo Finance API status

### Validation failures
- Review `logs/ingestion_*.log` for specific issues
- Check `manifest.json` for error messages
- Inspect failed ticker data manually

### Resume not working
- Ensure `manifest.json` exists
- Check file permissions on `data/` directory
- Use `--fresh` to start over if corrupted

## Next Steps

1. **Test with subset**: `python scripts/download_stock_data.py --tickers AAPL MSFT GOOGL`
2. **Run full download**: `python scripts/download_stock_data.py`
3. **Commit to repo**: `git add data/raw/stock_data/ && git commit -m "Add historical stock data"`
4. **Upload to Azure**: Use `scripts/upload_to_azure.py` (to be created)
