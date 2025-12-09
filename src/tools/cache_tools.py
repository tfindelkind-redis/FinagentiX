"""
Cache Tools - Semantic caching and query response management

Tools for:
- Checking semantic cache for similar queries
- Storing query responses in semantic cache
- Invalidating stale cache entries
"""

from typing import Optional, Dict, Any, List
import redis
from datetime import datetime
import json
from src.agents.config import get_config
from src.tools.vector_tools import _generate_embedding, _embedding_to_bytes


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


def check_semantic_cache(
    query: str,
    similarity_threshold: float = 0.92
) -> Optional[Dict[str, Any]]:
    """
    Check if a similar query exists in semantic cache.
    
    This implements full response caching - if a very similar question
    was asked before (>92% similarity), return the cached response.
    
    Args:
        query: User's query text
        similarity_threshold: Minimum similarity for cache hit (0.92 = 92%)
        
    Returns:
        Cached response dict if found, None otherwise:
            - answer: Final answer text
            - agents_used: List of agents that generated the response
            - timestamp: When response was cached
            - cache_hits: Number of times this was a cache hit
            
    Example:
        cached = check_semantic_cache("Should I buy AAPL?")
        if cached:
            return cached["answer"]  # Cache hit! 30-70% cost savings
    """
    redis_client = _get_redis_client()
    config = get_config()
    
    # Generate query embedding
    try:
        query_embedding = _generate_embedding(query)
    except Exception as e:
        print(f"Error generating embedding for cache check: {e}")
        return None
    
    # Vector search in semantic cache
    from redis.commands.search.query import Query
    
    query_obj = (
        Query(f"*=>[KNN 1 @embedding $vector AS score]")
        .return_fields("query", "response", "timestamp", "agents_used", "score")
        .dialect(2)
    )
    
    try:
        results = redis_client.ft("idx:semantic_cache").search(
            query_obj,
            query_params={"vector": _embedding_to_bytes(query_embedding)}
        )
        
        if results.docs:
            doc = results.docs[0]
            score = float(doc.score)
            
            if score >= similarity_threshold:
                # Cache hit!
                response_data = json.loads(doc.response)
                
                # Increment cache hit counter
                cache_key = doc.id
                redis_client.hincrby(cache_key, "cache_hits", 1)
                
                return {
                    "answer": response_data.get("answer"),
                    "agents_used": json.loads(doc.agents_used) if hasattr(doc, 'agents_used') else [],
                    "timestamp": doc.timestamp,
                    "cached": True,
                    "similarity_score": score
                }
        
        return None
    
    except Exception as e:
        # Index might not exist yet
        print(f"Error checking semantic cache: {e}")
        return None


def cache_query_response(
    query: str,
    response: Dict[str, Any],
    ttl: Optional[int] = None
) -> bool:
    """
    Store query and response in semantic cache.
    
    Args:
        query: User's query text
        response: Response dict with keys:
            - answer: Final answer text
            - agents_used: List of agent names
            - (other optional metadata)
        ttl: Time-to-live in seconds (default: from config)
        
    Returns:
        True if cached successfully, False otherwise
        
    Example:
        success = cache_query_response(
            query="What is AAPL's P/E ratio?",
            response={
                "answer": "Apple's P/E ratio is 28.5",
                "agents_used": ["market_data", "fundamental_analysis"]
            }
        )
    """
    redis_client = _get_redis_client()
    config = get_config()
    
    if ttl is None:
        ttl = config.semantic_cache_ttl  # Default: 1 hour
    
    try:
        # Generate query embedding
        query_embedding = _generate_embedding(query)
        
        # Create cache key
        import hashlib
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_key = f"cache:semantic:{query_hash}"
        
        # Store in Redis Hash
        cache_data = {
            "query": query,
            "response": json.dumps(response),
            "timestamp": datetime.now().isoformat(),
            "agents_used": json.dumps(response.get("agents_used", [])),
            "cache_hits": 0,
            "embedding": _embedding_to_bytes(query_embedding).hex()
        }
        
        # Store with TTL
        pipe = redis_client.pipeline()
        pipe.hset(cache_key, mapping=cache_data)
        pipe.expire(cache_key, ttl)
        pipe.execute()
        
        return True
    
    except Exception as e:
        print(f"Error caching query response: {e}")
        return False


def invalidate_cache(
    pattern: Optional[str] = None,
    ticker: Optional[str] = None,
    cache_type: str = "semantic"
) -> int:
    """
    Invalidate cache entries matching criteria.
    
    Use this when data becomes stale (e.g., new earnings report,
    market close, breaking news).
    
    Args:
        pattern: Redis key pattern to match (e.g., "cache:semantic:*")
        ticker: Invalidate all caches related to this ticker
        cache_type: Type of cache ("semantic", "tool", "routing")
        
    Returns:
        Number of cache entries deleted
        
    Example:
        # Invalidate all AAPL-related semantic caches
        deleted = invalidate_cache(ticker="AAPL", cache_type="semantic")
        
        # Invalidate all semantic caches
        deleted = invalidate_cache(cache_type="semantic")
    """
    redis_client = _get_redis_client()
    
    # Build search pattern
    if pattern:
        search_pattern = pattern
    elif ticker:
        search_pattern = f"cache:{cache_type}:*{ticker}*"
    else:
        search_pattern = f"cache:{cache_type}:*"
    
    try:
        # Find matching keys
        keys = []
        cursor = 0
        while True:
            cursor, batch = redis_client.scan(cursor, match=search_pattern, count=100)
            keys.extend(batch)
            if cursor == 0:
                break
        
        # Delete keys
        if keys:
            deleted = redis_client.delete(*keys)
            return deleted
        
        return 0
    
    except Exception as e:
        print(f"Error invalidating cache: {e}")
        return 0


def get_cache_stats() -> Dict[str, Any]:
    """
    Get semantic cache statistics.
    
    Returns:
        Dict with cache statistics:
            - total_entries: Number of cached queries
            - total_hits: Sum of all cache hits
            - hit_rate: Cache hit rate percentage
            - avg_similarity: Average similarity score of hits
            
    Example:
        stats = get_cache_stats()
        print(f"Cache hit rate: {stats['hit_rate']:.1%}")
    """
    redis_client = _get_redis_client()
    
    try:
        # Count cache entries
        cursor = 0
        total_entries = 0
        total_hits = 0
        
        while True:
            cursor, keys = redis_client.scan(cursor, match="cache:semantic:*", count=100)
            
            for key in keys:
                total_entries += 1
                cache_hits = redis_client.hget(key, "cache_hits")
                if cache_hits:
                    total_hits += int(cache_hits)
            
            if cursor == 0:
                break
        
        # Calculate hit rate
        hit_rate = total_hits / total_entries if total_entries > 0 else 0.0
        
        return {
            "total_entries": total_entries,
            "total_hits": total_hits,
            "hit_rate": hit_rate,
            "estimated_savings_pct": hit_rate * 0.70  # Assume 70% cost per hit
        }
    
    except Exception as e:
        print(f"Error getting cache stats: {e}")
        return {
            "total_entries": 0,
            "total_hits": 0,
            "hit_rate": 0.0,
            "estimated_savings_pct": 0.0
        }


def warm_cache(queries: List[str]) -> int:
    """
    Pre-warm cache with common queries.
    
    Run this during off-peak hours to pre-compute responses
    for frequently asked questions.
    
    Args:
        queries: List of common queries to pre-compute
        
    Returns:
        Number of queries successfully cached
        
    Example:
        queries = [
            "What is AAPL stock price?",
            "Recent news about Tesla",
            "MSFT earnings report"
        ]
        cached = warm_cache(queries)
    """
    # This will be implemented in Phase 5.4 when we have
    # full orchestration workflow
    return 0
