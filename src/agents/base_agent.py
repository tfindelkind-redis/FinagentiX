"""
Base Agent Class
Common functionality for all FinagentiX agents
"""

from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
import redis
from openai import AzureOpenAI

from .config import get_config


class BaseAgent(ABC):
    """
    Base class for all FinagentiX agents
    
    Provides common functionality:
    - Redis connection management
    - Azure OpenAI client
    - Semantic caching
    - Tool output caching
    - Logging
    """
    
    def __init__(
        self,
        name: str,
        instructions: str,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize base agent
        
        Args:
            name: Agent name
            instructions: System instructions for the agent
            tools: List of tool definitions (optional)
        """
        self.name = name
        self.instructions = instructions
        self.tools = tools or []
        
        # Load configuration
        self.config = get_config()
        
        # Initialize Redis connection
        self._redis_client: Optional[redis.Redis] = None
        
        # Initialize OpenAI client
        self._openai_client: Optional[AzureOpenAI] = None
    
    @property
    def redis(self) -> redis.Redis:
        """Get or create Redis connection"""
        if self._redis_client is None:
            self._redis_client = redis.Redis(
                host=self.config.redis.host,
                port=self.config.redis.port,
                password=self.config.redis.password,
                ssl=self.config.redis.ssl,
                decode_responses=self.config.redis.decode_responses
            )
        return self._redis_client
    
    @property
    def openai(self) -> AzureOpenAI:
        """Get or create Azure OpenAI client"""
        if self._openai_client is None:
            self._openai_client = AzureOpenAI(
                api_key=self.config.azure_openai.api_key,
                api_version=self.config.azure_openai.api_version,
                azure_endpoint=self.config.azure_openai.endpoint
            )
        return self._openai_client
    
    @abstractmethod
    async def run(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the agent's task
        
        Args:
            task: Task description/query
            context: Additional context (optional)
        
        Returns:
            Agent response with results
        """
        pass
    
    def check_semantic_cache(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Check if similar query exists in semantic cache
        
        Args:
            query: User query
        
        Returns:
            Cached response if found, None otherwise
        """
        if not self.config.enable_semantic_cache:
            return None
        
        # TODO: Implement vector similarity search
        # This will be implemented in Phase 5.3
        return None
    
    def cache_response(
        self,
        query: str,
        response: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """
        Cache agent response for future use
        
        Args:
            query: Original query
            response: Agent response
            ttl: Time to live in seconds (optional)
        """
        if not self.config.enable_semantic_cache:
            return
        
        # TODO: Implement semantic caching
        # This will be implemented in Phase 5.3
        pass
    
    def check_tool_cache(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Check if tool output is cached
        
        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
        
        Returns:
            Cached tool output if found, None otherwise
        """
        if not self.config.enable_tool_cache:
            return None
        
        # Create cache key from tool name and parameters
        import json
        import hashlib
        
        params_str = json.dumps(parameters, sort_keys=True)
        cache_key = f"tool:{tool_name}:{hashlib.md5(params_str.encode()).hexdigest()}"
        
        # Check Redis cache
        cached = self.redis.get(cache_key)
        if cached:
            import pickle
            return pickle.loads(cached)
        
        return None
    
    def cache_tool_output(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        output: Any,
        ttl: Optional[int] = None
    ):
        """
        Cache tool output for future use
        
        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
            output: Tool output to cache
            ttl: Time to live in seconds (optional)
        """
        if not self.config.enable_tool_cache:
            return
        
        import json
        import hashlib
        import pickle
        
        # Create cache key
        params_str = json.dumps(parameters, sort_keys=True)
        cache_key = f"tool:{tool_name}:{hashlib.md5(params_str.encode()).hexdigest()}"
        
        # Cache in Redis
        ttl = ttl or self.config.tool_cache_ttl
        self.redis.setex(
            cache_key,
            ttl,
            pickle.dumps(output)
        )
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"


if __name__ == "__main__":
    """Test base agent functionality"""
    print("BaseAgent class loaded successfully")
    print("This is an abstract class - use specific agent implementations")
