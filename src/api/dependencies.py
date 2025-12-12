"""
FastAPI dependencies for dependency injection
"""

from functools import lru_cache
from openai import AsyncAzureOpenAI

from ..redis import SemanticCache, ContextualMemory, SemanticRouter, ToolCache, get_redis_client, DocumentStore
from ..redis.rag_retriever import RAGRetriever
from .config import settings


@lru_cache()
def get_semantic_cache() -> SemanticCache:
    """Get semantic cache instance"""
    return SemanticCache()


@lru_cache()
def get_contextual_memory() -> ContextualMemory:
    """Get contextual memory instance"""
    return ContextualMemory()


@lru_cache()
def get_semantic_router() -> SemanticRouter:
    """Get semantic router instance"""
    return SemanticRouter()


@lru_cache()
def get_tool_cache() -> ToolCache:
    """Get tool cache instance"""
    return ToolCache()


@lru_cache()
def get_azure_openai_client() -> AsyncAzureOpenAI:
    """Get Azure OpenAI client"""
    return AsyncAzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )


@lru_cache()
def get_document_store() -> DocumentStore:
    """Get document store instance"""
    openai_client = get_azure_openai_client()
    return DocumentStore(openai_client=openai_client)


@lru_cache()
def get_rag_retriever() -> RAGRetriever:
    """Get RAG retriever instance"""
    document_store = get_document_store()
    openai_client = get_azure_openai_client()
    return RAGRetriever(
        document_store=document_store,
        openai_client=openai_client,
        deployment_name=settings.GPT4_DEPLOYMENT_NAME,
    )

