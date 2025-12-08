#!/usr/bin/env python3
"""
Monitor embedding generation progress
"""

import redis
import os
import time
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def check_progress():
    """Check and display embedding progress"""
    r = redis.Redis(
        host=os.getenv('REDIS_HOST'),
        port=int(os.getenv('REDIS_PORT')),
        password=os.getenv('REDIS_PASSWORD'),
        decode_responses=False,
        ssl=True
    )
    
    print(f"\n{'='*60}")
    print(f"  Embedding Generation Progress - {datetime.now().strftime('%I:%M:%S %p')}")
    print(f"{'='*60}\n")
    
    # Count documents
    sec_keys = list(r.scan_iter('sec:*', count=3000))
    news_keys = list(r.scan_iter('news:*', count=3000))
    
    # Get tickers from SEC filings
    sec_tickers = set()
    for key in sec_keys:
        parts = key.decode().split(':')
        if len(parts) >= 2:
            sec_tickers.add(parts[1])
    
    # Get tickers from news
    news_tickers = set()
    for key in news_keys:
        parts = key.decode().split(':')
        if len(parts) >= 2:
            news_tickers.add(parts[1])
    
    # Display stats
    print(f"📄 SEC Filing Documents: {len(sec_keys)}")
    print(f"   Tickers: {len(sec_tickers)}/28")
    if sec_tickers:
        print(f"   List: {', '.join(sorted(sec_tickers))}")
    
    print(f"\n📰 News Article Documents: {len(news_keys)}")
    print(f"   Tickers: {len(news_tickers)}/28")
    if news_tickers:
        print(f"   List: {', '.join(sorted(news_tickers))}")
    
    print(f"\n📊 Total Documents: {len(sec_keys) + len(news_keys)}")
    
    # Estimated progress
    target_sec = 28 * 2  # 28 tickers × 2 filing types (10-K, 10-Q)
    target_news = 280    # Approximately 10 articles per ticker
    total_target = target_sec + target_news
    
    current_total = len(sec_keys) + len(news_keys)
    progress_pct = (current_total / total_target) * 100 if total_target > 0 else 0
    
    print(f"\n📈 Overall Progress: {progress_pct:.1f}%")
    print(f"   ({current_total}/{total_target} estimated documents)")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        # Watch mode - refresh every 30 seconds
        try:
            while True:
                check_progress()
                time.sleep(30)
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped\n")
    else:
        # Single check
        check_progress()
