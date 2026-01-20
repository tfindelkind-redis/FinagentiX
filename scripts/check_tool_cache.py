#!/usr/bin/env python3
"""Check tool cache contents"""
import redis
import os
import json

r = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 10000)),
    password=os.environ.get('REDIS_PASSWORD', ''),
    ssl=os.environ.get('REDIS_SSL', 'true').lower() == 'true',
    decode_responses=True
)

# Check tool cache key
key = 'tool:news_sentiment:b1ab2478'
val = r.get(key)
if val:
    print(f"=== {key} ===")
    wrapper = json.loads(val)
    print(f"Wrapper keys: {list(wrapper.keys())}")
    print(f"params: {wrapper.get('params')}")
    
    data = wrapper.get('output', {})
    print(f"Output keys: {list(data.keys())}")
    
    if 'articles' in data:
        print(f"articles.count: {data['articles'].get('count')}")
        print(f"articles.results len: {len(data['articles'].get('results', []))}")
    if 'news' in data:
        print(f"news.count: {data['news'].get('count')}")
    if 'sentiment' in data:
        sent = data['sentiment']
        if isinstance(sent, dict):
            print(f"sentiment.overall_sentiment: {sent.get('overall_sentiment')}")
            print(f"sentiment.articles_analyzed: {sent.get('articles_analyzed')}")
else:
    print(f"Key {key} not found")
