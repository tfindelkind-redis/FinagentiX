"""
Agent Configuration
Centralized configuration for Microsoft Agent Framework agents
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class AzureOpenAIConfig:
    """Azure OpenAI configuration"""
    endpoint: str
    api_key: str
    api_version: str = "2024-08-01-preview"
    embedding_deployment: str = "text-embedding-3-large"
    chat_deployment: str = "gpt-4o"
    
    @classmethod
    def from_env(cls) -> "AzureOpenAIConfig":
        """Load configuration from environment variables"""
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_KEY")
        
        if not endpoint or not api_key:
            raise ValueError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY must be set")
        
        return cls(
            endpoint=endpoint,
            api_key=api_key,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
            embedding_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large"),
            chat_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
        )


@dataclass
class RedisConfig:
    """Redis Enterprise configuration"""
    host: str
    port: int
    password: str
    ssl: bool = True
    decode_responses: bool = False
    
    @classmethod
    def from_env(cls) -> "RedisConfig":
        """Load configuration from environment variables"""
        host = os.getenv("REDIS_HOST")
        password = os.getenv("REDIS_PASSWORD")
        
        if not host or not password:
            raise ValueError("REDIS_HOST and REDIS_PASSWORD must be set")
        
        return cls(
            host=host,
            port=int(os.getenv("REDIS_PORT", "10000")),
            password=password
        )


@dataclass
class AgentConfig:
    """Complete agent configuration"""
    azure_openai: AzureOpenAIConfig
    redis: RedisConfig
    
    # Agent behavior settings
    max_iterations: int = 10
    timeout_seconds: int = 300
    enable_semantic_cache: bool = True
    enable_tool_cache: bool = True
    enable_routing_cache: bool = True
    
    # Cache TTLs (seconds)
    semantic_cache_ttl: int = 3600  # 1 hour
    tool_cache_ttl: int = 300  # 5 minutes
    routing_cache_ttl: int = 86400  # 24 hours
    
    # Vector search settings
    vector_top_k: int = 5
    similarity_threshold: float = 0.85
    
    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load complete configuration from environment"""
        return cls(
            azure_openai=AzureOpenAIConfig.from_env(),
            redis=RedisConfig.from_env()
        )


# Global configuration instance
_config: Optional[AgentConfig] = None

def get_config() -> AgentConfig:
    """Get or create the global configuration instance"""
    global _config
    if _config is None:
        _config = AgentConfig.from_env()
    return _config


if __name__ == "__main__":
    """Test configuration loading"""
    print("Testing Agent Configuration...\n")
    
    try:
        config = get_config()
        
        print("✅ Configuration loaded successfully!")
        print(f"\nAzure OpenAI:")
        print(f"  Endpoint: {config.azure_openai.endpoint}")
        print(f"  Chat Model: {config.azure_openai.chat_deployment}")
        print(f"  Embedding Model: {config.azure_openai.embedding_deployment}")
        
        print(f"\nRedis:")
        print(f"  Host: {config.redis.host}")
        print(f"  Port: {config.redis.port}")
        print(f"  SSL: {config.redis.ssl}")
        
        print(f"\nAgent Settings:")
        print(f"  Max Iterations: {config.max_iterations}")
        print(f"  Semantic Cache: {config.enable_semantic_cache}")
        print(f"  Tool Cache: {config.enable_tool_cache}")
        print(f"  Routing Cache: {config.enable_routing_cache}")
        
        print("\n✅ All configuration valid!")
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        exit(1)
