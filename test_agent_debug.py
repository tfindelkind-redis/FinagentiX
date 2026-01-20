#!/usr/bin/env python3
"""Debug test for news sentiment agent"""
import asyncio
import sys
sys.path.insert(0, '/app')

from src.agents.news_sentiment_agent import NewsSentimentAgent

async def test():
    agent = NewsSentimentAgent()
    print(f'Agent name: {agent.name}')
    print(f'Redis host: {agent.config.redis.host}')
    print(f'Redis port: {agent.config.redis.port}')
    print(f'Plugin index: {agent.plugin.index_name}')
    
    # Test the plugin directly
    result = await agent.plugin.get_ticker_news('MSFT', limit=3)
    print(f'Plugin direct result - count: {result.get("count")}')
    print(f'Plugin direct result - success: {result.get("success")}')
    
    # Now test through the agent run method
    run_result = await agent.run('MSFT news', {'ticker': 'MSFT', 'top_k': 3})
    articles = run_result.get('articles', {})
    print(f'Agent run articles count: {articles.get("count", "N/A")}')
    print(f'Agent run articles success: {articles.get("success", "N/A")}')
    sentiment = run_result.get('sentiment', {})
    print(f'Agent sentiment: {sentiment.get("overall_sentiment", "N/A")}')
    print(f'Agent sentiment analyzed: {sentiment.get("articles_analyzed", "N/A")}')

if __name__ == '__main__':
    asyncio.run(test())
