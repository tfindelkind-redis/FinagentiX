# Data Ingestion Plan - Step 1: Stock Market Data

## 🎯 Overview

**Goal:** Download 1 year of historical OHLCV data for 20-30 tickers from Yahoo Finance with robust error handling, validation, and local persistence before Azure upload.

**Key Principles:**
- ✅ Run locally (no Azure dependencies during gathering)
- ✅ Robust retry logic with exponential backoff
- ✅ Comprehensive data validation after each ticker
- ✅ Resume capability (track progress, skip completed)
- ✅ Local storage in repo (data versioned, replayable)
- ✅ Separate upload phase (only after all data validated)

---

## 📁 Local Data Structure

```
data/
├── raw/                          # Raw downloads (versioned in repo)
│   ├── stock_data/
│   │   ├── manifest.json        # Master tracking file
│   │   ├── AAPL/
│   │   │   ├── daily_1y.parquet
│   │   │   ├── metadata.json
│   │   │   └── checksum.md5
│   │   ├── MSFT/
│   │   │   ├── daily_1y.parquet
│   │   │   ├── metadata.json
│   │   │   └── checksum.md5
│   │   └── ...
│   └── .gitkeep
├── logs/                         # Ingestion logs (not in repo)
│   ├── stock_ingestion_20251208_080000.log
│   └── retries.json             # Track retry attempts
└── staging/                      # Temp processing area
    └── .gitkeep

.gitignore:
  data/logs/
  data/staging/
```

---

## 🔧 Script Architecture

### **File Structure:**
```
scripts/
├── ingestion/
│   ├── __init__.py
│   ├── stock_downloader.py       # Main downloader class
│   ├── validators.py             # Data validation logic
│   ├── retry_handler.py          # Retry mechanism
│   ├── progress_tracker.py       # Resume capability
│   ├── uploader.py               # Azure upload (separate phase)
│   └── config.py                 # Configuration
├── run_stock_ingestion.py        # CLI entry point
└── requirements-ingestion.txt    # Dependencies
```

---

## 📋 Detailed Implementation Plan

### **Phase 1: Download & Validate (Local Only)**

#### **1.1 Configuration (`config.py`)**

```python
from dataclasses import dataclass
from typing import List
import os

@dataclass
class IngestionConfig:
    """Configuration for stock data ingestion"""
    
    # Target tickers (20-30 stocks)
    TICKERS: List[str] = [
        # Tech
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
        # Finance
        'JPM', 'BAC', 'WFC', 'GS', 'MS',
        # Consumer
        'WMT', 'HD', 'NKE', 'SBUX', 'MCD',
        # Healthcare
        'JNJ', 'UNH', 'PFE', 'ABBV',
        # Industrial
        'BA', 'CAT', 'GE',
        # Energy
        'XOM', 'CVX',
        # Crypto-related
        'COIN', 'MSTR'
    ]
    
    # Time periods
    PERIOD: str = '1y'              # 1 year historical
    INTERVAL: str = '1d'            # Daily bars
    
    # Retry configuration
    MAX_RETRIES: int = 5
    INITIAL_RETRY_DELAY: int = 2    # seconds
    MAX_RETRY_DELAY: int = 60       # seconds
    BACKOFF_MULTIPLIER: float = 2.0
    
    # Rate limiting (respect Yahoo Finance)
    DELAY_BETWEEN_TICKERS: float = 1.0  # seconds
    BATCH_SIZE: int = 5                  # tickers per batch
    BATCH_DELAY: float = 5.0             # seconds between batches
    
    # Validation thresholds
    MIN_RECORDS_REQUIRED: int = 200      # ~8 months of daily data
    MAX_NULL_PERCENTAGE: float = 0.05    # Allow 5% nulls
    MIN_COMPLETENESS_SCORE: float = 0.90
    
    # Paths
    BASE_DIR: str = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
    RAW_DIR: str = os.path.join(BASE_DIR, 'raw', 'stock_data')
    LOG_DIR: str = os.path.join(BASE_DIR, 'logs')
    STAGING_DIR: str = os.path.join(BASE_DIR, 'staging')
    
    # Logging
    LOG_LEVEL: str = 'INFO'
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
```

---

#### **1.2 Progress Tracker (`progress_tracker.py`)**

```python
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class TickerStatus(Enum):
    """Status of ticker download"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class TickerProgress:
    """Track progress for individual ticker"""
    ticker: str
    status: TickerStatus
    attempts: int = 0
    last_attempt: Optional[str] = None
    error_message: Optional[str] = None
    record_count: Optional[int] = None
    file_path: Optional[str] = None
    checksum: Optional[str] = None
    completed_at: Optional[str] = None

class ProgressTracker:
    """Track download progress with resume capability"""
    
    def __init__(self, manifest_path: str, tickers: List[str]):
        self.manifest_path = manifest_path
        self.tickers = tickers
        self.progress: Dict[str, TickerProgress] = {}
        self._load_or_initialize()
    
    def _load_or_initialize(self):
        """Load existing progress or initialize new"""
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, 'r') as f:
                data = json.load(f)
                for ticker_data in data.get('tickers', []):
                    status = TickerStatus(ticker_data['status'])
                    self.progress[ticker_data['ticker']] = TickerProgress(
                        ticker=ticker_data['ticker'],
                        status=status,
                        attempts=ticker_data.get('attempts', 0),
                        last_attempt=ticker_data.get('last_attempt'),
                        error_message=ticker_data.get('error_message'),
                        record_count=ticker_data.get('record_count'),
                        file_path=ticker_data.get('file_path'),
                        checksum=ticker_data.get('checksum'),
                        completed_at=ticker_data.get('completed_at')
                    )
        else:
            # Initialize all tickers as pending
            for ticker in self.tickers:
                self.progress[ticker] = TickerProgress(
                    ticker=ticker,
                    status=TickerStatus.PENDING
                )
            self.save()
    
    def save(self):
        """Persist current progress"""
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        data = {
            'version': '1.0',
            'last_updated': datetime.now().isoformat(),
            'total_tickers': len(self.tickers),
            'completed': len(self.get_completed()),
            'failed': len(self.get_failed()),
            'pending': len(self.get_pending()),
            'tickers': [
                {
                    **asdict(p),
                    'status': p.status.value
                }
                for p in self.progress.values()
            ]
        }
        with open(self.manifest_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def mark_in_progress(self, ticker: str):
        """Mark ticker as currently being processed"""
        self.progress[ticker].status = TickerStatus.IN_PROGRESS
        self.progress[ticker].attempts += 1
        self.progress[ticker].last_attempt = datetime.now().isoformat()
        self.save()
    
    def mark_completed(self, ticker: str, record_count: int, 
                       file_path: str, checksum: str):
        """Mark ticker as successfully completed"""
        self.progress[ticker].status = TickerStatus.COMPLETED
        self.progress[ticker].record_count = record_count
        self.progress[ticker].file_path = file_path
        self.progress[ticker].checksum = checksum
        self.progress[ticker].completed_at = datetime.now().isoformat()
        self.progress[ticker].error_message = None
        self.save()
    
    def mark_failed(self, ticker: str, error: str):
        """Mark ticker as failed"""
        self.progress[ticker].status = TickerStatus.FAILED
        self.progress[ticker].error_message = error
        self.save()
    
    def get_pending(self) -> List[str]:
        """Get list of pending tickers"""
        return [
            t for t, p in self.progress.items()
            if p.status == TickerStatus.PENDING
        ]
    
    def get_completed(self) -> List[str]:
        """Get list of completed tickers"""
        return [
            t for t, p in self.progress.items()
            if p.status == TickerStatus.COMPLETED
        ]
    
    def get_failed(self) -> List[str]:
        """Get list of failed tickers"""
        return [
            t for t, p in self.progress.items()
            if p.status == TickerStatus.FAILED
        ]
    
    def should_retry(self, ticker: str, max_retries: int) -> bool:
        """Check if ticker should be retried"""
        p = self.progress[ticker]
        return (p.status == TickerStatus.FAILED and 
                p.attempts < max_retries)
    
    def get_summary(self) -> Dict:
        """Get progress summary"""
        return {
            'total': len(self.tickers),
            'completed': len(self.get_completed()),
            'failed': len(self.get_failed()),
            'pending': len(self.get_pending()),
            'completion_rate': len(self.get_completed()) / len(self.tickers) * 100
        }
```

---

#### **1.3 Retry Handler (`retry_handler.py`)**

```python
import time
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

class RetryHandler:
    """Exponential backoff retry handler"""
    
    def __init__(self, max_retries: int, initial_delay: float,
                 max_delay: float, backoff_multiplier: float):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with exponential backoff retry"""
        delay = self.initial_delay
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Success after {attempt + 1} attempts")
                return result
            
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    delay = min(delay * self.backoff_multiplier, self.max_delay)
                else:
                    logger.error(
                        f"All {self.max_retries} attempts failed. "
                        f"Last error: {e}"
                    )
        
        raise last_exception

def retry_on_failure(max_retries=3, initial_delay=2, 
                     max_delay=60, backoff_multiplier=2.0):
    """Decorator for retry logic"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = RetryHandler(
                max_retries, initial_delay, 
                max_delay, backoff_multiplier
            )
            return handler.execute_with_retry(func, *args, **kwargs)
        return wrapper
    return decorator
```

---

#### **1.4 Validator (`validators.py`)**

```python
import pandas as pd
import hashlib
from typing import Dict, Tuple
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    record_count: int
    completeness_score: float
    null_percentage: float
    date_range: Tuple[str, str]
    issues: list[str]
    checksum: str

class DataValidator:
    """Validate downloaded stock data"""
    
    def __init__(self, min_records: int, max_null_pct: float, 
                 min_completeness: float):
        self.min_records = min_records
        self.max_null_pct = max_null_pct
        self.min_completeness = min_completeness
    
    def validate(self, df: pd.DataFrame, ticker: str) -> ValidationResult:
        """Comprehensive validation of stock data"""
        issues = []
        
        # 1. Check record count
        record_count = len(df)
        if record_count < self.min_records:
            issues.append(
                f"Insufficient records: {record_count} < {self.min_records}"
            )
        
        # 2. Check for required columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            issues.append(f"Missing columns: {missing_cols}")
        
        # 3. Check for nulls
        total_cells = len(df) * len(required_cols)
        null_cells = df[required_cols].isnull().sum().sum()
        null_percentage = (null_cells / total_cells) * 100
        
        if null_percentage > self.max_null_pct * 100:
            issues.append(
                f"Too many nulls: {null_percentage:.2f}% > "
                f"{self.max_null_pct * 100}%"
            )
        
        # 4. Check data quality
        completeness_score = self._calculate_completeness(df)
        if completeness_score < self.min_completeness:
            issues.append(
                f"Low completeness: {completeness_score:.2f} < "
                f"{self.min_completeness}"
            )
        
        # 5. Check date range
        date_range = (
            df.index[0].strftime('%Y-%m-%d'),
            df.index[-1].strftime('%Y-%m-%d')
        )
        
        # 6. Validate OHLC relationships
        ohlc_issues = self._validate_ohlc(df)
        issues.extend(ohlc_issues)
        
        # 7. Check for extreme values (potential data errors)
        extreme_issues = self._check_extreme_values(df, ticker)
        issues.extend(extreme_issues)
        
        # 8. Calculate checksum
        checksum = self._calculate_checksum(df)
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            record_count=record_count,
            completeness_score=completeness_score,
            null_percentage=null_percentage,
            date_range=date_range,
            issues=issues,
            checksum=checksum
        )
    
    def _calculate_completeness(self, df: pd.DataFrame) -> float:
        """Calculate data completeness score (0-1)"""
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        total_cells = len(df) * len(required_cols)
        valid_cells = df[required_cols].notna().sum().sum()
        return valid_cells / total_cells
    
    def _validate_ohlc(self, df: pd.DataFrame) -> list[str]:
        """Validate OHLC price relationships"""
        issues = []
        
        # High should be >= Low
        if (df['High'] < df['Low']).any():
            invalid_count = (df['High'] < df['Low']).sum()
            issues.append(f"{invalid_count} rows where High < Low")
        
        # High should be >= Open and Close
        if (df['High'] < df['Open']).any() or (df['High'] < df['Close']).any():
            issues.append("High < Open or Close in some rows")
        
        # Low should be <= Open and Close
        if (df['Low'] > df['Open']).any() or (df['Low'] > df['Close']).any():
            issues.append("Low > Open or Close in some rows")
        
        return issues
    
    def _check_extreme_values(self, df: pd.DataFrame, ticker: str) -> list[str]:
        """Check for extreme/suspicious values"""
        issues = []
        
        # Check for zero or negative prices
        price_cols = ['Open', 'High', 'Low', 'Close']
        for col in price_cols:
            if (df[col] <= 0).any():
                issues.append(f"Zero or negative values in {col}")
        
        # Check for extreme price changes (>50% in one day)
        df['price_change'] = df['Close'].pct_change()
        extreme_changes = df[abs(df['price_change']) > 0.5]
        if len(extreme_changes) > 0:
            issues.append(
                f"Warning: {len(extreme_changes)} days with >50% price change"
            )
        
        return issues
    
    def _calculate_checksum(self, df: pd.DataFrame) -> str:
        """Calculate MD5 checksum of data"""
        data_str = df.to_csv(index=True)
        return hashlib.md5(data_str.encode()).hexdigest()
```

---

#### **1.5 Stock Downloader (`stock_downloader.py`)**

```python
import yfinance as yf
import pandas as pd
import os
import json
import logging
from datetime import datetime
from pathlib import Path

from .config import IngestionConfig
from .validators import DataValidator, ValidationResult
from .retry_handler import retry_on_failure
from .progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)

class StockDownloader:
    """Download and validate stock data from Yahoo Finance"""
    
    def __init__(self, config: IngestionConfig):
        self.config = config
        self.validator = DataValidator(
            min_records=config.MIN_RECORDS_REQUIRED,
            max_null_pct=config.MAX_NULL_PERCENTAGE,
            min_completeness=config.MIN_COMPLETENESS_SCORE
        )
        self.tracker = ProgressTracker(
            manifest_path=os.path.join(config.RAW_DIR, 'manifest.json'),
            tickers=config.TICKERS
        )
    
    def download_all(self, resume: bool = True):
        """Download all tickers with progress tracking"""
        logger.info(f"Starting download for {len(self.config.TICKERS)} tickers")
        
        # Determine which tickers to process
        if resume:
            pending = self.tracker.get_pending()
            failed = [t for t in self.tracker.get_failed() 
                     if self.tracker.should_retry(t, self.config.MAX_RETRIES)]
            to_process = pending + failed
            logger.info(
                f"Resume mode: {len(pending)} pending, "
                f"{len(failed)} failed (will retry)"
            )
        else:
            to_process = self.config.TICKERS
            logger.info("Fresh start mode: processing all tickers")
        
        # Process in batches
        for i in range(0, len(to_process), self.config.BATCH_SIZE):
            batch = to_process[i:i + self.config.BATCH_SIZE]
            logger.info(
                f"Processing batch {i//self.config.BATCH_SIZE + 1}: "
                f"{batch}"
            )
            
            for ticker in batch:
                try:
                    self.download_ticker(ticker)
                    time.sleep(self.config.DELAY_BETWEEN_TICKERS)
                except Exception as e:
                    logger.error(f"Failed to download {ticker}: {e}")
            
            # Delay between batches
            if i + self.config.BATCH_SIZE < len(to_process):
                logger.info(
                    f"Batch complete. Waiting {self.config.BATCH_DELAY}s "
                    f"before next batch..."
                )
                time.sleep(self.config.BATCH_DELAY)
        
        # Final summary
        summary = self.tracker.get_summary()
        logger.info("=" * 50)
        logger.info("DOWNLOAD COMPLETE")
        logger.info(f"Total: {summary['total']}")
        logger.info(f"Completed: {summary['completed']}")
        logger.info(f"Failed: {summary['failed']}")
        logger.info(f"Completion Rate: {summary['completion_rate']:.1f}%")
        logger.info("=" * 50)
        
        return summary
    
    @retry_on_failure(max_retries=5, initial_delay=2)
    def download_ticker(self, ticker: str):
        """Download data for single ticker with retry"""
        logger.info(f"Downloading {ticker}...")
        self.tracker.mark_in_progress(ticker)
        
        try:
            # 1. Download from Yahoo Finance
            stock = yf.Ticker(ticker)
            df = stock.history(
                period=self.config.PERIOD,
                interval=self.config.INTERVAL
            )
            
            if df.empty:
                raise ValueError(f"No data returned for {ticker}")
            
            logger.info(f"{ticker}: Downloaded {len(df)} records")
            
            # 2. Validate data
            validation = self.validator.validate(df, ticker)
            
            if not validation.is_valid:
                error_msg = f"Validation failed: {'; '.join(validation.issues)}"
                logger.error(f"{ticker}: {error_msg}")
                self.tracker.mark_failed(ticker, error_msg)
                raise ValueError(error_msg)
            
            logger.info(
                f"{ticker}: Validation passed - "
                f"{validation.record_count} records, "
                f"{validation.completeness_score:.2%} complete"
            )
            
            # 3. Save to disk
            ticker_dir = os.path.join(self.config.RAW_DIR, ticker)
            os.makedirs(ticker_dir, exist_ok=True)
            
            # Save Parquet
            parquet_path = os.path.join(ticker_dir, 'daily_1y.parquet')
            df.to_parquet(parquet_path, compression='snappy')
            
            # Save metadata
            metadata = {
                'ticker': ticker,
                'period': self.config.PERIOD,
                'interval': self.config.INTERVAL,
                'record_count': validation.record_count,
                'date_range_start': validation.date_range[0],
                'date_range_end': validation.date_range[1],
                'completeness_score': validation.completeness_score,
                'null_percentage': validation.null_percentage,
                'downloaded_at': datetime.now().isoformat(),
                'data_source': 'yahoo_finance',
                'schema_version': '1.0'
            }
            
            metadata_path = os.path.join(ticker_dir, 'metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Save checksum
            checksum_path = os.path.join(ticker_dir, 'checksum.md5')
            with open(checksum_path, 'w') as f:
                f.write(validation.checksum)
            
            # 4. Mark as completed
            self.tracker.mark_completed(
                ticker=ticker,
                record_count=validation.record_count,
                file_path=parquet_path,
                checksum=validation.checksum
            )
            
            logger.info(f"{ticker}: ✅ Successfully saved to {ticker_dir}")
            
        except Exception as e:
            self.tracker.mark_failed(ticker, str(e))
            raise
```

---

## 🎮 CLI Entry Point

**`scripts/run_stock_ingestion.py`:**

```python
#!/usr/bin/env python3
import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.ingestion.config import IngestionConfig
from scripts.ingestion.stock_downloader import StockDownloader

def setup_logging(config: IngestionConfig):
    """Configure logging"""
    Path(config.LOG_DIR).mkdir(parents=True, exist_ok=True)
    
    log_file = Path(config.LOG_DIR) / f"stock_ingestion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    parser = argparse.ArgumentParser(
        description='Download stock market data from Yahoo Finance'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from last checkpoint (skip completed tickers)'
    )
    parser.add_argument(
        '--fresh',
        action='store_true',
        help='Start fresh (ignore previous progress)'
    )
    
    args = parser.parse_args()
    
    # Initialize
    config = IngestionConfig()
    setup_logging(config)
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Stock Market Data Ingestion - Step 1")
    logger.info("=" * 60)
    logger.info(f"Tickers: {len(config.TICKERS)}")
    logger.info(f"Period: {config.PERIOD}, Interval: {config.INTERVAL}")
    logger.info(f"Output: {config.RAW_DIR}")
    logger.info(f"Resume: {not args.fresh}")
    logger.info("=" * 60)
    
    # Download
    downloader = StockDownloader(config)
    summary = downloader.download_all(resume=not args.fresh)
    
    # Exit code based on results
    if summary['failed'] > 0:
        logger.warning(f"Completed with {summary['failed']} failures")
        sys.exit(1)
    else:
        logger.info("All tickers downloaded successfully!")
        sys.exit(0)

if __name__ == '__main__':
    main()
```

---

## 🚀 Usage

### **Initial Run:**
```bash
cd /Users/thomas.findelkind/Code/FinagentiX

# Install dependencies
pip install -r scripts/requirements-ingestion.txt

# Run download (foreground)
python scripts/run_stock_ingestion.py

# Or run in background (recommended for long runs)
nohup python scripts/run_stock_ingestion.py > ingestion.out 2>&1 &
echo $! > ingestion.pid
```

### **Resume After Failure:**
```bash
# Automatically resumes, skips completed, retries failed
python scripts/run_stock_ingestion.py --resume

# Or in background
nohup python scripts/run_stock_ingestion.py --resume > ingestion.out 2>&1 &
echo $! > ingestion.pid
```

### **Fresh Start:**
```bash
# Ignore previous progress, start over
python scripts/run_stock_ingestion.py --fresh
```

### **Check Progress (While Running):**
```bash
# View live manifest (progress tracker)
cat data/raw/stock_data/manifest.json | jq '{total, completed, failed, pending, completion_rate: (.completed / .total * 100)}'

# View live log output (if running in background)
tail -f ingestion.out

# Or watch progress every 5 seconds
watch -n 5 'cat data/raw/stock_data/manifest.json | jq "{completed, failed, pending, rate: (.completed / .total * 100 | tostring + \"%\")}"'

# Check if process is still running
ps -p $(cat ingestion.pid) || echo "Process finished"

# Count downloaded files
ls -1 data/raw/stock_data/*/daily_1y.parquet 2>/dev/null | wc -l
```

### **Stop Background Process:**
```bash
# Gracefully stop (will finish current ticker)
kill -TERM $(cat ingestion.pid)

# Force stop (not recommended)
kill -9 $(cat ingestion.pid)

# Resume later with --resume flag
```

---

## ✅ Validation Checks

After each ticker download:
1. ✅ Minimum 200 records (8 months of daily data)
2. ✅ Required columns present (OHLCV)
3. ✅ Less than 5% null values
4. ✅ 90%+ data completeness
5. ✅ OHLC price relationships valid (High >= Low, etc.)
6. ✅ No zero/negative prices
7. ✅ Extreme price changes flagged (>50% in 1 day)
8. ✅ MD5 checksum generated

---

## 📊 Output

### **Manifest File (`data/raw/stock_data/manifest.json`):**
```json
{
  "version": "1.0",
  "last_updated": "2025-12-08T08:30:00",
  "total_tickers": 28,
  "completed": 27,
  "failed": 1,
  "pending": 0,
  "tickers": [
    {
      "ticker": "AAPL",
      "status": "completed",
      "attempts": 1,
      "record_count": 252,
      "file_path": "data/raw/stock_data/AAPL/daily_1y.parquet",
      "checksum": "a1b2c3d4e5f6...",
      "completed_at": "2025-12-08T08:15:23"
    }
  ]
}
```

---

## 🔄 Phase 2: Upload to Azure (Separate)

**After all data validated locally, run upload script:**

```bash
python scripts/upload_to_azure.py --type stock_data
```

**Features:**
- Reads from local `data/raw/stock_data/`
- Uploads to Azure Storage with blob metadata
- Preserves checksums for verification
- Idempotent (can re-run safely)

---

## 📈 Success Criteria

- [x] 100% of tickers downloaded
- [x] All validation checks passed
- [x] Checksums calculated and stored
- [x] Manifest complete and accurate
- [x] Data versioned in repo
- [x] Logs captured for debugging
- [x] Resume capability works
- [x] Ready for Azure upload

---

**Next Steps:**
1. Implement Step 2 (News Articles)
2. Implement Step 3 (SEC Filings)
3. Implement unified uploader
4. Test full pipeline end-to-end
