"""
News Article Data Validators

Validates news article data quality and completeness.
Checks: required fields, article count, URL validity, duplicates, content length.
"""

import pandas as pd
import logging
from typing import Tuple, List, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class NewsValidator:
    """Validates news article data quality."""
    
    def __init__(
        self,
        min_articles: int = 5,
        max_duplicate_ratio: float = 0.3,
        min_title_length: int = 10,
        min_description_length: int = 20
    ):
        """
        Initialize news validator with thresholds.
        
        Args:
            min_articles: Minimum number of articles expected
            max_duplicate_ratio: Maximum allowed duplicate ratio (0.0-1.0)
            min_title_length: Minimum character length for title
            min_description_length: Minimum character length for description
        """
        self.min_articles = min_articles
        self.max_duplicate_ratio = max_duplicate_ratio
        self.min_title_length = min_title_length
        self.min_description_length = min_description_length
    
    def validate(self, df: pd.DataFrame, ticker: str) -> Tuple[bool, List[str]]:
        """
        Validate news article DataFrame.
        
        Args:
            df: DataFrame with news articles
            ticker: Ticker symbol for context
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # 1. Check article count
        if len(df) < self.min_articles:
            errors.append(
                f"Insufficient articles: {len(df)} (minimum: {self.min_articles})"
            )
        
        # 2. Check required columns
        required_columns = [
            'article_id', 'ticker', 'source', 'title', 'description',
            'url', 'published_at', 'fetched_at'
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")
            return False, errors  # Cannot continue validation
        
        # 3. Check for null values in required fields
        for col in required_columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                errors.append(
                    f"Column '{col}' has {null_count} null values "
                    f"({null_count/len(df)*100:.1f}%)"
                )
        
        # 4. Validate URLs
        invalid_urls = []
        for idx, url in df['url'].items():
            if pd.notna(url):
                parsed = urlparse(str(url))
                if not parsed.scheme or not parsed.netloc:
                    invalid_urls.append(f"Row {idx}: {url}")
        
        if invalid_urls:
            errors.append(
                f"Invalid URLs found ({len(invalid_urls)} articles): "
                f"{invalid_urls[:3]}"  # Show first 3
            )
        
        # 5. Check for excessive duplicates (by URL)
        if 'url' in df.columns and len(df) > 0:
            duplicate_count = df['url'].duplicated().sum()
            duplicate_ratio = duplicate_count / len(df)
            if duplicate_ratio > self.max_duplicate_ratio:
                errors.append(
                    f"Excessive duplicate URLs: {duplicate_count}/{len(df)} "
                    f"({duplicate_ratio*100:.1f}%, max: {self.max_duplicate_ratio*100}%)"
                )
        
        # 6. Validate title length
        if 'title' in df.columns:
            short_titles = df[df['title'].str.len() < self.min_title_length]
            if len(short_titles) > 0:
                errors.append(
                    f"Short titles found: {len(short_titles)} articles "
                    f"(minimum length: {self.min_title_length} chars)"
                )
        
        # 7. Validate description length (warning only, not error)
        if 'description' in df.columns:
            short_descriptions = df[
                df['description'].notna() & 
                (df['description'].str.len() < self.min_description_length)
            ]
            if len(short_descriptions) > 0:
                logger.debug(
                    f"Note: {len(short_descriptions)} articles have short descriptions "
                    f"(< {self.min_description_length} chars) - this is common with yfinance"
                )
        
        # 8. Check ticker consistency
        if 'ticker' in df.columns:
            unique_tickers = df['ticker'].unique()
            if len(unique_tickers) > 1:
                errors.append(
                    f"Multiple tickers found in data: {list(unique_tickers)}"
                )
            elif len(unique_tickers) == 1 and unique_tickers[0] != ticker:
                errors.append(
                    f"Ticker mismatch: expected {ticker}, found {unique_tickers[0]}"
                )
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def get_quality_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get data quality statistics.
        
        Args:
            df: DataFrame with news articles
            
        Returns:
            Dictionary with quality metrics
        """
        if len(df) == 0:
            return {
                'article_count': 0,
                'completeness': 0.0,
                'has_images': 0,
                'avg_title_length': 0,
                'avg_description_length': 0,
                'unique_sources': 0,
                'date_range_days': 0
            }
        
        stats = {
            'article_count': len(df),
            'completeness': (1 - df[['title', 'description', 'url']].isna().sum().sum() 
                           / (len(df) * 3)) * 100,
            'has_images': int(df.get('image_url', pd.Series()).notna().sum()),
            'avg_title_length': float(df['title'].str.len().mean()) if 'title' in df.columns else 0,
            'avg_description_length': float(df['description'].str.len().mean()) 
                if 'description' in df.columns else 0,
            'unique_sources': len(df['source'].unique()) if 'source' in df.columns else 0,
        }
        
        # Calculate date range if published_at is available
        if 'published_at' in df.columns and len(df) > 0:
            try:
                dates = pd.to_datetime(df['published_at'])
                date_range = (dates.max() - dates.min()).days
                stats['date_range_days'] = int(date_range)
            except Exception:
                stats['date_range_days'] = 0
        else:
            stats['date_range_days'] = 0
        
        return stats
