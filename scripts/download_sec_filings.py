#!/usr/bin/env python3
"""
SEC Filings Download Script

Downloads recent SEC filings (10-K, 10-Q, 8-K) for specified stock tickers.
Features:
- Resume capability (skips completed tickers)
- Progress tracking with manifest.json
- Rate limiting (10 req/sec for SEC API)
- Validation and retry logic
- Detailed logging

Usage:
    # Download all tickers (from config)
    python scripts/download_sec_filings.py
    
    # Resume previous download
    python scripts/download_sec_filings.py --resume
    
    # Fresh start (delete manifest)
    python scripts/download_sec_filings.py --fresh
    
    # Download specific tickers
    python scripts/download_sec_filings.py --tickers AAPL MSFT GOOGL
    
    # Specify user agent email
    python scripts/download_sec_filings.py --email your-email@example.com
    
    # Verbose logging
    python scripts/download_sec_filings.py --verbose
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ingestion.config import get_default_config
from ingestion.sec_validators import SECValidator
from ingestion.sec_downloader import SECDownloader
from ingestion.progress_tracker import ProgressTracker


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the script."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f'sec_download_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    logging.info(f"Logging to: {log_file}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Download SEC filings for stock tickers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--tickers',
        nargs='+',
        help='Specific tickers to download (default: all from config)'
    )
    
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume previous download (skip completed tickers)'
    )
    
    parser.add_argument(
        '--fresh',
        action='store_true',
        help='Start fresh (delete existing manifest)'
    )
    
    parser.add_argument(
        '--email',
        default='contact@tfindelkind-redis.com',
        help='Email for User-Agent header (required by SEC)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--output-dir',
        default='data/raw/sec_filings',
        help='Output directory for SEC filings (default: data/raw/sec_filings)'
    )
    
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=0.11,
        help='Delay between SEC requests in seconds (default: 0.11 for 10 req/sec)'
    )
    
    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    logger.info("="*80)
    logger.info("SEC FILINGS DOWNLOAD")
    logger.info("="*80)
    
    # Load configuration
    config = get_default_config()
    tickers = args.tickers if args.tickers else config.tickers
    
    logger.info(f"Configuration:")
    logger.info(f"  Tickers: {len(tickers)} ({', '.join(tickers[:5])}...)")
    logger.info(f"  Output: {args.output_dir}")
    logger.info(f"  Mode: {'RESUME' if args.resume else 'FRESH' if args.fresh else 'NORMAL'}")
    logger.info(f"  Rate limit: {args.rate_limit}s between requests")
    logger.info(f"  User-Agent: FinagentiX {args.email}")
    
    # Initialize components
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Handle fresh start
    if args.fresh:
        manifest_path = output_path / "manifest.json"
        if manifest_path.exists():
            logger.info(f"Deleting existing manifest: {manifest_path}")
            manifest_path.unlink()
    
    # Create validator
    validator = SECValidator(
        max_filing_age_days=730  # 2 years
    )
    
    # Create tracker
    tracker = ProgressTracker(
        manifest_path=str(output_path / "manifest.json"),
        tickers=tickers
    )
    
    # Create downloader
    # SEC requires format: "Company Name EmailAddress"
    user_agent = f"FinagentiX {args.email}"
    
    downloader = SECDownloader(
        output_dir=str(output_path),
        tickers=tickers,
        user_agent=user_agent,
        rate_limit_delay=args.rate_limit,
        validator=validator,
        tracker=tracker
    )
    
    # Determine which tickers to download
    if args.resume:
        pending_tickers = tracker.get_pending(tickers)
        logger.info(f"Resuming download: {len(pending_tickers)} pending tickers")
        tickers_to_download = pending_tickers
    else:
        tickers_to_download = tickers
    
    if not tickers_to_download:
        logger.info("No tickers to download. All complete!")
        return 0
    
    # SEC API warning
    logger.info("")
    logger.info("⚠️  SEC EDGAR API Notice:")
    logger.info("  - Rate limited to 10 requests/second")
    logger.info("  - Must provide valid User-Agent with contact info")
    logger.info("  - Download may take several minutes for all tickers")
    logger.info("")
    
    # Download filings
    logger.info(f"Downloading {len(tickers_to_download)} tickers...")
    logger.info("-"*80)
    
    start_time = datetime.now()
    success_count = 0
    failed_count = 0
    
    for i, ticker in enumerate(tickers_to_download, 1):
        logger.info(f"[{i}/{len(tickers_to_download)}] Processing {ticker}...")
        
        try:
            success = downloader.download_ticker(ticker)
            if success:
                success_count += 1
            else:
                failed_count += 1
                
        except KeyboardInterrupt:
            logger.warning("\nDownload interrupted by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error for {ticker}: {e}", exc_info=True)
            failed_count += 1
    
    # Summary
    duration = datetime.now() - start_time
    logger.info("")
    logger.info("="*80)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("="*80)
    
    summary = downloader.get_progress_summary()
    logger.info(f"Results:")
    logger.info(f"  Total tickers: {summary['total']}")
    logger.info(f"  Completed: {summary['completed']} ✓")
    logger.info(f"  Failed: {summary['failed']} ✗")
    logger.info(f"  Pending: {summary['pending']}")
    logger.info(f"  Completion rate: {summary['completion_rate']:.1f}%")
    logger.info(f"  Duration: {duration.total_seconds():.1f}s")
    logger.info(f"  Average: {duration.total_seconds() / len(tickers_to_download):.1f}s per ticker")
    
    if summary['failed'] > 0:
        failed_tickers = tracker.get_failed()
        logger.info(f"\nFailed tickers: {', '.join(failed_tickers)}")
        logger.info("Run with --resume to retry failed downloads")
    
    # Calculate total filings and size
    if summary['completed'] > 0:
        # Load manifest to get detailed stats
        manifest_path = output_path / "manifest.json"
        if manifest_path.exists():
            import json
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            total_filings = 0
            total_size = 0
            
            for ticker_data in manifest.get('tickers', []):
                if ticker_data.get('status') == 'completed':
                    # Read ticker metadata
                    ticker = ticker_data['ticker']
                    metadata_file = output_path / ticker / 'ticker_metadata.json'
                    if metadata_file.exists():
                        with open(metadata_file) as mf:
                            metadata = json.load(mf)
                            total_filings += metadata.get('total_filings', 0)
                            total_size += metadata.get('total_size_bytes', 0)
            
            logger.info(f"\nData Summary:")
            logger.info(f"  Total filings: {total_filings}")
            logger.info(f"  Total size: {total_size / 1024 / 1024:.1f} MB")
            
            if summary['completed'] > 0:
                logger.info(f"  Average: {total_filings / summary['completed']:.1f} filings/ticker")
                logger.info(f"  Average size: {total_size / summary['completed'] / 1024:.1f} KB/ticker")
            
            logger.info(f"  Storage: {args.output_dir}")
            
            # Size warning
            if total_size > 50_000_000:  # 50MB
                logger.warning(f"\n⚠️  Total size ({total_size / 1024 / 1024:.1f} MB) exceeds 50MB")
                logger.warning("  Consider documenting external storage strategy instead of git")
    
    logger.info("\nNext Steps:")
    logger.info("  1. Review downloaded filings in data/raw/sec_filings/")
    logger.info("  2. Implement text extraction for analysis")
    logger.info("  3. Create unified Azure uploader script")
    
    return 0 if failed_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
