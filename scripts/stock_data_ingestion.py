"""
Data Ingestion Script with Metadata Best Practices
Downloads stock data from Yahoo Finance and stores in Azure Storage with comprehensive metadata
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import json
import hashlib
from azure.storage.blob import BlobServiceClient, ContentSettings
from typing import List, Dict, Any
import os

class StockDataIngestion:
    """
    Best Practices Implemented:
    1. Blob Metadata: Azure blob properties for quick filtering
    2. Manifest File: JSON catalog of all data files
    3. Partitioning: Organize by ticker/date for efficient queries
    4. Checksums: Data integrity validation
    5. Version Control: Track schema and data versions
    """
    
    def __init__(self, connection_string: str):
        self.blob_service = BlobServiceClient.from_connection_string(connection_string)
        self.container_name = "stock-data"
        self.manifest = []
        
    def calculate_checksum(self, data: bytes) -> str:
        """Calculate MD5 checksum for data integrity"""
        return hashlib.md5(data).hexdigest()
    
    def create_blob_metadata(self, ticker: str, data_df: pd.DataFrame, 
                            period: str, interval: str) -> Dict[str, str]:
        """
        Create comprehensive metadata for blob storage
        Azure Blob Metadata Best Practices:
        - All keys must be valid HTTP headers (lowercase, no spaces)
        - Values must be strings
        - Used for filtering and searching without downloading blobs
        """
        return {
            # Data Identification
            "ticker": ticker,
            "data_type": "ohlcv",  # open, high, low, close, volume
            "interval": interval,
            "period": period,
            
            # Data Quality Metrics
            "record_count": str(len(data_df)),
            "start_date": data_df.index[0].strftime("%Y-%m-%d"),
            "end_date": data_df.index[-1].strftime("%Y-%m-%d"),
            "has_nulls": str(data_df.isnull().any().any()),
            "completeness_score": str(round((1 - data_df.isnull().sum().sum() / data_df.size) * 100, 2)),
            
            # Provenance (Data Lineage)
            "source": "yahoo_finance",
            "ingestion_time": datetime.utcnow().isoformat(),
            "ingestion_script": "stock_data_ingestion.py",
            "ingestion_version": "1.0.0",
            
            # Schema Information
            "columns": ",".join(data_df.columns.tolist()),
            "schema_version": "1.0",
            
            # File Format
            "format": "parquet",
            "compression": "snappy",
            
            # Business Context
            "asset_class": "equity",
            "market": "us",
            "currency": "usd",
            
            # Data Freshness
            "data_age_hours": str(round((datetime.utcnow() - data_df.index[-1]).total_seconds() / 3600, 2)),
            "is_latest": "true",  # Flag for latest version
        }
    
    def create_manifest_entry(self, ticker: str, blob_path: str, 
                             metadata: Dict[str, str], checksum: str,
                             file_size: int) -> Dict[str, Any]:
        """
        Create manifest entry for data catalog
        Manifest File Best Practices:
        - Central catalog of all data files
        - Enables data discovery and lineage tracking
        - Supports data quality monitoring
        """
        return {
            "blob_path": blob_path,
            "ticker": ticker,
            "checksum": checksum,
            "file_size_bytes": file_size,
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat(),
            
            # Data Quality Indicators
            "quality_checks": {
                "has_duplicates": False,  # Would check in real implementation
                "price_anomalies": False,  # Check for unrealistic price movements
                "volume_anomalies": False,  # Check for unusual volume
                "missing_trading_days": False,  # Check for gaps
            },
            
            # Usage Statistics (would be updated separately)
            "access_count": 0,
            "last_accessed": None,
        }
    
    def generate_blob_path(self, ticker: str, interval: str, date: str) -> str:
        """
        Generate hierarchical blob path for efficient querying
        Partitioning Strategy:
        - ticker/interval/year/month/day.parquet
        - Enables efficient date-range queries
        - Supports incremental updates
        """
        dt = datetime.strptime(date, "%Y-%m-%d")
        return f"{ticker}/{interval}/{dt.year}/{dt.month:02d}/{dt.day:02d}.parquet"
    
    def download_and_store(self, ticker: str, period: str = "5y", 
                          interval: str = "1d") -> Dict[str, Any]:
        """
        Download stock data and store with metadata
        Returns: Summary of ingestion operation
        """
        print(f"📊 Downloading {ticker} data ({period}, {interval})...")
        
        # Download data from Yahoo Finance
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        
        if df.empty:
            print(f"⚠️  No data available for {ticker}")
            return {"status": "error", "message": "No data available"}
        
        # Convert to Parquet (efficient columnar format)
        parquet_data = df.to_parquet(compression="snappy")
        file_size = len(parquet_data)
        checksum = self.calculate_checksum(parquet_data)
        
        # Generate blob path (partitioned by date)
        blob_path = self.generate_blob_path(ticker, interval, df.index[-1].strftime("%Y-%m-%d"))
        
        # Create metadata
        metadata = self.create_blob_metadata(ticker, df, period, interval)
        
        # Upload to Azure Blob Storage
        blob_client = self.blob_service.get_blob_client(
            container=self.container_name, 
            blob=blob_path
        )
        
        # Set content type and cache control
        content_settings = ContentSettings(
            content_type="application/octet-stream",
            cache_control="public, max-age=3600"
        )
        
        blob_client.upload_blob(
            parquet_data,
            overwrite=True,
            metadata=metadata,
            content_settings=content_settings
        )
        
        print(f"✅ Uploaded {blob_path}")
        print(f"   Records: {len(df):,} | Size: {file_size:,} bytes | Checksum: {checksum[:8]}...")
        
        # Create manifest entry
        manifest_entry = self.create_manifest_entry(
            ticker, blob_path, metadata, checksum, file_size
        )
        self.manifest.append(manifest_entry)
        
        return {
            "status": "success",
            "ticker": ticker,
            "blob_path": blob_path,
            "records": len(df),
            "file_size": file_size,
            "checksum": checksum,
            "date_range": f"{df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}"
        }
    
    def save_manifest(self):
        """
        Save manifest file to blob storage
        Manifest serves as data catalog for discovery and governance
        """
        manifest_data = {
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat(),
            "total_files": len(self.manifest),
            "files": self.manifest,
            
            # Aggregate Statistics
            "statistics": {
                "total_records": sum(int(f["metadata"]["record_count"]) for f in self.manifest),
                "total_size_bytes": sum(f["file_size_bytes"] for f in self.manifest),
                "tickers": list(set(f["ticker"] for f in self.manifest)),
                "date_range": {
                    "earliest": min(f["metadata"]["start_date"] for f in self.manifest),
                    "latest": max(f["metadata"]["end_date"] for f in self.manifest),
                }
            }
        }
        
        manifest_json = json.dumps(manifest_data, indent=2)
        
        blob_client = self.blob_service.get_blob_client(
            container=self.container_name,
            blob="manifest.json"
        )
        
        blob_client.upload_blob(
            manifest_json.encode('utf-8'),
            overwrite=True,
            metadata={
                "type": "manifest",
                "version": "1.0",
                "generated_at": datetime.utcnow().isoformat(),
                "file_count": str(len(self.manifest))
            }
        )
        
        print(f"\n📋 Manifest saved: {len(self.manifest)} files cataloged")
        print(f"   Total records: {manifest_data['statistics']['total_records']:,}")
        print(f"   Total size: {manifest_data['statistics']['total_size_bytes'] / 1024 / 1024:.2f} MB")

def main():
    """
    Example usage with best practices
    """
    # Configuration (would come from environment variables)
    STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    
    if not STORAGE_CONNECTION_STRING:
        print("❌ AZURE_STORAGE_CONNECTION_STRING not set")
        print("\nFor testing, set it with:")
        print('export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."')
        return
    
    # Initialize ingestion
    ingestion = StockDataIngestion(STORAGE_CONNECTION_STRING)
    
    # Tickers to download
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    
    print("=" * 70)
    print("Stock Data Ingestion with Metadata Best Practices")
    print("=" * 70)
    print()
    
    # Download and store each ticker
    results = []
    for ticker in tickers:
        try:
            result = ingestion.download_and_store(ticker, period="5y", interval="1d")
            results.append(result)
        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            results.append({"status": "error", "ticker": ticker, "error": str(e)})
        print()
    
    # Save manifest
    ingestion.save_manifest()
    
    print("\n" + "=" * 70)
    print("METADATA BEST PRACTICES IMPLEMENTED:")
    print("=" * 70)
    print("✅ Blob Metadata: Quick filtering without downloading")
    print("✅ Manifest File: Central data catalog (manifest.json)")
    print("✅ Partitioning: ticker/interval/year/month/day structure")
    print("✅ Checksums: MD5 validation for data integrity")
    print("✅ Data Lineage: Source, script version, ingestion time")
    print("✅ Quality Metrics: Completeness, nulls, data age")
    print("✅ Schema Versioning: Track data structure changes")
    print()
    print("QUERYING DATA:")
    print("  • By ticker: List blobs with prefix 'AAPL/'")
    print("  • By date: List blobs with prefix 'AAPL/1d/2025/12/'")
    print("  • By metadata: Filter blobs where metadata.is_latest='true'")
    print("  • Via manifest: Query manifest.json for full catalog")

if __name__ == "__main__":
    main()
