#!/usr/bin/env python3
"""Test the news sentiment plugin"""
import redis
import os
import asyncio
import json
import sys

sys.path.insert(0, 'src')

# Redis connection
r = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=int(os.getenv('REDIS_PORT', 10000)),
    password=os.getenv('REDIS_PASSWORD'),
    ssl=True,
    decode_responses=True
)

from agents.plugins.news_sentiment_plugin import NewsSentimentPlugin

plugin = NewsSentimentPlugin(r)

async def test():
    print("Testing get_ticker_news('MSFT')...")
    result = await plugin.get_ticker_news("MSFT", limit=5)
    print(f"  count: {result.get('count')}")
    print(f"  success: {result.get('success')}")
    print(f"  message: {result.get('message')}")
    if result.get('results'):
        print("  Results:")
        for a in result['results'][:3]:
            print(f"    - {a.get('sentiment')}: {a.get('title')[:50]}...")
    
    print("\nTesting get_news_sentiment('MSFT')...")
    result2 = await plugin.get_news_sentiment("MSFT", days=7)
    print(f"  articles_analyzed: {result2.get('articles_analyzed')}")
    print(f"  sentiment_distribution: {result2.get('sentiment_distribution')}")
    print(f"  overall_sentiment: {result2.get('overall_sentiment')}")

asyncio.run(test())
