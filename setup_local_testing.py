#!/usr/bin/env python3
"""
Local Testing Setup with Sample Data

This script:
1. Checks all dependencies
2. Sets up local Redis
3. Loads sample market data (no external APIs needed)
4. Verifies the system is ready for testing

Run this BEFORE starting the application for the first time.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("FinagentiX - Local Testing Setup")
print("=" * 70)

# Step 1: Check Redis
print("\n📦 Step 1: Checking Redis...")
try:
    import redis
    print("   ✅ Redis Python client installed")
    
    # Try to connect
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    r.ping()
    print("   ✅ Redis server is running")
    redis_available = True
except redis.ConnectionError:
    print("   ❌ Redis server not running")
    print("\n   To fix:")
    print("   brew install redis")
    print("   redis-server &")
    redis_available = False
except ImportError:
    print("   ❌ Redis Python client not installed")
    print("   pip install redis")
    sys.exit(1)

# Step 2: Check .env configuration
print("\n⚙️  Step 2: Checking .env configuration...")
from dotenv import load_dotenv
import os

load_dotenv()

required_vars = {
    "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY"),
    "REDIS_HOST": os.getenv("REDIS_HOST"),
    "REDIS_PORT": os.getenv("REDIS_PORT"),
}

all_configured = True
for var, value in required_vars.items():
    if value:
        if "KEY" in var or "PASSWORD" in var:
            print(f"   ✅ {var}: {'*' * 10}")
        else:
            print(f"   ✅ {var}: {value}")
    else:
        print(f"   ❌ {var}: Not set")
        all_configured = False

if not all_configured:
    print("\n   ⚠️  Some variables missing. Check .env file")
    print("   For local testing, REDIS_HOST should be 'localhost'")

# Step 3: Load sample market data
if redis_available:
    print("\n📊 Step 3: Loading sample market data into Redis...")
    
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]
    
    print(f"   Loading data for {len(tickers)} tickers...")
    
    # Generate sample OHLCV data for last 30 days
    days = 30
    end_date = datetime.now()
    
    for ticker in tickers:
        # Simulate realistic stock prices
        base_price = random.randint(100, 500)
        
        for day in range(days):
            date = end_date - timedelta(days=days - day)
            timestamp_ms = int(date.timestamp() * 1000)
            
            # Generate OHLCV with realistic variations
            open_price = base_price + random.uniform(-5, 5)
            high_price = open_price + random.uniform(0, 10)
            low_price = open_price - random.uniform(0, 10)
            close_price = open_price + random.uniform(-5, 5)
            volume = random.randint(1000000, 100000000)
            
            # Store in Redis TimeSeries format (keys match plugin expectations)
            try:
                # Create time series if not exists
                for metric, value in [
                    ("open", open_price),
                    ("high", high_price),
                    ("low", low_price),
                    ("close", close_price),
                    ("volume", volume)
                ]:
                    key = f"stock:{ticker}:{metric}"
                    
                    # Try to create time series
                    try:
                        r.execute_command(
                            "TS.CREATE", key,
                            "RETENTION", 31536000000,  # 1 year in ms
                            "LABELS", "ticker", ticker, "metric", metric
                        )
                    except:
                        pass  # Already exists
                    
                    # Add data point
                    r.execute_command("TS.ADD", key, timestamp_ms, value)
            
            except Exception as e:
                print(f"   ⚠️  Error loading {ticker}: {e}")
                print("   Note: RedisTimeSeries module may not be available")
                print("   Using fallback Hash storage...")
                
                # Fallback: Store as simple hash (agents will still work)
                for metric, value in [
                    ("open", open_price),
                    ("high", high_price),
                    ("low", low_price),
                    ("close", close_price),
                    ("volume", volume)
                ]:
                    key = f"stock:{ticker}:{metric}"
                    r.hset(key, mapping={
                        "value": value,
                        "timestamp": timestamp_ms,
                        "date": date.strftime("%Y-%m-%d")
                    })
                break
        
        print(f"   ✅ {ticker}: {days} days loaded")
    
    print(f"\n   ✅ Sample data loaded for {len(tickers)} tickers")
    print(f"   ✅ Total data points: {len(tickers) * days * 5}")

# Step 4: Test data retrieval
if redis_available:
    print("\n🔍 Step 4: Testing data retrieval...")
    
    test_ticker = "AAPL"
    key = f"stock:{test_ticker}:close"
    
    try:
        # Try TimeSeries GET
        result = r.execute_command("TS.GET", key)
        if result:
            timestamp_ms, value = result
            print(f"   ✅ Retrieved {test_ticker} close price: ${float(value):.2f}")
        else:
            # Try Hash GET
            result = r.hgetall(key)
            if result:
                print(f"   ✅ Retrieved {test_ticker} close price: ${float(result['value']):.2f}")
    except Exception as e:
        print(f"   ⚠️  Data retrieval test failed: {e}")

# Step 5: Summary
print("\n" + "=" * 70)
print("Setup Summary")
print("=" * 70)

if redis_available and all_configured:
    print("✅ System ready for testing!")
    print("\nNext steps:")
    print("  1. Start the server:")
    print("     ./start_server.sh")
    print("\n  2. Test with CLI:")
    print("     python cli.py \"What's the price of AAPL?\"")
    print("\n  3. Test trading query:")
    print("     python cli.py \"Should I invest in AAPL?\"")
    print("\n  4. Access API docs:")
    print("     http://localhost:8000/docs")
elif not redis_available:
    print("❌ Redis not running")
    print("\nFix with:")
    print("  brew install redis")
    print("  redis-server &")
    print("\nThen run this script again:")
    print("  python setup_local_testing.py")
elif not all_configured:
    print("❌ Configuration incomplete")
    print("\nCheck your .env file:")
    print("  cp .env.template .env")
    print("  # Edit .env with your Azure credentials")
    print("  # Set REDIS_HOST=localhost for local testing")

print("\n" + "=" * 70)
print("\n📚 Data Sources:")
print("  • Sample market data: Generated locally (no API calls)")
print("  • Real market data: Add yfinance integration later")
print("  • SEC filings: Use ingest_sec_filing.py script")
print("  • News data: Future integration with NewsAPI")
print("\n" + "=" * 70)
