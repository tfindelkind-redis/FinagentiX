#!/usr/bin/env python3
"""
Stock data ingestion script

Downloads historical stock data from Yahoo Finance with robust error handling,
progress tracking, and resume capability.

Usage:
    # Fresh download
    python scripts/download_stock_data.py
    
    # Resume from previous run
    python scripts/download_stock_data.py --resume
    
    # Download specific tickers
    python scripts/download_stock_data.py --tickers AAPL MSFT GOOGL
    
    # Background execution
    nohup python scripts/download_stock_data.py > ingestion.out 2>&1 &
    echo $! > ingestion.pid
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.ingestion.config import get_default_config, IngestionConfig
from scripts.ingestion.progress_tracker import ProgressTracker
from scripts.ingestion.downloader import StockDownloader

def setup_logging(log_dir: str, log_level: str = 'INFO') -> None:
    """Configure logging to file and console"""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_path / f'ingestion_{timestamp}.log'
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(console_formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logging.info(f"Logging to: {log_file}")

def print_summary(tracker: ProgressTracker):
    """Print progress summary"""
    summary = tracker.get_summary()
    
    success_rate = summary.get('success_rate', 0)
    print("\n" + "="*60)
    print("PROGRESS SUMMARY")
    print("="*60)
    print(f"Total:     {summary['total']}")
    print(f"Completed: {summary['completed']} ({success_rate:.1f}% success)")
    print(f"Failed:    {summary['failed']}")
    print(f"Pending:   {summary['pending']}")
    print("="*60 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description='Download stock market data from Yahoo Finance'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from previous run (skip completed tickers)'
    )
    parser.add_argument(
        '--fresh',
        action='store_true',
        help='Fresh start (delete existing data and manifest)'
    )
    parser.add_argument(
        '--tickers',
        nargs='+',
        help='Specific tickers to download (overrides config)'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = get_default_config()
    
    # Override tickers if specified
    if args.tickers:
        config.tickers = args.tickers
    
    # Setup logging
    setup_logging(config.log_dir, args.log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("Stock Data Ingestion Started")
    logger.info("="*60)
    logger.info(f"Tickers: {len(config.tickers)}")
    logger.info(f"Period: {config.period}")
    logger.info(f"Interval: {config.interval}")
    logger.info(f"Output directory: {config.output_dir}")
    
    # Initialize progress tracker
    manifest_path = Path(config.output_dir) / 'manifest.json'
    tracker = ProgressTracker(str(manifest_path), config.tickers)
    
    # Handle fresh start
    if args.fresh:
        logger.info("Fresh start requested - clearing existing data")
        import shutil
        output_path = Path(config.output_dir)
        if output_path.exists():
            shutil.rmtree(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        tracker = ProgressTracker(str(manifest_path), config.tickers)
    
    # Determine which tickers to process
    if args.resume:
        pending_tickers = tracker.get_pending()
        logger.info(f"Resuming: {len(pending_tickers)} pending tickers")
        tickers_to_process = pending_tickers
    else:
        tickers_to_process = config.tickers
    
    if not tickers_to_process:
        logger.info("No tickers to process")
        return
    
    # Initialize downloader
    downloader = StockDownloader(config, tracker)
    
    # Process tickers
    start_time = time.time()
    successful = 0
    failed = 0
    
    for i, ticker in enumerate(tickers_to_process, 1):
        logger.info(f"\n[{i}/{len(tickers_to_process)}] Processing {ticker}")
        
        success = downloader.download_ticker(ticker)
        
        if success:
            successful += 1
        else:
            failed += 1
        
        # Save progress after each ticker
        tracker.save()
        
        # Print progress every 5 tickers
        if i % 5 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed
            remaining = len(tickers_to_process) - i
            eta = remaining / rate if rate > 0 else 0
            
            logger.info(
                f"Progress: {i}/{len(tickers_to_process)} "
                f"({successful} success, {failed} failed) "
                f"- ETA: {eta/60:.1f} min"
            )
        
        # Rate limiting
        if i < len(tickers_to_process):
            time.sleep(config.rate_limit_delay)
    
    # Final summary
    elapsed_total = time.time() - start_time
    logger.info("\n" + "="*60)
    logger.info("INGESTION COMPLETE")
    logger.info("="*60)
    logger.info(f"Total time: {elapsed_total/60:.1f} minutes")
    logger.info(f"Successful: {successful}/{len(tickers_to_process)}")
    logger.info(f"Failed: {failed}/{len(tickers_to_process)}")
    logger.info(f"Output: {config.output_dir}")
    logger.info("="*60)
    
    # Print summary
    print_summary(tracker)
    
    # Exit with error code if any failures
    if failed > 0:
        logger.warning(f"{failed} ticker(s) failed - review logs for details")
        sys.exit(1)

if __name__ == '__main__':
    main()
