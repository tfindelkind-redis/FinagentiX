"""
Yahoo Finance Data Source Evaluation
Test script to verify data availability, format, and timeframes
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import json

def test_yahoo_finance():
    """Test Yahoo Finance API capabilities"""
    
    print("=" * 60)
    print("Yahoo Finance Data Source Evaluation")
    print("=" * 60)
    print()
    
    # Test ticker
    ticker = "AAPL"
    print(f"Testing with ticker: {ticker}")
    print()
    
    # Create ticker object
    stock = yf.Ticker(ticker)
    
    # 1. Test Company Info
    print("1. COMPANY INFORMATION")
    print("-" * 60)
    try:
        info = stock.info
        print(f"   Company Name: {info.get('longName', 'N/A')}")
        print(f"   Sector: {info.get('sector', 'N/A')}")
        print(f"   Industry: {info.get('industry', 'N/A')}")
        print(f"   Market Cap: ${info.get('marketCap', 0):,.0f}")
        print(f"   Currency: {info.get('currency', 'N/A')}")
        print("   ✅ Company info available")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # 2. Test Historical Data - Different Timeframes
    print("2. HISTORICAL DATA AVAILABILITY")
    print("-" * 60)
    
    timeframes = [
        ("1 Day (1min intervals)", "1d", "1m"),
        ("5 Days (5min intervals)", "5d", "5m"),
        ("1 Month (1hour intervals)", "1mo", "1h"),
        ("3 Months (daily)", "3mo", "1d"),
        ("1 Year (daily)", "1y", "1d"),
        ("5 Years (daily)", "5y", "1d"),
        ("10 Years (daily)", "10y", "1d"),
        ("Max available (daily)", "max", "1d"),
    ]
    
    results = []
    
    for desc, period, interval in timeframes:
        try:
            df = stock.history(period=period, interval=interval)
            if not df.empty:
                result = {
                    "description": desc,
                    "period": period,
                    "interval": interval,
                    "available": True,
                    "records": len(df),
                    "start_date": df.index[0].strftime("%Y-%m-%d %H:%M:%S"),
                    "end_date": df.index[-1].strftime("%Y-%m-%d %H:%M:%S"),
                    "columns": list(df.columns)
                }
                results.append(result)
                print(f"   ✅ {desc}")
                print(f"      Records: {len(df):,}")
                print(f"      Period: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
                print(f"      Columns: {', '.join(df.columns)}")
            else:
                print(f"   ⚠️  {desc} - No data returned")
                results.append({
                    "description": desc,
                    "available": False,
                    "error": "Empty dataframe"
                })
        except Exception as e:
            print(f"   ❌ {desc} - Error: {e}")
            results.append({
                "description": desc,
                "available": False,
                "error": str(e)
            })
        print()
    
    # 3. Test Data Format - Sample records
    print("3. DATA FORMAT SAMPLE (Last 5 days, daily)")
    print("-" * 60)
    try:
        df = stock.history(period="5d", interval="1d")
        print(df.to_string())
        print()
        print("   Sample record structure:")
        if not df.empty:
            sample = df.iloc[0].to_dict()
            print(json.dumps({k: float(v) if pd.notna(v) else None for k, v in sample.items()}, indent=4))
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # 4. Test News/Events
    print("4. NEWS & EVENTS")
    print("-" * 60)
    try:
        news = stock.news
        if news:
            print(f"   ✅ Recent news articles: {len(news)}")
            if len(news) > 0:
                latest = news[0]
                print(f"   Latest: {latest.get('title', 'N/A')}")
                print(f"   Publisher: {latest.get('publisher', 'N/A')}")
                print(f"   Available fields: {', '.join(latest.keys())}")
        else:
            print("   ⚠️  No news available")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # 5. Test Financial Statements
    print("5. FINANCIAL STATEMENTS")
    print("-" * 60)
    try:
        # Income Statement
        income_stmt = stock.financials
        if income_stmt is not None and not income_stmt.empty:
            print(f"   ✅ Income Statement: {income_stmt.shape[0]} line items, {income_stmt.shape[1]} periods")
        
        # Balance Sheet
        balance = stock.balance_sheet
        if balance is not None and not balance.empty:
            print(f"   ✅ Balance Sheet: {balance.shape[0]} line items, {balance.shape[1]} periods")
        
        # Cash Flow
        cashflow = stock.cashflow
        if cashflow is not None and not cashflow.empty:
            print(f"   ✅ Cash Flow: {cashflow.shape[0]} line items, {cashflow.shape[1]} periods")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # 6. Test Multiple Tickers
    print("6. MULTIPLE TICKERS TEST")
    print("-" * 60)
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    try:
        data = yf.download(tickers, period="5d", interval="1d", group_by="ticker", progress=False)
        print(f"   ✅ Successfully downloaded {len(tickers)} tickers")
        print(f"   Shape: {data.shape}")
        print(f"   Tickers: {', '.join(tickers)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    available_timeframes = [r for r in results if r.get('available', False)]
    print(f"✅ Available timeframes: {len(available_timeframes)}/{len(results)}")
    print()
    print("RECOMMENDED FOR FINAGENTIX:")
    print("  • Historical: 2-5 years daily data for backtesting")
    print("  • Real-time: Daily updates (1d interval)")
    print("  • Intraday: 1-5 days with 1m/5m intervals for recent analysis")
    print("  • News: Available via .news property")
    print("  • Fundamentals: Income statement, balance sheet, cash flow")
    print()
    print("LIMITATIONS:")
    print("  • Intraday data limited to recent days (1-60 days depending on interval)")
    print("  • Rate limiting: Recommended to batch requests")
    print("  • No official API - web scraping based (may break)")
    print()
    print("ALTERNATIVE SOURCES TO CONSIDER:")
    print("  • Alpha Vantage (500 requests/day free)")
    print("  • Polygon.io (free tier available)")
    print("  • IEX Cloud (free tier available)")
    print("  • Quandl/Nasdaq Data Link")

if __name__ == "__main__":
    test_yahoo_finance()
