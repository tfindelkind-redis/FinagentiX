"""
SEC Filing Data Validators

Validates SEC filing data quality and completeness.
Checks: file size, format, accession number, metadata, content validation.
"""

import re
import logging
from typing import Tuple, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class SECValidator:
    """Validates SEC filing data quality."""
    
    # File size ranges by form type (in bytes)
    SIZE_LIMITS = {
        '10-K': (100_000, 5_000_000),    # 100KB - 5MB
        '10-Q': (50_000, 3_000_000),     # 50KB - 3MB
        '8-K': (10_000, 1_000_000)       # 10KB - 1MB
    }
    
    # Accession number pattern: 0000000000-00-000000
    ACCESSION_PATTERN = re.compile(r'^\d{10}-\d{2}-\d{6}$')
    
    # CIK pattern: 10 digits, zero-padded
    CIK_PATTERN = re.compile(r'^\d{10}$')
    
    def __init__(
        self,
        max_filing_age_days: int = 730  # 2 years
    ):
        """
        Initialize SEC validator with thresholds.
        
        Args:
            max_filing_age_days: Maximum age for filings to be considered valid
        """
        self.max_filing_age_days = max_filing_age_days
    
    def validate_filing(
        self,
        form_type: str,
        file_path: Path,
        metadata: Dict[str, Any],
        ticker: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate SEC filing data.
        
        Args:
            form_type: Filing form type (10-K, 10-Q, 8-K)
            file_path: Path to filing text file
            metadata: Filing metadata dictionary
            ticker: Stock ticker symbol
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # 1. Validate form type
        if form_type not in self.SIZE_LIMITS:
            errors.append(f"Unknown form type: {form_type}")
            return False, errors
        
        # 2. Check required metadata fields
        required_fields = [
            'ticker', 'cik', 'company_name', 'form_type',
            'filing_date', 'accession_number', 'file_url'
        ]
        missing_fields = [f for f in required_fields if f not in metadata]
        if missing_fields:
            errors.append(f"Missing metadata fields: {missing_fields}")
            return False, errors
        
        # 3. Validate file exists and size
        if not file_path.exists():
            errors.append(f"Filing file not found: {file_path}")
            return False, errors
        
        file_size = file_path.stat().st_size
        min_size, max_size = self.SIZE_LIMITS[form_type]
        
        if file_size < min_size:
            errors.append(
                f"File too small: {file_size} bytes "
                f"(minimum for {form_type}: {min_size})"
            )
        elif file_size > max_size:
            errors.append(
                f"File too large: {file_size} bytes "
                f"(maximum for {form_type}: {max_size})"
            )
        
        # 4. Validate accession number format
        accession = metadata.get('accession_number', '')
        if not self.ACCESSION_PATTERN.match(accession):
            errors.append(
                f"Invalid accession number format: {accession} "
                f"(expected: 0000000000-00-000000)"
            )
        
        # 5. Validate CIK format
        cik = metadata.get('cik', '')
        if not self.CIK_PATTERN.match(cik):
            errors.append(
                f"Invalid CIK format: {cik} (expected: 10 digits)"
            )
        
        # 6. Validate filing date recency
        filing_date_str = metadata.get('filing_date', '')
        try:
            filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d')
            max_age = datetime.now() - timedelta(days=self.max_filing_age_days)
            
            if filing_date < max_age:
                logger.warning(
                    f"Filing date is older than {self.max_filing_age_days} days: "
                    f"{filing_date_str}"
                )
        except ValueError:
            errors.append(f"Invalid filing_date format: {filing_date_str}")
        
        # 7. Validate ticker consistency
        metadata_ticker = metadata.get('ticker', '')
        if metadata_ticker != ticker:
            errors.append(
                f"Ticker mismatch: expected {ticker}, "
                f"got {metadata_ticker} in metadata"
            )
        
        # 8. Validate form type consistency
        metadata_form = metadata.get('form_type', '')
        if metadata_form != form_type:
            errors.append(
                f"Form type mismatch: expected {form_type}, "
                f"got {metadata_form} in metadata"
            )
        
        # 9. Validate file content (not empty, has expected markers)
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1000)  # Read first 1KB
                
                if not content or len(content.strip()) < 100:
                    errors.append("File appears to be empty or too short")
                
                # Check for common SEC filing markers
                has_sec_markers = any(
                    marker in content.upper()
                    for marker in ['SEC', 'EDGAR', 'SECURITIES', 'COMMISSION']
                )
                
                if not has_sec_markers:
                    logger.warning(
                        f"File may not be a valid SEC filing "
                        f"(no SEC markers found in first 1KB)"
                    )
        except Exception as e:
            errors.append(f"Error reading file: {str(e)}")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def validate_8k_list(
        self,
        filings_data: List[Dict[str, Any]],
        ticker: str,
        min_count: int = 1
    ) -> Tuple[bool, List[str]]:
        """
        Validate 8-K filings list.
        
        Args:
            filings_data: List of 8-K filing metadata
            ticker: Stock ticker symbol
            min_count: Minimum number of 8-K filings expected
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        if len(filings_data) < min_count:
            errors.append(
                f"Insufficient 8-K filings: {len(filings_data)} "
                f"(minimum: {min_count})"
            )
        
        # Validate each filing metadata
        for i, filing in enumerate(filings_data):
            required_fields = ['accession_number', 'filing_date', 'form_type']
            missing = [f for f in required_fields if f not in filing]
            
            if missing:
                errors.append(
                    f"8-K filing {i+1} missing fields: {missing}"
                )
            
            # Validate accession number format
            accession = filing.get('accession_number', '')
            if accession and not self.ACCESSION_PATTERN.match(accession):
                errors.append(
                    f"8-K filing {i+1} has invalid accession: {accession}"
                )
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def get_filing_stats(
        self,
        ticker: str,
        ticker_dir: Path
    ) -> Dict[str, Any]:
        """
        Get statistics for downloaded filings.
        
        Args:
            ticker: Stock ticker symbol
            ticker_dir: Path to ticker directory
            
        Returns:
            Dictionary with filing statistics
        """
        stats = {
            'ticker': ticker,
            'filings_downloaded': 0,
            'total_size_bytes': 0,
            'forms': {}
        }
        
        for form_type in ['10-K', '10-Q', '8-K']:
            form_dir = ticker_dir / form_type
            
            if form_dir.exists():
                if form_type == '8-K':
                    # 8-K stores list in JSON
                    json_file = form_dir / 'recent_filings.json'
                    if json_file.exists():
                        stats['forms'][form_type] = 1
                        stats['filings_downloaded'] += 1
                        stats['total_size_bytes'] += json_file.stat().st_size
                else:
                    # 10-K and 10-Q store full text
                    txt_files = list(form_dir.glob('*.txt')) + list(form_dir.glob('*.htm'))
                    
                    if txt_files:
                        stats['forms'][form_type] = len(txt_files)
                        stats['filings_downloaded'] += len(txt_files)
                        stats['total_size_bytes'] += sum(
                            f.stat().st_size for f in txt_files
                        )
        
        return stats
