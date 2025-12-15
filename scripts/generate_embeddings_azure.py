#!/usr/bin/env python3
"""
Generate embeddings from Azure Storage and index in Redis

This script reads SEC filings and news articles directly from Azure Blob Storage,
generates embeddings using Azure OpenAI, and stores them in Redis with vector indexes.
"""

import os
import json
import hashlib
from typing import List, Dict, Any
from dataclasses import dataclass
import time
from datetime import datetime
from dotenv import load_dotenv


load_dotenv()


def require_env(name: str) -> str:
    """Fetch required environment variable"""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

from azure.storage.blob import BlobServiceClient
import redis
from redis.commands.search.field import VectorField, TextField, TagField, NumericField
try:
    from redis.commands.search.indexDefinition import IndexDefinition, IndexType
except ImportError:
    from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
import numpy as np
from openai import AzureOpenAI
from bs4 import BeautifulSoup
import pandas as pd


@dataclass
class Config:
    """Configuration for the embedding pipeline"""
    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_key: str
    # Redis
    redis_host: str
    redis_port: int
    redis_password: str
    # Azure Storage
    storage_account_name: str
    storage_account_key: str
    # Optional parameters with defaults
    embedding_deployment: str = 'text-embedding-3-large'
    api_version: str = '2024-08-01-preview'
    embedding_dim: int = 3072
    max_chunk_tokens: int = 8000
    rate_limit_delay: float = 0.1


class AzureStorageReader:
    """Reads data from Azure Blob Storage"""
    
    def __init__(self, account_name: str, account_key: str):
        connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    def list_tickers(self, container_name: str) -> List[str]:
        """List all tickers in a container"""
        container_client = self.blob_service_client.get_container_client(container_name)
        tickers = set()
        
        for blob in container_client.list_blobs():
            # Extract ticker from path like "AAPL/10-K/file.htm"
            parts = blob.name.split('/')
            if len(parts) > 0:
                tickers.add(parts[0])
        
        return sorted(list(tickers))
    
    def read_sec_filing(self, ticker: str, filing_type: str) -> Dict[str, Any]:
        """Read SEC filing from Azure Storage"""
        container_client = self.blob_service_client.get_container_client('sec-filings')
        
        # Read the HTML file
        blob_name = f"{ticker}/{filing_type}/000032019325000079.htm" if filing_type == "10-K" else f"{ticker}/{filing_type}/000032019325000073.htm"
        
        try:
            blob_client = container_client.get_blob_client(blob_name)
            html_content = blob_client.download_blob().readall().decode('utf-8')
        except:
            # Try to find any .htm file in the directory
            blobs = container_client.list_blobs(name_starts_with=f"{ticker}/{filing_type}/")
            for blob in blobs:
                if blob.name.endswith('.htm'):
                    blob_client = container_client.get_blob_client(blob.name)
                    html_content = blob_client.download_blob().readall().decode('utf-8')
                    break
            else:
                return None
        
        # Read metadata
        metadata = {}
        try:
            meta_blob = container_client.get_blob_client(f"{ticker}/{filing_type}/filing_metadata.json")
            metadata = json.loads(meta_blob.download_blob().readall())
        except:
            pass
        
        return {
            'html': html_content,
            'metadata': metadata,
            'ticker': ticker,
            'filing_type': filing_type
        }
    
    def read_news_articles(self, ticker: str) -> List[Dict]:
        """Read news articles from Azure Storage"""
        container_client = self.blob_service_client.get_container_client('news-articles')
        
        try:
            blob_client = container_client.get_blob_client(f"{ticker}/articles_recent.parquet")
            parquet_data = blob_client.download_blob().readall()
            
            # Write to temp file and read with pandas
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
                tmp.write(parquet_data)
                tmp_path = tmp.name
            
            df = pd.read_parquet(tmp_path)
            os.unlink(tmp_path)
            
            return df.to_dict('records')
        except Exception as e:
            print(f"    ⚠️  Could not read news for {ticker}: {e}")
            return []


class EmbeddingPipeline:
    """Main pipeline for generating and storing embeddings"""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Initialize clients
        self.openai_client = AzureOpenAI(
            api_key=config.azure_openai_key,
            api_version=config.api_version,
            azure_endpoint=config.azure_openai_endpoint
        )
        
        self.redis_client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            password=config.redis_password,
            decode_responses=False,
            ssl=True,
            ssl_cert_reqs='required'
        )
        
        self.storage = AzureStorageReader(
            config.storage_account_name,
            config.storage_account_key
        )
        
        print(f"✅ Connected to Redis at {config.redis_host}:{config.redis_port}")
        print(f"✅ Connected to Azure Storage: {config.storage_account_name}")
    
    def create_indexes(self):
        """Create Redis vector indexes"""
        self._create_sec_filing_index()
        self._create_news_index()
        self._create_semantic_cache_index()
    
    def _create_sec_filing_index(self):
        """Create vector index for SEC filings"""
        index_name = "idx:sec_filings"
        
        try:
            self.redis_client.ft(index_name).info()
            print(f"ℹ️  Index {index_name} already exists")
            return
        except:
            pass
        
        schema = (
            TextField("$.ticker", as_name="ticker"),
            TextField("$.filing_type", as_name="filing_type"),
            TextField("$.filing_date", as_name="filing_date"),
            TextField("$.content", as_name="content"),
            NumericField("$.chunk_index", as_name="chunk_index"),
            TagField("$.ticker_tag", as_name="ticker_tag"),
            VectorField(
                "$.embedding",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": self.config.embedding_dim,
                    "DISTANCE_METRIC": "COSINE",
                    "INITIAL_CAP": 2000,
                },
                as_name="embedding"
            ),
        )
        
        definition = IndexDefinition(prefix=["sec:"], index_type=IndexType.JSON)
        self.redis_client.ft(index_name).create_index(fields=schema, definition=definition)
        print(f"✅ Created index: {index_name}")
    
    def _create_news_index(self):
        """Create vector index for news articles"""
        index_name = "idx:news_articles"
        
        try:
            self.redis_client.ft(index_name).info()
            print(f"ℹ️  Index {index_name} already exists")
            return
        except:
            pass
        
        schema = (
            TextField("$.ticker", as_name="ticker"),
            TextField("$.title", as_name="title"),
            TextField("$.content", as_name="content"),
            TagField("$.ticker_tag", as_name="ticker_tag"),
            VectorField(
                "$.embedding",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": self.config.embedding_dim,
                    "DISTANCE_METRIC": "COSINE",
                    "INITIAL_CAP": 500,
                },
                as_name="embedding"
            ),
        )
        
        definition = IndexDefinition(prefix=["news:"], index_type=IndexType.JSON)
        self.redis_client.ft(index_name).create_index(fields=schema, definition=definition)
        print(f"✅ Created index: {index_name}")
    
    def _create_semantic_cache_index(self):
        """Create index for semantic caching"""
        index_name = "idx:semantic_cache"
        
        try:
            self.redis_client.ft(index_name).info()
            print(f"ℹ️  Index {index_name} already exists")
            return
        except:
            pass
        
        schema = (
            TextField("$.query", as_name="query"),
            TextField("$.model", as_name="model"),
            NumericField("$.timestamp", as_name="timestamp"),
            VectorField(
                "$.query_embedding",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": self.config.embedding_dim,
                    "DISTANCE_METRIC": "COSINE",
                    "INITIAL_CAP": 10000,
                },
                as_name="query_embedding"
            ),
        )
        
        definition = IndexDefinition(prefix=["cache:"], index_type=IndexType.JSON)
        self.redis_client.ft(index_name).create_index(fields=schema, definition=definition)
        print(f"✅ Created index: {index_name}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        time.sleep(self.config.rate_limit_delay)
        
        # text-embedding-3-large supports up to 8191 tokens
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = 8000 * 4  # 32,000 chars ≈ 8000 tokens
        
        response = self.openai_client.embeddings.create(
            input=text[:max_chars],
            model=self.config.embedding_deployment
        )
        
        return response.data[0].embedding
    
    def extract_text_from_html(self, html: str) -> str:
        """Extract clean text from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def chunk_text(self, text: str, max_chars: int = 24000) -> List[str]:
        """Split text into chunks (safe margin for 8K token limit, ~6K tokens)"""
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1
            if current_length + word_length > max_chars:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def process_sec_filing(self, ticker: str, filing_type: str) -> int:
        """Process a single SEC filing"""
        filing_data = self.storage.read_sec_filing(ticker, filing_type)
        if not filing_data:
            return 0
        
        text = self.extract_text_from_html(filing_data['html'])
        chunks = self.chunk_text(text)
        
        filing_date = filing_data['metadata'].get('filing_date', 'unknown')
        
        for idx, chunk in enumerate(chunks):
            if len(chunk.strip()) < 200:
                continue
            
            embedding = self.generate_embedding(chunk)
            
            doc_id = f"sec:{ticker}:{filing_type}:{idx}"
            doc_data = {
                "ticker": ticker,
                "ticker_tag": ticker,
                "filing_type": filing_type,
                "filing_date": filing_date,
                "content": chunk[:5000],
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "embedding": embedding,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            self.redis_client.json().set(doc_id, '$', doc_data)
        
        return len(chunks)
    
    def process_news_articles(self, ticker: str) -> int:
        """Process news articles for a ticker"""
        articles = self.storage.read_news_articles(ticker)
        count = 0
        
        for article in articles:
            title = str(article.get('title', ''))
            content = str(article.get('summary', ''))
            
            full_text = f"{title}\n\n{content}"
            if len(full_text.strip()) < 50:
                continue
            
            embedding = self.generate_embedding(full_text)
            
            article_id = hashlib.md5(full_text.encode()).hexdigest()[:16]
            doc_id = f"news:{ticker}:{article_id}"
            
            doc_data = {
                "ticker": ticker,
                "ticker_tag": ticker,
                "title": title,
                "content": content[:2000],
                "embedding": embedding,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            self.redis_client.json().set(doc_id, '$', doc_data)
            count += 1
        
        return count
    
    def process_all_data(self, limit_tickers: int = None):
        """Process all SEC filings and news articles"""
        tickers = self.storage.list_tickers('sec-filings')
        
        if limit_tickers:
            tickers = tickers[:limit_tickers]
        
        print(f"\n📊 Processing {len(tickers)} tickers...")
        
        total_sec_chunks = 0
        total_news = 0
        
        for ticker in tickers:
            print(f"\n  Processing {ticker}...")
            
            # SEC filings
            for filing_type in ['10-K', '10-Q']:
                try:
                    chunks = self.process_sec_filing(ticker, filing_type)
                    total_sec_chunks += chunks
                    print(f"    ✅ {filing_type}: {chunks} chunks")
                except Exception as e:
                    print(f"    ❌ {filing_type}: {str(e)}")
            
            # News articles
            try:
                count = self.process_news_articles(ticker)
                total_news += count
                print(f"    ✅ News: {count} articles")
            except Exception as e:
                print(f"    ❌ News: {str(e)}")
        
        print(f"\n" + "=" * 60)
        print(f"✅ Processing complete!")
        print(f"   SEC filings: {total_sec_chunks} chunks")
        print(f"   News articles: {total_news} articles")
        print("=" * 60)


def main():
    """Main execution"""
    print("=" * 60)
    print("FinagentiX - Embedding Generation from Azure Storage")
    print("=" * 60)
    
    config = Config(
        azure_openai_endpoint=require_env('AZURE_OPENAI_ENDPOINT'),
        azure_openai_key=require_env('AZURE_OPENAI_API_KEY'),
        redis_host=require_env('REDIS_HOST'),
        redis_port=int(require_env('REDIS_PORT')),
        redis_password=os.getenv('REDIS_PASSWORD'),
        storage_account_name=require_env('AZURE_STORAGE_ACCOUNT_NAME'),
        storage_account_key=require_env('AZURE_STORAGE_ACCOUNT_KEY'),
        embedding_deployment=require_env('AZURE_OPENAI_EMBEDDING_DEPLOYMENT'),
        api_version=require_env('AZURE_OPENAI_API_VERSION')
    )
    
    # Get storage key if not provided
    if not config.storage_account_key:
        import subprocess
        result = subprocess.run(
            ['az', 'storage', 'account', 'keys', 'list',
             '-g', 'finagentix-dev-rg',
             '-n', config.storage_account_name,
             '--query', '[0].value', '-o', 'tsv'],
            capture_output=True, text=True
        )
        config.storage_account_key = result.stdout.strip()
    
    pipeline = EmbeddingPipeline(config)
    
    print("\n📊 Creating vector indexes...")
    pipeline.create_indexes()
    
    # Process first 3 tickers as a test
    print("\n🚀 Starting embedding generation (first 3 tickers)...")
    pipeline.process_all_data(limit_tickers=3)


if __name__ == "__main__":
    main()
