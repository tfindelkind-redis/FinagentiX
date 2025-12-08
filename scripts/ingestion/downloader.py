"""Stock data downloader with validation and progress tracking"""
import pandas as pd
import yfinance as yf
from pathlib import Path
import json
import logging
from typing import Optional
from datetime import datetime

from .config import IngestionConfig
from .progress_tracker import ProgressTracker
from .validators import DataValidator
from .retry_handler import retry_with_backoff

logger = logging.getLogger(__name__)

class StockDownloader:
    """Download and validate stock market data"""
    
    def __init__(self, config: IngestionConfig, tracker: ProgressTracker):
        self.config = config
        self.tracker = tracker
        self.validator = DataValidator(
            min_records=config.validation_thresholds['min_records'],
            max_null_pct=config.validation_thresholds['max_null_percent'],
            min_completeness=config.validation_thresholds['min_completeness']
        )
    
    def download_ticker(self, ticker: str) -> bool:
        """
        Download and validate data for a single ticker
        
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Starting download for {ticker}")
        self.tracker.mark_in_progress(ticker)
        
        try:
            # Download with retry
            df = self._download_with_retry(ticker)
            if df is None or df.empty:
                error_msg = f"No data returned for {ticker}"
                logger.error(error_msg)
                self.tracker.mark_failed(ticker, error_msg)
                return False
            
            # Validate data
            validation_result = self.validator.validate(df, ticker)
            
            if not validation_result.is_valid:
                error_msg = f"Validation failed: {'; '.join(validation_result.issues)}"
                logger.error(f"{ticker}: {error_msg}")
                self.tracker.mark_failed(ticker, error_msg)
                return False
            
            # Save to disk
            output_dir = Path(self.config.output_dir) / ticker
            output_dir.mkdir(parents=True, exist_ok=True)
            
            parquet_path = output_dir / f"daily_{self.config.period}.parquet"
            self._save_to_parquet(df, parquet_path)
            
            # Save metadata
            metadata = {
                'ticker': ticker,
                'period': self.config.period,
                'interval': self.config.interval,
                'download_timestamp': datetime.now().isoformat(),
                'record_count': validation_result.record_count,
                'date_range': validation_result.date_range,
                'completeness_score': validation_result.completeness_score,
                'null_percentage': validation_result.null_percentage,
                'checksum': validation_result.checksum,
                'file_path': str(parquet_path),
                'file_size_bytes': parquet_path.stat().st_size
            }
            
            metadata_path = output_dir / 'metadata.json'
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Save checksum separately
            checksum_path = output_dir / 'checksum.md5'
            with open(checksum_path, 'w') as f:
                f.write(validation_result.checksum)
            
            # Update tracker
            self.tracker.mark_completed(
                ticker, 
                validation_result.record_count,
                str(parquet_path),
                validation_result.checksum
            )
            logger.info(
                f"{ticker}: Successfully downloaded {validation_result.record_count} "
                f"records ({validation_result.date_range[0]} to "
                f"{validation_result.date_range[1]})"
            )
            
            return True
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(f"{ticker}: {error_msg}")
            self.tracker.mark_failed(ticker, error_msg)
            return False
    
    @retry_with_backoff(max_retries=5, delays=[2, 4, 8, 16, 32, 60])
    def _download_with_retry(self, ticker: str) -> Optional[pd.DataFrame]:
        """Download data with automatic retry on failure"""
        logger.debug(f"Attempting download for {ticker}")
        
        # Download from Yahoo Finance
        df = yf.download(
            ticker,
            period=self.config.period,
            interval=self.config.interval,
            progress=False  # Suppress yfinance progress bar
        )
        
        if df.empty:
            raise ValueError(f"No data returned for {ticker}")
        
        return df
    
    def _save_to_parquet(self, df: pd.DataFrame, path: Path):
        """Save dataframe to parquet with compression"""
        df.to_parquet(
            path,
            engine='pyarrow',
            compression='snappy',
            index=True
        )
        logger.debug(f"Saved data to {path}")
