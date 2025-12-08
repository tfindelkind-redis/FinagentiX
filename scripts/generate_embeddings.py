"""
Embedding generation and vector indexing for FinagentiX

This script:
1. Reads SEC filings and news articles from local storage
2. Generates embeddings using Azure OpenAI
3. Stores embeddings in Redis with vector indexes
4. Sets up semantic caching infrastructure
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time
from datetime import datetime

import redis
from redis.commands.search.field import VectorField, TextField, TagField, NumericField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
import numpy as np
from openai import AzureOpenAI
from bs4 import BeautifulSoup
from tqdm import tqdm


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation"""
    azure_openai_endpoint: str
    azure_openai_key: str
    azure_openai_api_version: str
    embedding_deployment: str
    redis_host: str
    redis_port: int
    redis_password: str
    chunk_size: int = 8000  # tokens per chunk
    batch_size: int = 10  # documents to process in parallel
    embedding_dim: int = 3072  # text-embedding-3-large dimension


class RedisVectorStore:
    """Manages Redis connection and vector operations"""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.redis_client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            password=config.redis_password,
            decode_responses=False,
            ssl=True,
            ssl_cert_reqs='required'
        )
        print(f"✅ Connected to Redis at {config.redis_host}:{config.redis_port}")
    
    def create_sec_filing_index(self):
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
                    "INITIAL_CAP": 1000,
                },
                as_name="embedding"
            ),
        )
        
        definition = IndexDefinition(
            prefix=["sec:"],
            index_type=IndexType.JSON
        )
        
        self.redis_client.ft(index_name).create_index(
            fields=schema,
            definition=definition
        )
        print(f"✅ Created index: {index_name}")
    
    def create_news_index(self):
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
            TextField("$.published", as_name="published"),
            TextField("$.content", as_name="content"),
            TextField("$.url", as_name="url"),
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
        
        definition = IndexDefinition(
            prefix=["news:"],
            index_type=IndexType.JSON
        )
        
        self.redis_client.ft(index_name).create_index(
            fields=schema,
            definition=definition
        )
        print(f"✅ Created index: {index_name}")
    
    def create_semantic_cache_index(self):
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
            TextField("$.response", as_name="response"),
            TextField("$.model", as_name="model"),
            NumericField("$.timestamp", as_name="timestamp"),
            NumericField("$.tokens", as_name="tokens"),
            VectorField(
                "$.query_embedding",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": self.config.embedding_dim,
                    "DISTANCE_METRIC": "COSINE",
                    "INITIAL_CAP": 5000,
                },
                as_name="query_embedding"
            ),
        )
        
        definition = IndexDefinition(
            prefix=["cache:"],
            index_type=IndexType.JSON
        )
        
        self.redis_client.ft(index_name).create_index(
            fields=schema,
            definition=definition
        )
        print(f"✅ Created index: {index_name}")
    
    def store_embedding(self, key: str, data: Dict[str, Any]):
        """Store document with embedding in Redis"""
        # Convert numpy array to list if needed
        if isinstance(data.get('embedding'), np.ndarray):
            data['embedding'] = data['embedding'].tolist()
        
        self.redis_client.json().set(key, '$', data)
    
    def search_similar(self, index_name: str, query_embedding: List[float], 
                      top_k: int = 5, filters: str = "") -> List[Dict]:
        """Search for similar documents using vector similarity"""
        query_vector = np.array(query_embedding, dtype=np.float32).tobytes()
        
        base_query = f"*=>[KNN {top_k} @embedding $vec AS score]"
        if filters:
            base_query = f"({filters})=>[KNN {top_k} @embedding $vec AS score]"
        
        query = (
            Query(base_query)
            .sort_by("score")
            .return_fields("score", "ticker", "content")
            .dialect(2)
        )
        
        results = self.redis_client.ft(index_name).search(
            query, 
            query_params={"vec": query_vector}
        )
        
        return [
            {
                "score": float(doc.score),
                "ticker": doc.ticker if hasattr(doc, 'ticker') else None,
                "content": doc.content[:200] if hasattr(doc, 'content') else None
            }
            for doc in results.docs
        ]


class EmbeddingGenerator:
    """Generates embeddings using Azure OpenAI"""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.client = AzureOpenAI(
            api_key=config.azure_openai_key,
            api_version=config.azure_openai_api_version,
            azure_endpoint=config.azure_openai_endpoint
        )
        self.request_count = 0
        self.last_request_time = time.time()
    
    def _rate_limit(self):
        """Simple rate limiting to avoid quota issues"""
        self.request_count += 1
        if self.request_count % 10 == 0:
            time.sleep(1)  # Pause every 10 requests
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        self._rate_limit()
        
        response = self.client.embeddings.create(
            input=text,
            model=self.config.embedding_deployment
        )
        
        return response.data[0].embedding
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        self._rate_limit()
        
        response = self.client.embeddings.create(
            input=texts,
            model=self.config.embedding_deployment
        )
        
        return [item.embedding for item in response.data]
    
    def chunk_text(self, text: str, max_tokens: int = 8000) -> List[str]:
        """Split text into chunks (simple word-based splitting)"""
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
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


class DataProcessor:
    """Processes SEC filings and news articles"""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.embedding_gen = EmbeddingGenerator(config)
        self.vector_store = RedisVectorStore(config)
    
    def extract_text_from_html(self, html_content: str) -> str:
        """Extract text content from HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def process_sec_filing(self, ticker: str, filing_type: str, 
                          filing_path: Path) -> int:
        """Process a single SEC filing and generate embeddings"""
        with open(filing_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        text = self.extract_text_from_html(html_content)
        
        # Get metadata
        metadata_path = filing_path.parent / f"{filing_type.lower()}_metadata.json"
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        
        filing_date = metadata.get('filing_date', 'unknown')
        
        # Chunk the text
        chunks = self.embedding_gen.chunk_text(text)
        
        # Generate embeddings for each chunk
        for idx, chunk in enumerate(chunks):
            if len(chunk.strip()) < 100:  # Skip very short chunks
                continue
            
            embedding = self.embedding_gen.generate_embedding(chunk)
            
            doc_id = f"sec:{ticker}:{filing_type}:{filing_date}:{idx}"
            doc_data = {
                "ticker": ticker,
                "ticker_tag": ticker,
                "filing_type": filing_type,
                "filing_date": filing_date,
                "content": chunk[:5000],  # Store first 5000 chars
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "embedding": embedding,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            self.vector_store.store_embedding(doc_id, doc_data)
        
        return len(chunks)
    
    def process_news_article(self, ticker: str, article: Dict) -> bool:
        """Process a single news article and generate embedding"""
        title = article.get('title', '')
        content = article.get('summary', '')
        url = article.get('link', '')
        published = article.get('published', '')
        
        # Combine title and content
        full_text = f"{title}\n\n{content}"
        
        if len(full_text.strip()) < 50:
            return False
        
        embedding = self.embedding_gen.generate_embedding(full_text)
        
        # Create unique ID
        article_id = hashlib.md5(url.encode()).hexdigest()
        doc_id = f"news:{ticker}:{article_id}"
        
        doc_data = {
            "ticker": ticker,
            "ticker_tag": ticker,
            "title": title,
            "content": content,
            "url": url,
            "published": published,
            "embedding": embedding,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        self.vector_store.store_embedding(doc_id, doc_data)
        return True
    
    def process_all_sec_filings(self, data_dir: Path):
        """Process all SEC filings"""
        print("\n📄 Processing SEC Filings...")
        
        filing_types = ['10-K', '10-Q']
        total_chunks = 0
        
        for ticker_dir in sorted(data_dir.iterdir()):
            if not ticker_dir.is_dir() or ticker_dir.name == '.git':
                continue
            
            ticker = ticker_dir.name
            print(f"\n  Processing {ticker}...")
            
            for filing_type in filing_types:
                filing_file = ticker_dir / f"{filing_type.lower()}.htm"
                if filing_file.exists():
                    try:
                        chunks = self.process_sec_filing(ticker, filing_type, filing_file)
                        total_chunks += chunks
                        print(f"    ✅ {filing_type}: {chunks} chunks")
                    except Exception as e:
                        print(f"    ❌ {filing_type}: {str(e)}")
        
        print(f"\n✅ Processed SEC filings: {total_chunks} total chunks")
        return total_chunks
    
    def process_all_news_articles(self, data_dir: Path):
        """Process all news articles"""
        print("\n📰 Processing News Articles...")
        
        total_articles = 0
        
        for ticker_dir in sorted(data_dir.iterdir()):
            if not ticker_dir.is_dir() or ticker_dir.name == '.git':
                continue
            
            ticker = ticker_dir.name
            news_file = ticker_dir / "news_articles.json"
            
            if not news_file.exists():
                continue
            
            with open(news_file, 'r') as f:
                articles = json.load(f)
            
            processed = 0
            for article in articles:
                if self.process_news_article(ticker, article):
                    processed += 1
            
            total_articles += processed
            print(f"  ✅ {ticker}: {processed} articles")
        
        print(f"\n✅ Processed news articles: {total_articles} total")
        return total_articles


def main():
    """Main execution function"""
    print("=" * 60)
    print("FinagentiX - Embedding Generation & Vector Indexing")
    print("=" * 60)
    
    # Load configuration
    config = EmbeddingConfig(
        azure_openai_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT', 
                                        'https://openai-545d8fdb508d4.openai.azure.com/'),
        azure_openai_key=os.getenv('AZURE_OPENAI_API_KEY', 
                                   'a72469a7210c4c6286beddca96f37d62'),
        azure_openai_api_version='2024-08-01-preview',
        embedding_deployment='text-embedding-3-large',
        redis_host=os.getenv('REDIS_HOST', 
                            'redis-545d8fdb508d4.eastus.redis.azure.net'),
        redis_port=int(os.getenv('REDIS_PORT', '10000')),
        redis_password=os.getenv('REDIS_PASSWORD')
    )
    
    # Initialize processor
    processor = DataProcessor(config)
    
    # Create indexes
    print("\n📊 Creating Redis Vector Indexes...")
    processor.vector_store.create_sec_filing_index()
    processor.vector_store.create_news_index()
    processor.vector_store.create_semantic_cache_index()
    
    # Process data
    sec_dir = Path('data/raw/sec_filings')
    news_dir = Path('data/raw/news_articles')
    
    if sec_dir.exists():
        processor.process_all_sec_filings(sec_dir)
    else:
        print(f"⚠️  SEC filings directory not found: {sec_dir}")
    
    if news_dir.exists():
        processor.process_all_news_articles(news_dir)
    else:
        print(f"⚠️  News articles directory not found: {news_dir}")
    
    print("\n" + "=" * 60)
    print("✅ Embedding generation and indexing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
