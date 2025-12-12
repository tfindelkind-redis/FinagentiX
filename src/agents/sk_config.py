"""
Semantic Kernel Configuration for FinagentiX
Handles initialization of Semantic Kernel with Azure OpenAI and Redis
"""

import os
from typing import Optional
import redis
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.agents.runtime import InProcessRuntime
from ..utils.logger import SKDebugger


class SemanticKernelConfig:
    """
    Configuration and factory for Semantic Kernel components
    """
    
    def __init__(
        self,
        azure_openai_endpoint: Optional[str] = None,
        azure_openai_key: Optional[str] = None,
        azure_openai_deployment: Optional[str] = None,
        azure_openai_api_version: str = "2024-08-01-preview",
        redis_host: Optional[str] = None,
        redis_port: int = 10000,
        redis_password: Optional[str] = None,
        redis_ssl: bool = True
    ):
        """
        Initialize Semantic Kernel configuration
        
        Args:
            azure_openai_endpoint: Azure OpenAI endpoint URL
            azure_openai_key: Azure OpenAI API key
            azure_openai_deployment: Deployment name (default: gpt-4)
            azure_openai_api_version: API version
            redis_host: Redis hostname
            redis_port: Redis port (default: 10000 for Enterprise)
            redis_password: Redis password
            redis_ssl: Use SSL/TLS for Redis connection
        """
        # Azure OpenAI configuration
        self.azure_openai_endpoint = azure_openai_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_openai_key = azure_openai_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_openai_deployment = azure_openai_deployment or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4")
        self.azure_openai_api_version = azure_openai_api_version
        
        # Redis configuration
        self.redis_host = redis_host or os.getenv("REDIS_HOST")
        self.redis_port = int(os.getenv("REDIS_PORT", redis_port))
        self.redis_password = redis_password or os.getenv("REDIS_PASSWORD")
        self.redis_ssl = os.getenv("REDIS_SSL", str(redis_ssl)).lower() == "true"
        
        # Validate configuration
        self._validate_config()
        
        # Initialize debugger and components
        self.debugger = SKDebugger("config")
        self.debugger.log_config({
            "deployment": self.azure_openai_deployment,
            "endpoint": self.azure_openai_endpoint,
            "redis_host": self.redis_host,
            "redis_port": self.redis_port,
            "redis_ssl": self.redis_ssl
        })
        
        self._kernel: Optional[Kernel] = None
        self._redis_client: Optional[redis.Redis] = None
        self._runtime: Optional[InProcessRuntime] = None
    
    def _validate_config(self):
        """Validate that required configuration is provided"""
        if not self.azure_openai_endpoint:
            raise ValueError("Azure OpenAI endpoint not configured. Set AZURE_OPENAI_ENDPOINT environment variable.")
        
        if not self.azure_openai_key:
            raise ValueError("Azure OpenAI key not configured. Set AZURE_OPENAI_API_KEY environment variable.")
        
        if not self.redis_host:
            raise ValueError("Redis host not configured. Set REDIS_HOST environment variable.")
        
        # Only require password for remote Redis (not localhost)
        # Check for both None and empty string
        has_password = self.redis_password and self.redis_password.strip()
        if self.redis_host not in ["localhost", "127.0.0.1"] and not has_password:
            raise ValueError("Redis password not configured. Set REDIS_PASSWORD environment variable.")
    
    def create_kernel(self) -> Kernel:
        """
        Create and configure a Semantic Kernel instance
        
        Returns:
            Configured Kernel with Azure OpenAI service
        """
        if self._kernel is None:
            # Log kernel creation
            self.debugger.log_kernel_creation(
                self.azure_openai_deployment,
                self.azure_openai_endpoint
            )
            
            kernel = Kernel()
            
            # Add Azure OpenAI chat completion service
            kernel.add_service(
                AzureChatCompletion(
                    deployment_name=self.azure_openai_deployment,
                    endpoint=self.azure_openai_endpoint,
                    api_key=self.azure_openai_key,
                    api_version=self.azure_openai_api_version,
                    service_id="azure_openai"
                )
            )
            
            self._kernel = kernel
        
        return self._kernel
    
    def get_kernel(self) -> Kernel:
        """
        Get or create the Kernel instance
        
        Returns:
            Configured Kernel
        """
        if self._kernel is None:
            return self.create_kernel()
        return self._kernel
    
    def create_redis_client(self) -> redis.Redis:
        """
        Create and configure a Redis client
        
        Returns:
            Configured Redis client
        """
        if self._redis_client is None:
            self._redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                ssl=self.redis_ssl,
                decode_responses=True,
                ssl_cert_reqs=None  # Don't verify SSL certificate for Azure Redis Enterprise
            )
            
            # Test connection
            try:
                self._redis_client.ping()
            except redis.ConnectionError as e:
                raise ConnectionError(f"Failed to connect to Redis: {e}")
        
        return self._redis_client
    
    def get_redis_client(self) -> redis.Redis:
        """
        Get or create the Redis client
        
        Returns:
            Configured Redis client
        """
        if self._redis_client is None:
            return self.create_redis_client()
        return self._redis_client
    
    def create_runtime(self) -> InProcessRuntime:
        """
        Create and start an InProcessRuntime for agent orchestration
        
        Returns:
            Started runtime instance
        """
        if self._runtime is None:
            self._runtime = InProcessRuntime()
            self._runtime.start()
        
        return self._runtime
    
    def get_runtime(self) -> InProcessRuntime:
        """
        Get or create the runtime
        
        Returns:
            Started runtime instance
        """
        if self._runtime is None:
            return self.create_runtime()
        return self._runtime
    
    async def stop_runtime(self):
        """Stop the runtime if it's running"""
        if self._runtime is not None:
            await self._runtime.stop_when_idle()
            self._runtime = None
    
    def close_redis(self):
        """Close the Redis connection"""
        if self._redis_client is not None:
            self._redis_client.close()
            self._redis_client = None


# Global configuration instance
_global_config: Optional[SemanticKernelConfig] = None


def get_global_config() -> SemanticKernelConfig:
    """
    Get or create the global Semantic Kernel configuration
    
    Returns:
        Global configuration instance
    """
    global _global_config
    if _global_config is None:
        _global_config = SemanticKernelConfig()
    return _global_config


def initialize_semantic_kernel() -> Kernel:
    """
    Initialize and return a configured Semantic Kernel
    
    Returns:
        Configured Kernel instance
    """
    config = get_global_config()
    return config.create_kernel()


def get_redis_client() -> redis.Redis:
    """
    Get a configured Redis client
    
    Returns:
        Redis client instance
    """
    config = get_global_config()
    return config.get_redis_client()


def get_runtime() -> InProcessRuntime:
    """
    Get a started runtime for agent orchestration
    
    Returns:
        Runtime instance
    """
    config = get_global_config()
    return config.get_runtime()


# Example usage
if __name__ == "__main__":
    # Test configuration
    print("Testing Semantic Kernel configuration...")
    
    try:
        # Initialize kernel
        kernel = initialize_semantic_kernel()
        print(f"✅ Kernel initialized with Azure OpenAI")
        
        # Test Redis connection
        redis_client = get_redis_client()
        print(f"✅ Redis connected to {redis_client.connection_pool.connection_kwargs['host']}")
        
        # Create runtime
        runtime = get_runtime()
        print(f"✅ Runtime started")
        
        print("\n🎉 All components initialized successfully!")
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
