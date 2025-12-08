"""
News Article Downloader

Downloads news articles for specified tickers using yfinance.
Features: retry logic, validation, progress tracking, resume capability.
"""

import yfinance as yf
import pandas as pd
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import logging

from .news_validators import NewsValidator
from .progress_tracker import ProgressTracker
from .retry_handler import retry_with_backoff


logger = logging.getLogger(__name__)


class NewsDownloader:
    """Downloads and validates news articles for stock tickers."""
    
    def __init__(
        self,
        output_dir: str,
        tickers: List[str],
        validator: Optional[NewsValidator] = None,
        tracker: Optional[ProgressTracker] = None
    ):
        """
        Initialize news downloader.
        
        Args:
            output_dir: Base directory for news data (e.g., 'data/raw/news_articles')
            tickers: List of ticker symbols to download
            validator: NewsValidator instance (uses default if None)
            tracker: ProgressTracker instance (uses default if None)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.validator = validator or NewsValidator()
        self.tracker = tracker or ProgressTracker(
            manifest_path=str(self.output_dir / "manifest.json"),
            tickers=tickers
        )
    
    def download_ticker(self, ticker: str) -> bool:
        """
        Download news articles for a single ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Starting download for {ticker}")
            self.tracker.mark_in_progress(ticker)
            
            # Download with retry
            df = self._download_with_retry(ticker)
            
            if df is None or len(df) == 0:
                logger.warning(f"No data returned for {ticker}")
                self.tracker.mark_failed(
                    ticker,
                    error="No articles returned from API"
                )
                return False
            
            # Validate data
            is_valid, errors = self.validator.validate(df, ticker)
            if not is_valid:
                error_msg = "; ".join(errors)
                logger.error(f"Validation failed for {ticker}: {error_msg}")
                self.tracker.mark_failed(ticker, error=error_msg)
                return False
            
            # Save data
            parquet_path, checksum = self._save_to_parquet(df, ticker)
            
            # Mark success
            quality_stats = self.validator.get_quality_stats(df)
            self.tracker.mark_completed(
                ticker=ticker,
                record_count=len(df),
                file_path=str(parquet_path),
                checksum=checksum
            )
            
            logger.info(
                f"✓ {ticker}: {len(df)} articles downloaded "
                f"({quality_stats['unique_sources']} sources)"
            )
            return True
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Failed to download {ticker}: {error_msg}")
            self.tracker.mark_failed(ticker, error=error_msg)
            return False
    
    @retry_with_backoff(max_retries=5, delays=[2, 4, 8, 16, 32, 60])
    def _download_with_retry(self, ticker: str) -> Optional[pd.DataFrame]:
        """
        Download news articles with retry logic.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            DataFrame with articles, or None if failed
        """
        logger.debug(f"Fetching news for {ticker}")
        
        # Fetch news from yfinance
        ticker_obj = yf.Ticker(ticker)
        news = ticker_obj.news
        
        if not news or len(news) == 0:
            logger.warning(f"No news articles found for {ticker}")
            return None
        
        # Transform to our schema
        articles = []
        fetched_at = datetime.now().isoformat()
        
        for item in news:
            content = item.get('content', {})
            
            # Generate unique article ID from URL + publication date
            canonical = content.get('canonicalUrl', {})
            url = canonical.get('url', '') if canonical else ''
            pub_date = content.get('pubDate', '')
            article_id = hashlib.md5(f'{url}{pub_date}'.encode()).hexdigest()
            
            # Safely extract nested fields
            thumbnail = content.get('thumbnail', {})
            image_url = thumbnail.get('originalUrl', None) if thumbnail else None
            
            provider = content.get('provider', {})
            source = provider.get('displayName', 'Yahoo Finance') if provider else 'Yahoo Finance'
            
            article = {
                'article_id': article_id,
                'ticker': ticker,
                'source': source,
                'title': content.get('title', ''),
                'description': content.get('description', ''),
                'summary': content.get('summary', ''),
                'url': url,
                'published_at': pub_date,
                'image_url': image_url,
                'fetched_at': fetched_at,
                'content_type': content.get('contentType', 'STORY')
            }
            articles.append(article)
        
        df = pd.DataFrame(articles)
        logger.debug(f"Fetched {len(df)} articles for {ticker}")
        
        return df
    
    def _save_to_parquet(self, df: pd.DataFrame, ticker: str) -> tuple[Path, str]:
        """
        Save DataFrame to Parquet with metadata and checksum.
        
        Args:
            df: DataFrame with news articles
            ticker: Stock ticker symbol
            
        Returns:
            Tuple of (parquet_path, checksum)
        """
        # Create ticker directory
        ticker_dir = self.output_dir / ticker
        ticker_dir.mkdir(parents=True, exist_ok=True)
        
        # Save Parquet file
        parquet_path = ticker_dir / "articles_recent.parquet"
        df.to_parquet(
            parquet_path,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        logger.debug(f"Saved {len(df)} articles to {parquet_path}")
        
        # Create metadata
        quality_stats = self.validator.get_quality_stats(df)
        metadata = {
            'ticker': ticker,
            'source': 'yfinance',
            'download_timestamp': datetime.now().isoformat(),
            'article_count': len(df),
            'date_range': [
                df['published_at'].min() if len(df) > 0 else None,
                df['published_at'].max() if len(df) > 0 else None
            ],
            'sources': df['source'].unique().tolist() if len(df) > 0 else [],
            'has_images': int(df['image_url'].notna().sum()),
            'quality_stats': quality_stats,
            'file_size_bytes': parquet_path.stat().st_size
        }
        
        metadata_path = ticker_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        logger.debug(f"Saved metadata to {metadata_path}")
        
        # Create checksum
        checksum = self._calculate_checksum(parquet_path)
        checksum_path = ticker_dir / "checksum.md5"
        with open(checksum_path, 'w') as f:
            f.write(f"{checksum}  {parquet_path.name}\n")
        logger.debug(f"Saved checksum to {checksum_path}")
        
        return parquet_path, checksum
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum for a file."""
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get download progress summary from tracker."""
        return self.tracker.get_summary()
