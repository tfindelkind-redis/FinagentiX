#!/usr/bin/env python3
"""Test news search index"""
import os
import redis
import json
from dotenv import load_dotenv
load_dotenv()

def main():
    r = redis.Redis(
        host=os.getenv('REDIS_HOST'),
        port=int(os.getenv('REDIS_PORT', 10000)),
        password=os.getenv('REDIS_PASSWORD'),
        ssl=True,
        decode_responses=True
    )
    
    # Check indexes
    print("=" * 60)
    print("Testing News Search Indexes")
    print("=" * 60)
    
    from redis.commands.search.query import Query
    
    # Test idx:news_articles with different queries
    print("\n📰 Testing idx:news_articles searches...")
    info = r.ft('idx:news_articles').info()
    print(f"   Total docs: {info.get('num_docs', 0)}")
    
    # 1. Using ticker_tag (TAG field)  
    print("\n   1. @ticker_tag:{MSFT}")
    try:
        results = r.ft('idx:news_articles').search(Query("@ticker_tag:{MSFT}").paging(0, 3))
        print(f"      Results: {results.total}")
        for doc in results.docs:
            print(f"      - {getattr(doc, 'title', 'No title')[:50]}")
    except Exception as e:
        print(f"      Error: {e}")
    
    # 2. Using ticker (TEXT field)
    print("\n   2. @ticker:MSFT")
    try:
        results = r.ft('idx:news_articles').search(Query("@ticker:MSFT").paging(0, 3))
        print(f"      Results: {results.total}")
    except Exception as e:
        print(f"      Error: {e}")
    
    # 3. Full text search
    print("\n   3. Microsoft (full text)")
    try:
        results = r.ft('idx:news_articles').search(Query("Microsoft").paging(0, 3))
        print(f"      Results: {results.total}")
        for doc in results.docs:
            print(f"      - {getattr(doc, 'title', 'No title')[:50]}")
    except Exception as e:
        print(f"      Error: {e}")
    
    # 4. Wildcard all
    print("\n   4. * (all docs)")
    try:
        results = r.ft('idx:news_articles').search(Query("*").paging(0, 3))
        print(f"      Results: {results.total}")
        for doc in results.docs:
            ticker = getattr(doc, 'ticker', 'N/A')
            title = getattr(doc, 'title', 'No title')[:40]
            print(f"      - [{ticker}] {title}")
    except Exception as e:
        print(f"      Error: {e}")
    
    # Get raw MSFT news article
    print("\n🔍 Raw news article for MSFT...")
    keys = list(r.scan_iter('news:MSFT:*', count=10))
    if keys:
        key = keys[0]
        key_type = r.type(key)
        print(f"   Key: {key}")
        print(f"   Type: {key_type}")
        if key_type == 'ReJSON-RL':
            data = r.execute_command('JSON.GET', key)
            article = json.loads(data)
            print(f"   Title: {article.get('title', 'N/A')[:50]}...")
            print(f"   Ticker: {article.get('ticker', 'N/A')}")
            print(f"   Ticker_tag: {article.get('ticker_tag', 'N/A')}")
            print(f"   Has embedding: {'embedding' in article}")
    
    print("\n✅ Test complete!")

if __name__ == "__main__":
    main()
