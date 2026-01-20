#!/usr/bin/env python3
"""Debug test for the workflow's news sentiment"""
import asyncio
import sys
sys.path.insert(0, '/app')

from src.orchestration.workflows import InvestmentAnalysisWorkflow
from src.redis.tool_cache import ToolCache
from src.redis.client import get_redis_client

async def test():
    redis = get_redis_client()
    print(f'Redis ping: {redis.ping()}')
    
    # Create workflow
    tool_cache = ToolCache(redis_client=redis)
    workflow = InvestmentAnalysisWorkflow(tool_cache=tool_cache, redis_client=redis)
    
    # Test the plugin directly first
    print('\n=== Testing plugin.get_ticker_news("MSFT") ===')
    news = await workflow.news_sentiment.get_ticker_news("MSFT", limit=5)
    print(f'News keys: {list(news.keys())}')
    print(f'News count: {news.get("count")}')
    print(f'News results len: {len(news.get("results", []))}')
    
    print('\n=== Testing plugin.get_news_sentiment("MSFT") ===')
    sentiment = await workflow.news_sentiment.get_news_sentiment("MSFT")
    print(f'Sentiment keys: {list(sentiment.keys())}')
    print(f'Sentiment overall: {sentiment.get("overall_sentiment")}')
    
    # Now simulate what _structure_news_result does
    print('\n=== Simulating _structure_news_result ===')
    raw_payload = {"news": news, "sentiment": sentiment}
    print(f'payload keys: {list(raw_payload.keys())}')
    print(f'payload["news"].get("count"): {raw_payload["news"].get("count")}')
    print(f'payload["news"].get("results") len: {len(raw_payload["news"].get("results", []))}')
    
    # Test with workflow method
    print('\n=== Testing workflow._get_news_sentiment("MSFT") ===')
    result = await workflow._get_news_sentiment("MSFT")
    print(f'Result keys: {list(result.keys())}')
    articles = result.get("articles", {})
    print(f'Articles: {articles}')

if __name__ == '__main__':
    asyncio.run(test())
