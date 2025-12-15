#!/usr/bin/env python3
"""
Test embedding generation with a single ticker
"""

import os
import sys

import pytest
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, '/Users/thomas.findelkind/Code/FinagentiX')

from scripts.generate_embeddings import *  # noqa: F401,F403

load_dotenv()

_required = {
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    "REDIS_HOST",
    "REDIS_PORT",
}
_missing = [env for env in _required if not os.getenv(env)]
if _missing:
    pytest.skip(
        f"Skipping embedding integration test; missing environment variables: {', '.join(sorted(_missing))}",
        allow_module_level=True,
    )


def require_env(name: str) -> str:
    """Fetch required environment variable"""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

def test_single_ticker():
    """Test with just AAPL"""
    print("=" * 60)
    print("Testing Embedding Generation - Single Ticker (AAPL)")
    print("=" * 60)
    
    config = EmbeddingConfig(
        azure_openai_endpoint=require_env('AZURE_OPENAI_ENDPOINT'),
        azure_openai_key=require_env('AZURE_OPENAI_API_KEY'),
        azure_openai_api_version=require_env('AZURE_OPENAI_API_VERSION'),
        embedding_deployment=require_env('AZURE_OPENAI_EMBEDDING_DEPLOYMENT'),
        redis_host=require_env('REDIS_HOST'),
        redis_port=int(require_env('REDIS_PORT')),
        redis_password=os.getenv('REDIS_PASSWORD')
    )
    
    processor = DataProcessor(config)
    
    # Create indexes
    print("\n📊 Creating indexes...")
    processor.vector_store.create_sec_filing_index()
    processor.vector_store.create_news_index()
    processor.vector_store.create_semantic_cache_index()
    
    # Test SEC filing
    print("\n📄 Testing SEC filing processing (AAPL)...")
    sec_path = Path('data/raw/sec_filings/AAPL')
    if sec_path.exists():
        filing_10k = sec_path / '10-k.htm'
        if filing_10k.exists():
            chunks = processor.process_sec_filing('AAPL', '10-K', filing_10k)
            print(f"✅ Processed 10-K: {chunks} chunks")
    
    # Test news articles
    print("\n📰 Testing news article processing (AAPL)...")
    news_path = Path('data/raw/news_articles/AAPL/news_articles.json')
    if news_path.exists():
        with open(news_path, 'r') as f:
            articles = json.load(f)
        
        count = 0
        for article in articles[:3]:  # Just first 3 articles
            if processor.process_news_article('AAPL', article):
                count += 1
        print(f"✅ Processed {count} news articles")
    
    # Test vector search
    print("\n🔍 Testing vector search...")
    test_query = "What is Apple's revenue growth?"
    query_embedding = processor.embedding_gen.generate_embedding(test_query)
    
    results = processor.vector_store.search_similar(
        "idx:sec_filings",
        query_embedding,
        top_k=3,
        filters="@ticker_tag:{AAPL}"
    )
    
    print(f"✅ Found {len(results)} similar documents:")
    for i, res in enumerate(results, 1):
        print(f"  {i}. Score: {res['score']:.4f}")
        print(f"     Content: {res['content'][:100]}...")
    
    print("\n" + "=" * 60)
    print("✅ Test completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    test_single_ticker()
