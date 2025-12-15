"""
Tool Cache for caching agent tool outputs
Reduces redundant API calls and calculations
"""

import json
import time
import hashlib
from typing import Any, Optional, Dict
from redis import Redis

from .client import get_redis_client


class ToolCache:
    """
    Tool output cache for agent plugins
    
    Features:
    - Cache expensive tool outputs (API calls, calculations)
    - Configurable TTL per tool type
    - 95%+ cache hit rate achievable
    - Sub-millisecond cache access
    """
    
    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        prefix: str = "tool:",
    ):
        """
        Initialize tool cache
        
        Args:
            redis_client: Redis client instance
            prefix: Key prefix for cache entries
        """
        self.redis = redis_client or get_redis_client()
        self.prefix = prefix
        
        # Default TTL values for different tool types
        self.ttl_config = {
            "stock_price": 60,  # 1 minute
            "moving_average": 300,  # 5 minutes
            "rsi": 300,  # 5 minutes
            "volatility": 600,  # 10 minutes
            "news": 1800,  # 30 minutes
            "sentiment": 1800,  # 30 minutes
            "sec_filing": 86400,  # 24 hours
            "portfolio": 60,  # 1 minute
            "default": 300,  # 5 minutes
        }
    
    def _generate_key(self, tool_name: str, **params) -> str:
        """
        Generate cache key from tool name and parameters
        
        Args:
            tool_name: Name of the tool
            **params: Tool parameters
        
        Returns:
            Cache key string
        """
        # Sort params for consistent keys
        sorted_params = json.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(sorted_params.encode()).hexdigest()[:8]
        
        return f"{self.prefix}{tool_name}:{param_hash}"
    
    def get(self, tool_name: str, **params) -> Optional[Any]:
        """
        Get cached tool output
        
        Args:
            tool_name: Name of the tool
            **params: Tool parameters
        
        Returns:
            Cached output if found, None otherwise
        """
        key = self._generate_key(tool_name, **params)
        
        try:
            cached_json = self.redis.get(key)
            if cached_json:
                data = json.loads(cached_json)
                
                # Increment hit count
                self.redis.hincrby(f"{key}:stats", "hits", 1)
                
                return data["output"]
            
            # Increment miss count
            self.redis.hincrby(f"{key}:stats", "misses", 1)
            return None
            
        except Exception as e:
            print(f"❌ Error getting cached tool output: {e}")
            return None
    
    def set(
        self,
        tool_name: str,
        output: Any,
        ttl_seconds: Optional[int] = None,
        **params
    ):
        """
        Cache tool output
        
        Args:
            tool_name: Name of the tool
            output: Tool output to cache
            ttl_seconds: Time to live (uses default if None)
            **params: Tool parameters
        """
        key = self._generate_key(tool_name, **params)
        
        # Get TTL from config or use default
        if ttl_seconds is None:
            ttl_seconds = self.ttl_config.get(tool_name, self.ttl_config["default"])
        
        try:
            cache_data = {
                "tool_name": tool_name,
                "params": params,
                "output": output,
                "timestamp": time.time(),
            }
            
            self.redis.setex(
                key,
                ttl_seconds,
                json.dumps(cache_data)
            )
            
        except Exception as e:
            print(f"❌ Error caching tool output: {e}")
    
    def invalidate(self, tool_name: str, **params):
        """
        Invalidate cached tool output
        
        Args:
            tool_name: Name of the tool
            **params: Tool parameters
        """
        key = self._generate_key(tool_name, **params)
        
        try:
            self.redis.delete(key)
            self.redis.delete(f"{key}:stats")
        except Exception as e:
            print(f"❌ Error invalidating cache: {e}")
    
    def invalidate_pattern(self, pattern: str):
        """
        Invalidate all cache entries matching pattern
        
        Args:
            pattern: Key pattern (e.g., "tool:stock_price:*")
        """
        try:
            keys = list(self.redis.scan_iter(f"{self.prefix}{pattern}", count=1000))
            if keys:
                self.redis.delete(*keys)
                print(f"✅ Invalidated {len(keys)} cache entries")
        except Exception as e:
            print(f"❌ Error invalidating cache pattern: {e}")
    
    def get_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Args:
            tool_name: Specific tool name (all tools if None)
        
        Returns:
            Statistics dict
        """
        pattern = f"{self.prefix}{tool_name}:*" if tool_name else f"{self.prefix}*"
        
        try:
            cache_keys = list(self.redis.scan_iter(pattern, count=1000))
            
            total_hits = 0
            total_misses = 0
            
            for key in cache_keys:
                if ":stats" in key:
                    continue
                    
                stats = self.redis.hgetall(f"{key}:stats")
                total_hits += int(stats.get("hits", 0))
                total_misses += int(stats.get("misses", 0))
            
            total_requests = total_hits + total_misses
            hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "total_entries": len([k for k in cache_keys if ":stats" not in k]),
                "total_hits": total_hits,
                "total_misses": total_misses,
                "hit_rate": f"{hit_rate:.2f}%",
                "tool_name": tool_name or "all",
            }
            
        except Exception as e:
            print(f"❌ Error getting cache stats: {e}")
            return {}
    
    def clear(self, tool_name: Optional[str] = None) -> int:
        """Clear cache entries and return the number of deleted items."""
        pattern = f"{self.prefix}{tool_name}:*" if tool_name else f"{self.prefix}*"
        
        try:
            keys = list(self.redis.scan_iter(pattern, count=1000))
            cleared = len(keys)
            if keys:
                self.redis.delete(*keys)
            print(f"✅ Cleared {cleared} tool cache entries")
            return cleared
        except Exception as e:
            print(f"❌ Error clearing cache: {e}")
            return 0


if __name__ == "__main__":
    # Test tool cache
    cache = ToolCache()
    
    # Test caching stock price
    cache.set(
        "stock_price",
        output={"ticker": "AAPL", "price": 195.30, "timestamp": time.time()},
        ticker="AAPL"
    )
    
    # Retrieve from cache
    result = cache.get("stock_price", ticker="AAPL")
    print(f"Cached result: {result}")
    
    # Try again (cache hit)
    result2 = cache.get("stock_price", ticker="AAPL")
    print(f"Second retrieval: {result2}")
    
    # Different ticker (cache miss)
    result3 = cache.get("stock_price", ticker="MSFT")
    print(f"Different ticker: {result3}")
    
    # Stats
    print(f"Stats: {cache.get_stats('stock_price')}")
