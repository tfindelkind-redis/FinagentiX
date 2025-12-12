#!/usr/bin/env python3
"""Quick test to see what's failing"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_azure_openai():
    """Test Azure OpenAI connection"""
    from openai import AsyncAzureOpenAI
    import httpx
    
    print("Testing Azure OpenAI connection...")
    print(f"Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    print(f"API Version: {os.getenv('AZURE_OPENAI_API_VERSION')}")
    print(f"GPT4 Deployment: {os.getenv('AZURE_OPENAI_GPT4_DEPLOYMENT')}")
    print(f"Embedding Deployment: {os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT')}")
    
    # Create HTTP client
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    http_client = httpx.AsyncClient()
    
    client = AsyncAzureOpenAI(
        azure_endpoint=endpoint,
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        http_client=http_client
    )
    
    try:
        # Test embedding
        print("\n1. Testing embedding...")
        embedding_response = await client.embeddings.create(
            input="test query",
            model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
        )
        print(f"✅ Embedding works! Dimension: {len(embedding_response.data[0].embedding)}")
        
        # Test chat
        print("\n2. Testing chat completion...")
        chat_response = await client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_GPT4_DEPLOYMENT", "gpt-4o"),
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=10
        )
        print(f"✅ Chat works! Response: {chat_response.choices[0].message.content}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_azure_openai())
