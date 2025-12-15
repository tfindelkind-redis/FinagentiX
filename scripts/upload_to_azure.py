#!/usr/bin/env python3
"""
Upload Data to Azure Blob Storage

This script uploads stock data, news articles, and SEC filings to Azure Blob Storage.
It supports uploading specific data types or all data types with progress tracking.

Usage:
    python upload_to_azure.py --all
    python upload_to_azure.py --type stock_data
    python upload_to_azure.py --type news_articles
    python upload_to_azure.py --type sec_filings
    python upload_to_azure.py --storage-account <storage-account-name> --resource-group finagentix-dev-rg

Requirements:
    - Azure CLI installed and authenticated (az login)
    - azure-storage-blob package: pip install azure-storage-blob
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

try:
    from azure.storage.blob import BlobServiceClient, ContentSettings
    from azure.identity import DefaultAzureCredential
except ImportError:
    print("Error: azure-storage-blob not installed. Run: pip install azure-storage-blob azure-identity")
    sys.exit(1)


load_dotenv()


def require_env(name: str) -> str:
    """Fetch required environment variable"""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


class AzureUploader:
    """Upload financial data to Azure Blob Storage"""
    
    # Container mappings
    CONTAINER_MAP = {
        'stock_data': 'stock-data',
        'news_articles': 'news-articles',
        'sec_filings': 'sec-filings'
    }
    
    # Data type configurations
    DATA_CONFIGS = {
        'stock_data': {
            'local_path': 'data/raw/stock_data',
            'container': 'stock-data',
            'description': 'Stock market data (OHLCV)'
        },
        'news_articles': {
            'local_path': 'data/raw/news_articles',
            'container': 'news-articles',
            'description': 'Financial news articles'
        },
        'sec_filings': {
            'local_path': 'data/raw/sec_filings',
            'container': 'sec-filings',
            'description': 'SEC filings (10-K, 10-Q, 8-K)'
        }
    }
    
    def __init__(self, storage_account: str, resource_group: str, use_key: bool = False):
        """
        Initialize Azure uploader
        
        Args:
            storage_account: Azure storage account name
            resource_group: Azure resource group name
            use_key: Use storage account key instead of Azure AD (default: False)
        """
        self.storage_account = storage_account
        self.resource_group = resource_group
        self.use_key = use_key
        self.blob_service_client = None
        self.stats = {
            'total_files': 0,
            'total_bytes': 0,
            'uploaded_files': 0,
            'uploaded_bytes': 0,
            'skipped_files': 0,
            'failed_files': 0,
            'errors': []
        }
        
    def _connect(self) -> None:
        """Connect to Azure Blob Storage"""
        account_url = f"https://{self.storage_account}.blob.core.windows.net"
        
        if self.use_key:
            # Get storage account key using Azure CLI
            import subprocess
            result = subprocess.run(
                ['az', 'storage', 'account', 'keys', 'list',
                 '-g', self.resource_group,
                 '-n', self.storage_account,
                 '--query', '[0].value',
                 '-o', 'tsv'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise Exception(f"Failed to get storage key: {result.stderr}")
            
            account_key = result.stdout.strip()
            from azure.storage.blob import BlobServiceClient
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=account_key
            )
            logging.info(f"Connected to {account_url} using account key")
        else:
            # Use Azure AD authentication
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=credential
            )
            logging.info(f"Connected to {account_url} using Azure AD")
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of a file"""
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
        return md5.hexdigest()
    
    def _get_content_type(self, file_path: Path) -> str:
        """Determine content type based on file extension"""
        extension = file_path.suffix.lower()
        content_types = {
            '.parquet': 'application/vnd.apache.parquet',
            '.json': 'application/json',
            '.md5': 'text/plain',
            '.htm': 'text/html',
            '.html': 'text/html',
            '.txt': 'text/plain',
            '.csv': 'text/csv'
        }
        return content_types.get(extension, 'application/octet-stream')
    
    def _upload_file(self, local_path: Path, blob_name: str, container_name: str, 
                     metadata: Optional[Dict] = None) -> bool:
        """
        Upload a single file to Azure Blob Storage
        
        Args:
            local_path: Local file path
            blob_name: Blob name in Azure
            container_name: Container name
            metadata: Optional metadata dictionary
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(blob_name)
            
            # Check if blob already exists with same checksum
            try:
                properties = blob_client.get_blob_properties()
                if properties.metadata and 'checksum' in properties.metadata:
                    local_checksum = self._calculate_checksum(local_path)
                    if properties.metadata['checksum'] == local_checksum:
                        logging.debug(f"Skipping {blob_name} (already exists with same checksum)")
                        self.stats['skipped_files'] += 1
                        return True
            except Exception:
                pass  # Blob doesn't exist, continue with upload
            
            # Prepare metadata
            file_metadata = metadata or {}
            file_metadata['checksum'] = self._calculate_checksum(local_path)
            file_metadata['upload_timestamp'] = datetime.utcnow().isoformat()
            file_metadata['source'] = 'FinagentiX-ingestion'
            
            # Determine content type
            content_type = self._get_content_type(local_path)
            content_settings = ContentSettings(content_type=content_type)
            
            # Upload file
            with open(local_path, 'rb') as data:
                blob_client.upload_blob(
                    data,
                    overwrite=True,
                    metadata=file_metadata,
                    content_settings=content_settings
                )
            
            file_size = local_path.stat().st_size
            self.stats['uploaded_files'] += 1
            self.stats['uploaded_bytes'] += file_size
            logging.info(f"✓ Uploaded {blob_name} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logging.error(f"✗ Failed to upload {blob_name}: {e}")
            self.stats['failed_files'] += 1
            self.stats['errors'].append(f"{blob_name}: {str(e)}")
            return False
    
    def _upload_ticker_data(self, data_type: str, ticker_dir: Path, container_name: str) -> None:
        """Upload all files for a specific ticker"""
        ticker = ticker_dir.name
        logging.info(f"  Processing {ticker}...")
        
        # Find all files to upload
        files = list(ticker_dir.rglob('*'))
        files = [f for f in files if f.is_file()]
        
        for file_path in files:
            # Calculate blob name (relative path from ticker directory)
            rel_path = file_path.relative_to(ticker_dir.parent)
            blob_name = str(rel_path).replace('\\', '/')
            
            # Don't pass file content as metadata - Azure metadata must be string key-value pairs
            # The file itself will be uploaded with proper content type
            self._upload_file(file_path, blob_name, container_name, None)
    
    def upload_data_type(self, data_type: str) -> bool:
        """
        Upload all data for a specific data type
        
        Args:
            data_type: One of 'stock_data', 'news_articles', 'sec_filings'
            
        Returns:
            True if upload successful, False otherwise
        """
        if data_type not in self.DATA_CONFIGS:
            logging.error(f"Unknown data type: {data_type}")
            return False
        
        config = self.DATA_CONFIGS[data_type]
        local_path = Path(config['local_path'])
        container_name = config['container']
        
        if not local_path.exists():
            logging.error(f"Data directory not found: {local_path}")
            return False
        
        logging.info(f"\n{'='*80}")
        logging.info(f"Uploading {data_type.upper()}")
        logging.info(f"{'='*80}")
        logging.info(f"Description: {config['description']}")
        logging.info(f"Local path: {local_path}")
        logging.info(f"Container: {container_name}")
        logging.info("")
        
        # Count total files
        all_files = list(local_path.rglob('*'))
        all_files = [f for f in all_files if f.is_file()]
        self.stats['total_files'] += len(all_files)
        total_size = sum(f.stat().st_size for f in all_files)
        self.stats['total_bytes'] += total_size
        
        logging.info(f"Found {len(all_files)} files ({total_size / (1024*1024):.1f} MB)")
        
        # Upload manifest first if it exists
        manifest_path = local_path / 'manifest.json'
        if manifest_path.exists():
            self._upload_file(manifest_path, f'{data_type}/manifest.json', container_name)
        
        # Upload ticker-specific data
        ticker_dirs = [d for d in local_path.iterdir() if d.is_dir()]
        for i, ticker_dir in enumerate(ticker_dirs, 1):
            logging.info(f"[{i}/{len(ticker_dirs)}] {ticker_dir.name}")
            self._upload_ticker_data(data_type, ticker_dir, container_name)
        
        return True
    
    def upload_all(self) -> bool:
        """Upload all data types"""
        success = True
        for data_type in self.DATA_CONFIGS.keys():
            if not self.upload_data_type(data_type):
                success = False
        return success
    
    def print_summary(self) -> None:
        """Print upload summary"""
        logging.info(f"\n{'='*80}")
        logging.info("UPLOAD SUMMARY")
        logging.info(f"{'='*80}")
        logging.info(f"Total files:     {self.stats['total_files']}")
        logging.info(f"Uploaded:        {self.stats['uploaded_files']} ✓")
        logging.info(f"Skipped:         {self.stats['skipped_files']} (already exist)")
        logging.info(f"Failed:          {self.stats['failed_files']} ✗")
        logging.info(f"Total size:      {self.stats['total_bytes'] / (1024*1024):.1f} MB")
        logging.info(f"Uploaded size:   {self.stats['uploaded_bytes'] / (1024*1024):.1f} MB")
        
        if self.stats['failed_files'] > 0:
            logging.error(f"\nErrors:")
            for error in self.stats['errors'][:10]:  # Show first 10 errors
                logging.error(f"  - {error}")
            if len(self.stats['errors']) > 10:
                logging.error(f"  ... and {len(self.stats['errors']) - 10} more errors")
        
        success_rate = (self.stats['uploaded_files'] / self.stats['total_files'] * 100) if self.stats['total_files'] > 0 else 0
        logging.info(f"\nSuccess rate: {success_rate:.1f}%")


def main():
    parser = argparse.ArgumentParser(
        description='Upload financial data to Azure Blob Storage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload all data types
  python upload_to_azure.py --all
  
  # Upload specific data type
  python upload_to_azure.py --type stock_data
  python upload_to_azure.py --type news_articles
  python upload_to_azure.py --type sec_filings
  
  # Specify custom storage account
  python upload_to_azure.py --all --storage-account myaccount --resource-group myrg
  
  # Use storage account key instead of Azure AD
  python upload_to_azure.py --all --use-key
        """
    )
    
    parser.add_argument(
        '--type',
        choices=['stock_data', 'news_articles', 'sec_filings'],
        help='Data type to upload (use --all to upload all types)'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Upload all data types'
    )
    
    parser.add_argument(
        '--storage-account',
        default=os.getenv('AZURE_STORAGE_ACCOUNT_NAME'),
        help='Azure storage account name (defaults to AZURE_STORAGE_ACCOUNT_NAME)'
    )
    
    parser.add_argument(
        '--resource-group',
        default='finagentix-dev-rg',
        help='Azure resource group name (default: finagentix-dev-rg)'
    )
    
    parser.add_argument(
        '--use-key',
        action='store_true',
        help='Use storage account key instead of Azure AD authentication'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()

    if not args.storage_account:
        args.storage_account = require_env('AZURE_STORAGE_ACCOUNT_NAME')
    
    # Validate arguments
    if not args.all and not args.type:
        parser.error("Must specify either --all or --type")
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Create log file
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f'azure_upload_{timestamp}.log'
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    logging.getLogger().addHandler(file_handler)
    
    logging.info(f"Logging to: {log_file}")
    logging.info(f"{'='*80}")
    logging.info("AZURE BLOB STORAGE UPLOAD")
    logging.info(f"{'='*80}")
    logging.info(f"Storage account: {args.storage_account}")
    logging.info(f"Resource group: {args.resource_group}")
    logging.info(f"Authentication: {'Account Key' if args.use_key else 'Azure AD'}")
    
    try:
        # Initialize uploader
        uploader = AzureUploader(
            storage_account=args.storage_account,
            resource_group=args.resource_group,
            use_key=args.use_key
        )
        
        # Connect to Azure
        uploader._connect()
        
        # Upload data
        start_time = datetime.now()
        
        if args.all:
            success = uploader.upload_all()
        else:
            success = uploader.upload_data_type(args.type)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Print summary
        uploader.print_summary()
        logging.info(f"\nDuration: {duration:.1f}s")
        
        if success:
            logging.info("\n✅ Upload completed successfully!")
            return 0
        else:
            logging.error("\n❌ Upload completed with errors")
            return 1
            
    except Exception as e:
        logging.error(f"\n❌ Upload failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
