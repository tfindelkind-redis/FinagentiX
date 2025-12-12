"""
Redis client configuration and connection management
"""

import os
import redis
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class RedisConfig:
    """Redis configuration from environment variables"""
    
    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self.password = os.getenv("REDIS_PASSWORD")
        self.ssl = os.getenv("REDIS_SSL", "false").lower() == "true"
        self.decode_responses = True
        self.max_connections = 50


# Global Redis client instance
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client instance
    
    Returns:
        redis.Redis: Redis client instance
    """
    global _redis_client
    
    if _redis_client is None:
        config = RedisConfig()
        
        _redis_client = redis.Redis(
            host=config.host,
            port=config.port,
            password=config.password,
            ssl=config.ssl,
            decode_responses=config.decode_responses,
            max_connections=config.max_connections,
        )
        
        # Test connection
        try:
            _redis_client.ping()
            print(f"✅ Connected to Redis at {config.host}:{config.port}")
        except redis.ConnectionError as e:
            print(f"❌ Failed to connect to Redis: {e}")
            raise
    
    return _redis_client


def close_redis_client():
    """Close Redis client connection"""
    global _redis_client
    if _redis_client:
        _redis_client.close()
        _redis_client = None


if __name__ == "__main__":
    # Test Redis connection
    client = get_redis_client()
    print(f"Redis connection test: {client.ping()}")
    print(f"Redis info: {client.info('server')['redis_version']}")
