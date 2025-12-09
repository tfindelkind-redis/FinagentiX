"""
Vector Search Tools - Redis HNSW vector search operations

Tools for semantic search across:
- SEC filings (10-K, 10-Q documents)
- News articles
- Previous queries (semantic cache)
"""

from typing import List, Dict, Optional, Any
import redis
from openai import AzureOpenAI
from src.agents.config import get_config
import json


def _get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    config = get_config()
    return redis.Redis(
        host=config.redis.host,
        port=config.redis.port,
        password=config.redis.password,
        ssl=config.redis.ssl,
        decode_responses=True
    )


def _get_openai_client() -> AzureOpenAI:
    """Get Azure OpenAI client instance."""
    config = get_config()
    return AzureOpenAI(
        api_key=config.azure_openai.api_key,
        api_version=config.azure_openai.api_version,
        azure_endpoint=config.azure_openai.endpoint
    )


def _generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for text using Azure OpenAI.
    
    Args:
        text: Text to embed
        
    Returns:
        List of floats representing the embedding vector
    """
    config = get_config()
    client = _get_openai_client()
    
    response = client.embeddings.create(
        input=text,
        model=config.azure_openai.embedding_deployment
    )
    
    return response.data[0].embedding


def search_sec_filings(
    query: str,
    ticker: Optional[str] = None,
    filing_type: Optional[str] = None,
    top_k: int = 5,
    similarity_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Search SEC filings using vector similarity.
    
    Args:
        query: Natural language query (e.g., "revenue recognition policy")
        ticker: Optional ticker symbol to filter by (e.g., "AAPL")
        filing_type: Optional filing type filter (e.g., "10-K", "10-Q")
        top_k: Number of results to return
        similarity_threshold: Minimum similarity score (0-1)
        
    Returns:
        List of dicts with keys:
            - ticker: Stock ticker
            - filing_type: Form type (10-K, 10-Q)
            - filing_date: Date of filing
            - section: Section name
            - content: Text content
            - url: SEC EDGAR URL
            - score: Similarity score (0-1)
            
    Example:
        results = search_sec_filings(
            query="What was AAPL's revenue in 2023?",
            ticker="AAPL",
            filing_type="10-K",
            top_k=3
        )
    """
    redis_client = _get_redis_client()
    
    # Generate query embedding
    query_embedding = _generate_embedding(query)
    
    # Build Redis search query
    from redis.commands.search.query import Query
    
    # Create filter conditions
    filter_parts = ["*"]
    if ticker:
        filter_parts.append(f"@ticker:{{{ticker}}}")
    if filing_type:
        filter_parts.append(f"@filing_type:{{{filing_type}}}")
    
    filter_str = " ".join(filter_parts)
    
    # Vector search query
    query_obj = (
        Query(f"{filter_str}=>[KNN {top_k} @embedding $vector AS score]")
        .return_fields("ticker", "filing_type", "filing_date", "section", "content", "url", "score")
        .sort_by("score")
        .dialect(2)
    )
    
    # Execute search
    results = redis_client.ft("idx:sec_filings").search(
        query_obj,
        query_params={"vector": _embedding_to_bytes(query_embedding)}
    )
    
    # Parse and filter results
    filtered_results = []
    for doc in results.docs:
        score = float(doc.score)
        if score >= similarity_threshold:
            filtered_results.append({
                "ticker": doc.ticker,
                "filing_type": doc.filing_type,
                "filing_date": doc.filing_date,
                "section": doc.section,
                "content": doc.content[:500] + "..." if len(doc.content) > 500 else doc.content,
                "url": doc.url,
                "score": score
            })
    
    return filtered_results


def search_news(
    query: str,
    ticker: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    top_k: int = 10,
    similarity_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Search news articles using vector similarity.
    
    Args:
        query: Natural language query (e.g., "recent product launches")
        ticker: Optional ticker symbol to filter by
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
        top_k: Number of results to return
        similarity_threshold: Minimum similarity score (0-1)
        
    Returns:
        List of dicts with keys:
            - title: Article title
            - ticker: Related ticker
            - published_date: Publication date
            - source: News source
            - content: Article text
            - url: Article URL
            - sentiment: Sentiment score (-1 to 1)
            - score: Similarity score (0-1)
            
    Example:
        results = search_news(
            query="Apple iPhone sales decline",
            ticker="AAPL",
            top_k=5
        )
    """
    redis_client = _get_redis_client()
    
    # Generate query embedding
    query_embedding = _generate_embedding(query)
    
    # Build filter conditions
    filter_parts = ["*"]
    if ticker:
        filter_parts.append(f"@ticker:{{{ticker}}}")
    if start_date:
        filter_parts.append(f"@published_date:[{start_date} +inf]")
    if end_date:
        filter_parts.append(f"@published_date:[-inf {end_date}]")
    
    filter_str = " ".join(filter_parts)
    
    # Vector search query
    from redis.commands.search.query import Query
    
    query_obj = (
        Query(f"{filter_str}=>[KNN {top_k} @embedding $vector AS score]")
        .return_fields("title", "ticker", "published_date", "source", "content", "url", "sentiment", "score")
        .sort_by("score")
        .dialect(2)
    )
    
    # Execute search
    results = redis_client.ft("idx:news_articles").search(
        query_obj,
        query_params={"vector": _embedding_to_bytes(query_embedding)}
    )
    
    # Parse and filter results
    filtered_results = []
    for doc in results.docs:
        score = float(doc.score)
        if score >= similarity_threshold:
            filtered_results.append({
                "title": doc.title,
                "ticker": doc.ticker,
                "published_date": doc.published_date,
                "source": doc.source,
                "content": doc.content[:300] + "..." if len(doc.content) > 300 else doc.content,
                "url": doc.url,
                "sentiment": float(doc.sentiment) if hasattr(doc, 'sentiment') else 0.0,
                "score": score
            })
    
    return filtered_results


def search_similar_queries(
    query: str,
    top_k: int = 3,
    similarity_threshold: float = 0.92
) -> List[Dict[str, Any]]:
    """
    Search for similar previous queries in semantic cache.
    
    This is used for full response caching - if a very similar question
    was asked before, return the cached response.
    
    Args:
        query: User's current query
        top_k: Number of similar queries to find
        similarity_threshold: High threshold (0.92+) for cache hit
        
    Returns:
        List of dicts with keys:
            - query: Previous query text
            - response: Cached response
            - timestamp: When response was cached
            - score: Similarity score (0-1)
            - agents_used: List of agents that generated response
            
    Example:
        cached = search_similar_queries(
            query="Should I buy AAPL stock?",
            top_k=1,
            similarity_threshold=0.92
        )
        if cached:
            return cached[0]["response"]  # Cache hit!
    """
    redis_client = _get_redis_client()
    
    # Generate query embedding
    query_embedding = _generate_embedding(query)
    
    # Vector search in semantic cache
    from redis.commands.search.query import Query
    
    query_obj = (
        Query(f"*=>[KNN {top_k} @embedding $vector AS score]")
        .return_fields("query", "response", "timestamp", "agents_used", "score")
        .sort_by("score")
        .dialect(2)
    )
    
    try:
        results = redis_client.ft("idx:semantic_cache").search(
            query_obj,
            query_params={"vector": _embedding_to_bytes(query_embedding)}
        )
        
        # Parse and filter results
        filtered_results = []
        for doc in results.docs:
            score = float(doc.score)
            if score >= similarity_threshold:
                filtered_results.append({
                    "query": doc.query,
                    "response": json.loads(doc.response),
                    "timestamp": doc.timestamp,
                    "score": score,
                    "agents_used": json.loads(doc.agents_used) if hasattr(doc, 'agents_used') else []
                })
        
        return filtered_results
    
    except Exception as e:
        # Cache index might not exist yet
        return []


def _embedding_to_bytes(embedding: List[float]) -> bytes:
    """
    Convert embedding vector to bytes for Redis.
    
    Args:
        embedding: List of floats
        
    Returns:
        Bytes representation for Redis vector search
    """
    import struct
    import numpy as np
    
    # Convert to numpy array and then to bytes
    arr = np.array(embedding, dtype=np.float32)
    return arr.tobytes()
