#!/usr/bin/env python3
"""
Generate and load embeddings for SEC filings and news articles into Redis.

This script processes SEC filings and news articles from local files,
generates embeddings using Azure OpenAI, and stores them in Redis with
HNSW vector indexes for semantic search.

Usage:
    python scripts/load_embeddings.py --help
    python scripts/load_embeddings.py --dry-run
    python scripts/load_embeddings.py --sec-filings
    python scripts/load_embeddings.py --news
    python scripts/load_embeddings.py --all
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
from openai import AzureOpenAI


class EmbeddingLoader:
    """Load embeddings for SEC filings and news into Redis."""

    def __init__(
        self,
        redis_host: str,
        redis_port: int,
        redis_password: str,
        openai_endpoint: str,
        openai_key: str,
        openai_deployment: str = "text-embedding-3-large",
        data_dir: str = "data/raw",
    ):
        """Initialize the loader.
        
        Args:
            redis_host: Redis host
            redis_port: Redis port
            redis_password: Redis password
            openai_endpoint: Azure OpenAI endpoint
            openai_key: Azure OpenAI API key
            openai_deployment: Model deployment name
            data_dir: Data directory path
        """
        self.data_dir = Path(data_dir)
        
        # Redis connection
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            decode_responses=False,  # Binary mode for vectors
            ssl=True,
            ssl_cert_reqs=None,
        )
        
        # Test connection
        try:
            self.redis_client.ping()
            print(f"✅ Connected to Redis at {redis_host}:{redis_port}")
        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
            sys.exit(1)
        
        # Azure OpenAI connection
        self.openai_client = AzureOpenAI(
            azure_endpoint=openai_endpoint,
            api_key=openai_key,
            api_version="2024-08-01-preview",
        )
        self.embedding_deployment = openai_deployment
        
        print(f"✅ Connected to Azure OpenAI: {openai_endpoint}")
        print(f"   Deployment: {openai_deployment}")

    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Azure OpenAI."""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.embedding_deployment,
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"  ⚠️  Failed to generate embedding: {e}")
            return None

    def create_vector_index(self, index_name: str, vector_dim: int = 3072):
        """Create HNSW vector index in Redis if it doesn't exist."""
        try:
            # Check if index exists
            self.redis_client.ft(index_name).info()
            print(f"  ℹ️  Index already exists: {index_name}")
        except redis.exceptions.ResponseError:
            # Create index with HNSW algorithm
            try:
                from redis.commands.search.field import TextField, VectorField, NumericField
                from redis.commands.search.indexDefinition import IndexDefinition, IndexType
            except (ImportError, ModuleNotFoundError):
                # Fallback for different redis-py versions
                from redis.commands.search.field import TextField, VectorField, NumericField
                from redis.commands.search import IndexDefinition, IndexType
            
            schema = (
                TextField("content"),
                TextField("ticker"),
                TextField("source"),
                NumericField("timestamp"),
                VectorField(
                    "embedding",
                    "HNSW",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": vector_dim,
                        "DISTANCE_METRIC": "COSINE",
                    },
                ),
            )
            
            definition = IndexDefinition(prefix=[f"{index_name}:"], index_type=IndexType.HASH)
            
            self.redis_client.ft(index_name).create_index(
                fields=schema,
                definition=definition,
            )
            print(f"  ✅ Created vector index: {index_name}")

    def load_news_articles(self, dry_run: bool = False) -> Dict:
        """Load news articles with embeddings."""
        news_dir = self.data_dir / "news_articles"
        
        if not news_dir.exists():
            return {"status": "error", "message": "News directory not found"}
        
        # Get all tickers with news
        tickers = [d.name for d in news_dir.iterdir() if d.is_dir()]
        
        print(f"\n📰 Processing news articles for {len(tickers)} tickers...")
        
        if dry_run:
            total_articles = 0
            for ticker in tickers:
                parquet_file = news_dir / ticker / "articles_recent.parquet"
                if parquet_file.exists():
                    df = pd.read_parquet(parquet_file)
                    total_articles += len(df)
            print(f"  [DRY RUN] Would process {total_articles} news articles")
            return {"status": "dry_run", "tickers": len(tickers), "articles": total_articles}
        
        # Create vector index
        self.create_vector_index("news_idx", vector_dim=3072)
        
        total_loaded = 0
        errors = 0
        
        for i, ticker in enumerate(tickers, 1):
            print(f"\n[{i}/{len(tickers)}] {ticker}")
            
            parquet_file = news_dir / ticker / "articles_recent.parquet"
            metadata_file = news_dir / ticker / "metadata.json"
            
            if not parquet_file.exists():
                print(f"  ⚠️  No articles found")
                continue
            
            # Load articles
            df = pd.read_parquet(parquet_file)
            
            # Load metadata
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
            
            print(f"  Articles: {len(df)}")
            
            for idx, row in df.iterrows():
                # Combine title and content for embedding
                text = f"{row.get('title', '')} {row.get('description', '')}"
                
                if not text.strip():
                    continue
                
                # Generate embedding
                embedding = self.get_embedding(text)
                if not embedding:
                    errors += 1
                    continue
                
                # Store in Redis
                key = f"news_idx:{ticker}:{idx}"
                
                import numpy as np
                embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
                
                self.redis_client.hset(
                    key,
                    mapping={
                        "content": text[:1000],  # Truncate for storage
                        "ticker": ticker,
                        "source": row.get("source", "unknown"),
                        "timestamp": int(pd.Timestamp(row.get("published", "now")).timestamp()),
                        "embedding": embedding_bytes,
                        "url": row.get("url", ""),
                    },
                )
                
                total_loaded += 1
            
            print(f"  ✅ Loaded {len(df)} articles")
        
        print(f"\n✅ Total news articles loaded: {total_loaded}")
        if errors > 0:
            print(f"⚠️  Errors: {errors}")
        
        return {
            "status": "success",
            "tickers": len(tickers),
            "articles": total_loaded,
            "errors": errors,
        }

    def load_sec_filings(self, dry_run: bool = False) -> Dict:
        """Load SEC filings with embeddings."""
        sec_dir = self.data_dir / "sec_filings"
        
        if not sec_dir.exists():
            return {"status": "error", "message": "SEC filings directory not found"}
        
        # Get all tickers with SEC filings
        tickers = [d.name for d in sec_dir.iterdir() if d.is_dir()]
        
        print(f"\n📑 Processing SEC filings for {len(tickers)} tickers...")
        
        if dry_run:
            total_filings = 0
            for ticker in tickers:
                ticker_meta = sec_dir / ticker / "ticker_metadata.json"
                if ticker_meta.exists():
                    with open(ticker_meta) as f:
                        meta = json.load(f)
                        total_filings += meta.get("total_filings", 0)
            print(f"  [DRY RUN] Would process {total_filings} SEC filings")
            return {"status": "dry_run", "tickers": len(tickers), "filings": total_filings}
        
        # Create vector index
        self.create_vector_index("sec_idx", vector_dim=3072)
        
        total_loaded = 0
        errors = 0
        
        for i, ticker in enumerate(tickers, 1):
            print(f"\n[{i}/{len(tickers)}] {ticker}")
            
            ticker_dir = sec_dir / ticker
            metadata_file = ticker_dir / "ticker_metadata.json"
            
            if not metadata_file.exists():
                print(f"  ⚠️  No metadata found")
                continue
            
            # Load metadata
            with open(metadata_file) as f:
                metadata = json.load(f)
            
            filings = metadata.get("filings", [])
            print(f"  Filings: {len(filings)}")
            
            for filing in filings:
                filing_type = filing.get("form_type")
                filing_date = filing.get("filing_date")
                accession = filing.get("accession_number", "").replace("-", "")
                
                # Look for text file
                text_file = ticker_dir / f"{accession}.txt"
                
                if not text_file.exists():
                    continue
                
                # Read filing text
                with open(text_file, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                
                # Chunk the text (SEC filings can be very long)
                chunk_size = 1500  # characters
                chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
                
                for chunk_idx, chunk in enumerate(chunks[:20]):  # Limit to 20 chunks per filing
                    # Generate embedding
                    embedding = self.get_embedding(chunk)
                    if not embedding:
                        errors += 1
                        continue
                    
                    # Store in Redis
                    key = f"sec_idx:{ticker}:{accession}:{chunk_idx}"
                    
                    import numpy as np
                    embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
                    
                    self.redis_client.hset(
                        key,
                        mapping={
                            "content": chunk[:1000],
                            "ticker": ticker,
                            "source": f"{filing_type} {filing_date}",
                            "timestamp": int(pd.Timestamp(filing_date).timestamp()),
                            "embedding": embedding_bytes,
                            "filing_type": filing_type,
                            "accession": accession,
                        },
                    )
                    
                    total_loaded += 1
                
                print(f"  ✅ Loaded {filing_type} ({len(chunks)} chunks)")
            
        print(f"\n✅ Total SEC filing chunks loaded: {total_loaded}")
        if errors > 0:
            print(f"⚠️  Errors: {errors}")
        
        return {
            "status": "success",
            "tickers": len(tickers),
            "chunks": total_loaded,
            "errors": errors,
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Load embeddings into Redis")
    parser.add_argument(
        "--sec-filings",
        action="store_true",
        help="Load SEC filings embeddings",
    )
    parser.add_argument(
        "--news",
        action="store_true",
        help="Load news articles embeddings",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Load all embeddings (SEC filings + news)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be loaded without actually loading",
    )

    args = parser.parse_args()

    # Get credentials from environment
    redis_host = os.getenv("REDIS_HOST")
    redis_port = int(os.getenv("REDIS_PORT", 10000))
    redis_password = os.getenv("REDIS_PASSWORD")
    
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai_key = os.getenv("AZURE_OPENAI_KEY")

    if not all([redis_host, redis_password, openai_endpoint, openai_key]):
        print("❌ Error: Required environment variables not set")
        print("\nRequired:")
        print("  REDIS_HOST")
        print("  REDIS_PASSWORD")
        print("  AZURE_OPENAI_ENDPOINT")
        print("  AZURE_OPENAI_KEY")
        sys.exit(1)

    loader = EmbeddingLoader(
        redis_host, redis_port, redis_password, openai_endpoint, openai_key
    )

    if args.sec_filings or args.all:
        loader.load_sec_filings(dry_run=args.dry_run)

    if args.news or args.all:
        loader.load_news_articles(dry_run=args.dry_run)

    if not (args.sec_filings or args.news or args.all):
        parser.print_help()


if __name__ == "__main__":
    main()
