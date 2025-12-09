#!/usr/bin/env python3
"""
Load market data from local Parquet files into Redis TimeSeries.

This script reads the existing stock data from data/raw/stock_data/ and
loads it into Redis TimeSeries for real-time feature serving.

Usage:
    python scripts/load_market_data.py --help
    python scripts/load_market_data.py --dry-run
    python scripts/load_market_data.py --ticker AAPL
    python scripts/load_market_data.py --all
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import redis
from redis.commands.timeseries import TimeSeries


class MarketDataLoader:
    """Load market data into Redis TimeSeries."""

    def __init__(
        self,
        redis_host: str,
        redis_port: int,
        redis_password: str,
        data_dir: str = "data/raw/stock_data",
    ):
        """Initialize the loader."""
        self.data_dir = Path(data_dir)
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            decode_responses=True,
        )
        self.ts = self.redis_client.ts()

        # Test connection
        try:
            self.redis_client.ping()
            print(f"✅ Connected to Redis at {redis_host}:{redis_port}")
        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
            sys.exit(1)

    def get_available_tickers(self) -> List[str]:
        """Get list of available tickers from the data directory."""
        manifest_path = self.data_dir / "manifest.json"
        if not manifest_path.exists():
            print(f"❌ Manifest not found at {manifest_path}")
            return []

        with open(manifest_path) as f:
            manifest = json.load(f)

        completed_tickers = [
            t["ticker"] for t in manifest["tickers"] if t["status"] == "completed"
        ]
        return completed_tickers

    def load_ticker_data(self, ticker: str, dry_run: bool = False) -> Dict:
        """Load data for a single ticker into Redis TimeSeries."""
        ticker_dir = self.data_dir / ticker
        parquet_file = ticker_dir / "daily_1y.parquet"
        metadata_file = ticker_dir / "metadata.json"

        if not parquet_file.exists():
            return {"ticker": ticker, "status": "error", "message": "File not found"}

        # Load metadata
        with open(metadata_file) as f:
            metadata = json.load(f)

        # Load parquet data
        df = pd.read_parquet(parquet_file)

        print(f"\n{'🔍' if dry_run else '📊'} Processing {ticker}")
        print(f"  Records: {len(df)}")
        print(f"  Date Range: {metadata['date_range'][0]} to {metadata['date_range'][1]}")

        if dry_run:
            print(f"  [DRY RUN] Would create {len(df) * 5} time series entries")
            return {
                "ticker": ticker,
                "status": "dry_run",
                "records": len(df),
                "series_count": 5,
            }

        # Create time series keys for each metric
        metrics = ["open", "high", "low", "close", "volume"]
        keys_created = []

        for metric in metrics:
            key = f"stock:{ticker}:{metric}"

            # Check if key exists, if so delete it for fresh load
            try:
                self.ts.info(key)
                self.ts.delete(key, 0, int(datetime.now().timestamp() * 1000))
                print(f"  🔄 Cleared existing data for {key}")
            except redis.ResponseError:
                # Key doesn't exist, create it
                try:
                    self.ts.create(
                        key,
                        retention_msecs=0,  # Keep forever
                        duplicate_policy="LAST",
                        labels={
                            "ticker": ticker,
                            "metric": metric,
                            "source": "yahoo_finance",
                            "interval": "1d",
                        },
                    )
                    print(f"  ✅ Created time series: {key}")
                except redis.ResponseError as e:
                    if "key already exists" not in str(e).lower():
                        raise
                    print(f"  ℹ️  Time series exists: {key}")

            keys_created.append(key)

        # Insert data points
        inserted_count = 0
        for _, row in df.iterrows():
            timestamp = int(pd.Timestamp(row["Date"]).timestamp() * 1000)

            for metric in metrics:
                key = f"stock:{ticker}:{metric}"
                value = float(row[metric.capitalize()])

                try:
                    self.ts.add(key, timestamp, value)
                    inserted_count += 1
                except Exception as e:
                    print(f"  ⚠️  Failed to insert {key} at {timestamp}: {e}")

        print(f"  ✅ Inserted {inserted_count} data points across {len(metrics)} series")

        # Create aggregations for common time windows
        self._create_aggregations(ticker, metrics)

        return {
            "ticker": ticker,
            "status": "success",
            "records": len(df),
            "series_count": len(metrics),
            "points_inserted": inserted_count,
        }

    def _create_aggregations(self, ticker: str, metrics: List[str]):
        """Create compacted aggregation rules for common time windows."""
        # Aggregation rules: source -> (aggregation_type, bucket_size_ms)
        aggregations = [
            ("avg", 3600000),  # 1 hour average
            ("avg", 86400000),  # 1 day average
            ("avg", 604800000),  # 1 week average
        ]

        for metric in metrics:
            source_key = f"stock:{ticker}:{metric}"

            for agg_type, bucket_size in aggregations:
                # Skip volume averages (not meaningful)
                if metric == "volume" and agg_type == "avg":
                    continue

                dest_key = f"stock:{ticker}:{metric}:{agg_type}_{bucket_size // 1000}s"

                try:
                    # Check if aggregation already exists
                    try:
                        self.ts.info(dest_key)
                        continue  # Already exists
                    except redis.ResponseError:
                        pass

                    # Create destination time series
                    self.ts.create(
                        dest_key,
                        retention_msecs=0,
                        labels={
                            "ticker": ticker,
                            "metric": metric,
                            "aggregation": agg_type,
                            "bucket": f"{bucket_size}ms",
                        },
                    )

                    # Create aggregation rule
                    self.ts.createrule(source_key, dest_key, agg_type, bucket_size)

                except Exception as e:
                    # Silently skip if rule already exists
                    if "already exists" not in str(e).lower():
                        print(f"  ⚠️  Aggregation warning for {dest_key}: {e}")

    def load_all_tickers(self, dry_run: bool = False) -> Dict:
        """Load all available tickers."""
        tickers = self.get_available_tickers()
        print(f"\n{'🔍' if dry_run else '🚀'} Loading {len(tickers)} tickers...")

        results = []
        for i, ticker in enumerate(tickers, 1):
            print(f"\n[{i}/{len(tickers)}] {ticker}")
            result = self.load_ticker_data(ticker, dry_run=dry_run)
            results.append(result)

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        success_count = sum(1 for r in results if r["status"] == "success")
        error_count = sum(1 for r in results if r["status"] == "error")
        total_points = sum(r.get("points_inserted", 0) for r in results)

        print(f"✅ Successful: {success_count}/{len(results)}")
        if error_count > 0:
            print(f"❌ Failed: {error_count}/{len(results)}")
        if not dry_run:
            print(f"📊 Total data points inserted: {total_points:,}")

        return {"tickers": results, "summary": {"success": success_count, "error": error_count}}

    def verify_data(self, ticker: str) -> Dict:
        """Verify data was loaded correctly."""
        metrics = ["open", "high", "low", "close", "volume"]
        results = {}

        for metric in metrics:
            key = f"stock:{ticker}:{metric}"
            try:
                info = self.ts.info(key)
                count = info.total_samples
                first_ts = info.first_timestamp
                last_ts = info.last_timestamp

                first_date = datetime.fromtimestamp(first_ts / 1000).strftime("%Y-%m-%d")
                last_date = datetime.fromtimestamp(last_ts / 1000).strftime("%Y-%m-%d")

                results[metric] = {
                    "count": count,
                    "first_date": first_date,
                    "last_date": last_date,
                }
            except Exception as e:
                results[metric] = {"error": str(e)}

        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Load market data into Redis TimeSeries")
    parser.add_argument(
        "--ticker",
        type=str,
        help="Load data for a specific ticker (e.g., AAPL)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Load data for all available tickers",
    )
    parser.add_argument(
        "--verify",
        type=str,
        help="Verify data for a specific ticker",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available tickers",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be loaded without actually loading",
    )

    args = parser.parse_args()

    # Get Redis credentials from environment
    redis_host = os.getenv("REDIS_HOST")
    redis_port = int(os.getenv("REDIS_PORT", 10000))
    redis_password = os.getenv("REDIS_PASSWORD")

    if not redis_host or not redis_password:
        print("❌ Error: REDIS_HOST and REDIS_PASSWORD environment variables must be set")
        print("\nExample:")
        print('  export REDIS_HOST="redis-xyz.westus3.redisenterprise.cache.azure.net"')
        print("  export REDIS_PORT=10000")
        print('  export REDIS_PASSWORD="your-password"')
        sys.exit(1)

    loader = MarketDataLoader(redis_host, redis_port, redis_password)

    if args.list:
        tickers = loader.get_available_tickers()
        print(f"\n📊 Available tickers ({len(tickers)}):")
        for ticker in tickers:
            print(f"  • {ticker}")
        return

    if args.verify:
        results = loader.verify_data(args.verify)
        print(f"\n✅ Verification results for {args.verify}:")
        for metric, data in results.items():
            if "error" in data:
                print(f"  ❌ {metric}: {data['error']}")
            else:
                print(f"  ✅ {metric}: {data['count']} points from {data['first_date']} to {data['last_date']}")
        return

    if args.ticker:
        loader.load_ticker_data(args.ticker, dry_run=args.dry_run)
    elif args.all:
        loader.load_all_tickers(dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
