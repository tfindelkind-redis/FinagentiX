"""
SEC Filing Downloader

Downloads SEC filings from EDGAR API for specified tickers.
Features: CIK lookup, rate limiting, retry logic, validation, progress tracking.
"""

import requests
import time
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import re

from .sec_validators import SECValidator
from .progress_tracker import ProgressTracker
from .retry_handler import retry_with_backoff

logger = logging.getLogger(__name__)


class SECDownloader:
    """Downloads and validates SEC filings from EDGAR."""
    
    # SEC API base URLs
    SEC_SEARCH_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
    SEC_DATA_URL = "https://data.sec.gov/submissions"
    SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
    
    def __init__(
        self,
        output_dir: str,
        tickers: List[str],
        user_agent: str = "FinagentiX/1.0 (github.com/tfindelkind-redis)",
        rate_limit_delay: float = 0.11,  # 10 req/sec with buffer
        validator: Optional[SECValidator] = None,
        tracker: Optional[ProgressTracker] = None
    ):
        """
        Initialize SEC downloader.
        
        Args:
            output_dir: Base directory for SEC filings (e.g., 'data/raw/sec_filings')
            tickers: List of ticker symbols to download
            user_agent: User-Agent header (required by SEC)
            rate_limit_delay: Delay between requests in seconds
            validator: SECValidator instance (uses default if None)
            tracker: ProgressTracker instance (uses default if None)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.user_agent = user_agent
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        
        self.validator = validator or SECValidator()
        self.tracker = tracker or ProgressTracker(
            manifest_path=str(self.output_dir / "manifest.json"),
            tickers=tickers
        )
        
        # Don't use session - SEC seems to block persistent connections
        # Cache for CIK lookups
        self.cik_cache: Dict[str, str] = {}
    
    def _rate_limit(self):
        """Enforce rate limiting (10 requests per second)."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    @retry_with_backoff(max_retries=5, delays=[2, 4, 8, 16, 32, 60])
    def _request(self, url: str, **kwargs) -> requests.Response:
        """
        Make HTTP request with rate limiting and retry.
        
        Args:
            url: URL to request
            **kwargs: Additional arguments for requests.get
            
        Returns:
            Response object
        """
        self._rate_limit()
        logger.debug(f"Requesting: {url}")
        
        # Set headers for each request (SEC requires specific User-Agent)
        headers = {
            'User-Agent': self.user_agent,
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate'
        }
        
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers
        
        response = requests.get(url, **kwargs)
        response.raise_for_status()
        
        return response
    
    # Known CIK mappings for common tickers
    KNOWN_CIKS = {
        'AAPL': '0000320193', 'MSFT': '0000789019', 'GOOGL': '0001652044',
        'AMZN': '0001018724', 'META': '0001326801', 'NVDA': '0001045810',
        'TSLA': '0001318605', 'JPM': '0000019617', 'BAC': '0000070858',
        'WFC': '0000072971', 'GS': '0000886982', 'MS': '0000895421',
        'WMT': '0000104169', 'HD': '0000354950', 'NKE': '0000320187',
        'SBUX': '0000829224', 'MCD': '0000063908', 'JNJ': '0000200406',
        'UNH': '0000731766', 'PFE': '0000078003', 'ABBV': '0001551152',
        'BA': '0000012927', 'CAT': '0000018230', 'GE': '0000040545',
        'XOM': '0000034088', 'CVX': '0000093410', 'COIN': '0001679788',
        'MSTR': '0001050446'
    }
    
    def get_cik(self, ticker: str) -> Optional[str]:
        """
        Get CIK (Central Index Key) for ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Zero-padded 10-digit CIK, or None if not found
        """
        if ticker in self.cik_cache:
            return self.cik_cache[ticker]
        
        # Check known CIKs first
        ticker_upper = ticker.upper()
        if ticker_upper in self.KNOWN_CIKS:
            cik = self.KNOWN_CIKS[ticker_upper]
            self.cik_cache[ticker] = cik
            logger.debug(f"Found CIK for {ticker} in known mappings: {cik}")
            return cik
        
        try:
            # Try SEC company_tickers.json (public mapping file)
            # This is more reliable than the submissions API
            tickers_url = "https://www.sec.gov/files/company_tickers.json"
            
            try:
                response = self._request(tickers_url)
                tickers_data = response.json()
                
                # Search for ticker in the data
                for entry in tickers_data.values():
                    if entry.get('ticker', '').upper() == ticker_upper:
                        cik = str(entry['cik_str']).zfill(10)
                        self.cik_cache[ticker] = cik
                        logger.debug(f"Found CIK for {ticker}: {cik}")
                        return cik
            except Exception as e:
                logger.debug(f"Could not fetch company_tickers.json: {e}")
            
            logger.warning(f"Could not find CIK for {ticker}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting CIK for {ticker}: {e}")
            return None
    
    def get_company_filings(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Get company filings metadata from SEC.
        
        Args:
            cik: Zero-padded 10-digit CIK
            
        Returns:
            Dictionary with company and filings data, or None if failed
        """
        try:
            url = f"{self.SEC_DATA_URL}/CIK{cik}.json"
            response = self._request(url)
            data = response.json()
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting filings for CIK {cik}: {e}")
            return None
    
    def download_filing(
        self,
        cik: str,
        accession: str,
        primary_doc: str,
        save_path: Path
    ) -> bool:
        """
        Download single filing document.
        
        Args:
            cik: Central Index Key
            accession: Accession number (with dashes)
            primary_doc: Primary document filename
            save_path: Where to save the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove dashes from accession for URL
            accession_no_dash = accession.replace('-', '')
            
            # Construct filing URL
            url = f"{self.SEC_ARCHIVES_URL}/{cik}/{accession_no_dash}/{primary_doc}"
            
            logger.debug(f"Downloading filing: {url}")
            response = self._request(url)
            
            # Save file
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            logger.debug(f"Saved filing to {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading filing {accession}: {e}")
            return False
    
    def download_ticker(self, ticker: str) -> bool:
        """
        Download all filings for a single ticker.
        
        Downloads:
        - Latest 10-K (annual report)
        - Latest 10-Q (quarterly report)
        - Recent 8-Ks (last 5 material events)
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Starting download for {ticker}")
            self.tracker.mark_in_progress(ticker)
            
            # Get CIK
            cik = self.get_cik(ticker)
            if not cik:
                self.tracker.mark_failed(ticker, error="Could not find CIK")
                return False
            
            # Get company filings
            filings_data = self.get_company_filings(cik)
            if not filings_data:
                self.tracker.mark_failed(ticker, error="Could not retrieve filings data")
                return False
            
            company_name = filings_data.get('name', ticker)
            recent_filings = filings_data.get('filings', {}).get('recent', {})
            
            if not recent_filings:
                self.tracker.mark_failed(ticker, error="No recent filings found")
                return False
            
            # Create ticker directory
            ticker_dir = self.output_dir / ticker
            ticker_dir.mkdir(parents=True, exist_ok=True)
            
            # Track downloaded filings
            downloaded_count = 0
            total_size = 0
            filings_summary = {}
            
            # Download 10-K (most recent)
            downloaded = self._download_form_type(
                ticker, cik, company_name, '10-K', recent_filings, limit=1
            )
            if downloaded:
                downloaded_count += 1
                filings_summary['10-K'] = 1
            
            # Download 10-Q (most recent)
            downloaded = self._download_form_type(
                ticker, cik, company_name, '10-Q', recent_filings, limit=1
            )
            if downloaded:
                downloaded_count += 1
                filings_summary['10-Q'] = 1
            
            # Download 8-Ks (last 5)
            count_8k = self._download_8k_list(
                ticker, cik, company_name, recent_filings, limit=5
            )
            if count_8k > 0:
                downloaded_count += 1
                filings_summary['8-K'] = count_8k
            
            # Save ticker metadata
            stats = self.validator.get_filing_stats(ticker, ticker_dir)
            total_size = stats['total_size_bytes']
            
            ticker_metadata = {
                'ticker': ticker,
                'cik': cik,
                'company_name': company_name,
                'download_timestamp': datetime.now().isoformat(),
                'filings_summary': filings_summary,
                'total_filings': downloaded_count,
                'total_size_bytes': total_size
            }
            
            metadata_path = ticker_dir / 'ticker_metadata.json'
            with open(metadata_path, 'w') as f:
                json.dump(ticker_metadata, f, indent=2)
            
            # Mark success
            if downloaded_count > 0:
                self.tracker.mark_completed(
                    ticker=ticker,
                    record_count=downloaded_count,
                    file_path=str(ticker_dir),
                    checksum=self._calculate_checksum(metadata_path)
                )
                
                logger.info(
                    f"✓ {ticker}: {downloaded_count} filing types downloaded "
                    f"({total_size / 1024:.1f} KB)"
                )
                return True
            else:
                self.tracker.mark_failed(ticker, error="No filings downloaded")
                return False
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Failed to download {ticker}: {error_msg}")
            self.tracker.mark_failed(ticker, error=error_msg)
            return False
    
    def _download_form_type(
        self,
        ticker: str,
        cik: str,
        company_name: str,
        form_type: str,
        recent_filings: Dict[str, List],
        limit: int = 1
    ) -> bool:
        """Download filings of a specific form type."""
        try:
            # Extract filings of this form type
            accessions = recent_filings.get('accessionNumber', [])
            forms = recent_filings.get('form', [])
            filing_dates = recent_filings.get('filingDate', [])
            primary_docs = recent_filings.get('primaryDocument', [])
            
            # Find matching filings
            matches = []
            for i, form in enumerate(forms):
                if form == form_type and i < len(accessions):
                    matches.append({
                        'accession': accessions[i],
                        'filing_date': filing_dates[i] if i < len(filing_dates) else None,
                        'primary_doc': primary_docs[i] if i < len(primary_docs) else None
                    })
                    
                    if len(matches) >= limit:
                        break
            
            if not matches:
                logger.warning(f"No {form_type} filings found for {ticker}")
                return False
            
            # Download first match
            filing = matches[0]
            accession = filing['accession']
            primary_doc = filing['primary_doc']
            
            if not primary_doc:
                logger.warning(f"No primary document for {form_type} {accession}")
                return False
            
            # Create form directory
            form_dir = self.output_dir / ticker / form_type
            form_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine file extension
            ext = '.htm' if primary_doc.endswith('.htm') else '.txt'
            file_path = form_dir / f"{accession.replace('-', '')}{ext}"
            
            # Download filing
            if not self.download_filing(cik, accession, primary_doc, file_path):
                return False
            
            # Create metadata
            metadata = {
                'ticker': ticker,
                'cik': cik,
                'company_name': company_name,
                'form_type': form_type,
                'filing_date': filing['filing_date'],
                'accession_number': accession,
                'primary_document': primary_doc,
                'file_url': f"{self.SEC_ARCHIVES_URL}/{cik}/{accession.replace('-', '')}/{primary_doc}",
                'file_size_bytes': file_path.stat().st_size,
                'download_timestamp': datetime.now().isoformat(),
                'checksum_md5': self._calculate_checksum(file_path)
            }
            
            metadata_path = form_dir / 'filing_metadata.json'
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Create checksum file
            checksum_path = form_dir / 'checksum.md5'
            with open(checksum_path, 'w') as f:
                f.write(f"{metadata['checksum_md5']}  {file_path.name}\n")
            
            # Validate
            is_valid, errors = self.validator.validate_filing(
                form_type, file_path, metadata, ticker
            )
            
            if not is_valid:
                logger.warning(f"Validation warnings for {ticker} {form_type}: {errors}")
            
            logger.debug(f"Downloaded {form_type} for {ticker}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading {form_type} for {ticker}: {e}")
            return False
    
    def _download_8k_list(
        self,
        ticker: str,
        cik: str,
        company_name: str,
        recent_filings: Dict[str, List],
        limit: int = 5
    ) -> int:
        """Download list of recent 8-K filings (metadata only)."""
        try:
            # Extract 8-K filings
            accessions = recent_filings.get('accessionNumber', [])
            forms = recent_filings.get('form', [])
            filing_dates = recent_filings.get('filingDate', [])
            
            # Find 8-K filings
            filings_8k = []
            for i, form in enumerate(forms):
                if form == '8-K' and i < len(accessions):
                    filings_8k.append({
                        'accession_number': accessions[i],
                        'filing_date': filing_dates[i] if i < len(filing_dates) else None,
                        'form_type': '8-K'
                    })
                    
                    if len(filings_8k) >= limit:
                        break
            
            if not filings_8k:
                logger.warning(f"No 8-K filings found for {ticker}")
                return 0
            
            # Create 8-K directory
            form_dir = self.output_dir / ticker / '8-K'
            form_dir.mkdir(parents=True, exist_ok=True)
            
            # Save filings list
            filings_data = {
                'ticker': ticker,
                'cik': cik,
                'company_name': company_name,
                'form_type': '8-K',
                'download_timestamp': datetime.now().isoformat(),
                'filings_count': len(filings_8k),
                'filings': filings_8k
            }
            
            json_path = form_dir / 'recent_filings.json'
            with open(json_path, 'w') as f:
                json.dump(filings_data, f, indent=2)
            
            # Create checksum
            checksum_path = form_dir / 'checksum.md5'
            checksum = self._calculate_checksum(json_path)
            with open(checksum_path, 'w') as f:
                f.write(f"{checksum}  {json_path.name}\n")
            
            # Validate
            is_valid, errors = self.validator.validate_8k_list(
                filings_8k, ticker, min_count=1
            )
            
            if not is_valid:
                logger.warning(f"Validation warnings for {ticker} 8-K list: {errors}")
            
            logger.debug(f"Saved {len(filings_8k)} 8-K filings for {ticker}")
            return len(filings_8k)
            
        except Exception as e:
            logger.error(f"Error downloading 8-K list for {ticker}: {e}")
            return 0
    
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
