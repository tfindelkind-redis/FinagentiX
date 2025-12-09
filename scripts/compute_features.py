"""
Feature Computation Script

Batch job to compute and store features in Featureform (Redis-backed).
Run this periodically (e.g., daily) to update all technical indicators,
risk metrics, and valuation ratios.

Usage:
    python scripts/compute_features.py --tickers AAPL,MSFT,GOOGL
    python scripts/compute_features.py --all  # All tickers in Redis
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict
import redis
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.config import get_config
from src.features.featureform_config import (
    get_feature_key,
    get_feature_ttl,
    TECHNICAL_INDICATORS,
    RISK_METRICS,
    VALUATION_METRICS
)
from src.tools.timeseries_tools import get_price_history, get_stock_price
from src.tools.feature_tools import (
    _calculate_ema,
    _calculate_rsi,
    _calculate_macd,
    _calculate_bollinger_bands
)


def get_redis_client():
    """Get Redis client."""
    config = get_config()
    return redis.Redis(
        host=config.redis.host,
        port=config.redis.port,
        password=config.redis.password,
        ssl=config.redis.ssl,
        decode_responses=True
    )


def get_all_tickers() -> List[str]:
    """Get all tickers from Redis TimeSeries."""
    client = get_redis_client()
    keys = client.keys("ts:*:close")
    tickers = set()
    for key in keys:
        # Extract ticker from key: ts:AAPL:close -> AAPL
        parts = key.split(":")
        if len(parts) >= 2:
            tickers.add(parts[1])
    return sorted(list(tickers))


def compute_technical_indicators(ticker: str, period_days: int = 252) -> Dict[str, float]:
    """
    Compute all technical indicators for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        period_days: Historical period for calculations
        
    Returns:
        Dict mapping indicator names to values
    """
    features = {}
    
    # Get historical prices
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days + 100)  # Extra buffer
    
    price_data = get_price_history(
        ticker=ticker,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        price_type="close"
    )
    
    if not price_data or len(price_data) < 50:
        print(f"⚠️  Insufficient data for {ticker} ({len(price_data) if price_data else 0} days)")
        return features
    
    prices = np.array([p[1] for p in price_data])
    
    # Simple Moving Averages
    if len(prices) >= 20:
        features["sma_20"] = float(np.mean(prices[-20:]))
    
    if len(prices) >= 50:
        features["sma_50"] = float(np.mean(prices[-50:]))
    
    if len(prices) >= 200:
        features["sma_200"] = float(np.mean(prices[-200:]))
    
    # Exponential Moving Averages
    if len(prices) >= 12:
        features["ema_12"] = float(_calculate_ema(prices, 12))
    
    if len(prices) >= 26:
        features["ema_26"] = float(_calculate_ema(prices, 26))
    
    # RSI
    if len(prices) >= 15:
        features["rsi_14"] = float(_calculate_rsi(prices, 14))
    
    # MACD
    if len(prices) >= 35:
        macd_data = _calculate_macd(prices)
        features["macd"] = float(macd_data["macd"])
        features["macd_signal"] = float(macd_data["signal"])
        features["macd_histogram"] = float(macd_data["histogram"])
    
    # Bollinger Bands
    if len(prices) >= 20:
        bb_data = _calculate_bollinger_bands(prices, 20, 2)
        features["bollinger_upper"] = float(bb_data["upper"])
        features["bollinger_middle"] = float(bb_data["middle"])
        features["bollinger_lower"] = float(bb_data["lower"])
    
    return features


def compute_risk_metrics(ticker: str, period_days: int = 252) -> Dict[str, float]:
    """
    Compute all risk metrics for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        period_days: Historical period for calculations
        
    Returns:
        Dict mapping metric names to values
    """
    features = {}
    
    # Get historical prices
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days + 10)
    
    price_data = get_price_history(
        ticker=ticker,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        price_type="close"
    )
    
    benchmark_data = get_price_history(
        ticker="SPY",
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        price_type="close"
    )
    
    if not price_data or len(price_data) < 30:
        return features
    
    prices = np.array([p[1] for p in price_data])
    returns = np.diff(prices) / prices[:-1]
    
    # 30-day volatility
    if len(returns) >= 30:
        features["volatility_30d"] = float(np.std(returns[-30:]) * np.sqrt(252))
    
    # 90-day volatility
    if len(returns) >= 90:
        features["volatility_90d"] = float(np.std(returns[-90:]) * np.sqrt(252))
    
    # Beta (vs SPY)
    if benchmark_data and len(benchmark_data) >= len(price_data):
        benchmark_prices = np.array([p[1] for p in benchmark_data])
        benchmark_returns = np.diff(benchmark_prices) / benchmark_prices[:-1]
        
        # Align lengths
        min_len = min(len(returns), len(benchmark_returns))
        returns_aligned = returns[-min_len:]
        benchmark_aligned = benchmark_returns[-min_len:]
        
        covariance = np.cov(returns_aligned, benchmark_aligned)[0, 1]
        benchmark_variance = np.var(benchmark_aligned)
        
        if benchmark_variance > 0:
            features["beta"] = float(covariance / benchmark_variance)
    
    # VaR and CVaR (95%)
    if len(returns) >= 30:
        var_95 = float(np.percentile(returns, 5))
        features["var_95"] = var_95
        features["cvar_95"] = float(np.mean(returns[returns <= var_95]))
    
    # Sharpe Ratio (assume 4% risk-free rate)
    if len(returns) >= 30:
        risk_free_rate = 0.04 / 252  # Daily rate
        excess_returns = returns - risk_free_rate
        if np.std(excess_returns) > 0:
            features["sharpe_ratio"] = float(
                np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
            )
    
    # Maximum Drawdown
    cumulative = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    features["max_drawdown"] = float(np.min(drawdown))
    
    return features


def compute_valuation_metrics(ticker: str) -> Dict[str, float]:
    """
    Get valuation metrics from Redis (already stored by data ingestion).
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Dict mapping metric names to values
    """
    client = get_redis_client()
    features = {}
    
    try:
        data = client.hgetall(f"financials:{ticker}")
        
        if data:
            # Map from financial data to features
            if "pe_ratio" in data:
                features["pe_ratio"] = float(data["pe_ratio"])
            if "pb_ratio" in data:
                features["pb_ratio"] = float(data["pb_ratio"])
            if "ps_ratio" in data:
                features["ps_ratio"] = float(data["ps_ratio"])
            if "dividend_yield" in data:
                features["dividend_yield"] = float(data["dividend_yield"])
            if "market_cap" in data:
                features["market_cap"] = float(data["market_cap"])
                
    except Exception as e:
        print(f"⚠️  Error getting valuation metrics for {ticker}: {e}")
    
    return features


def store_features(ticker: str, features: Dict[str, float]):
    """
    Store computed features in Redis with appropriate TTLs.
    
    Args:
        ticker: Stock ticker symbol
        features: Dict mapping feature names to values
    """
    client = get_redis_client()
    
    for feature_name, value in features.items():
        key = get_feature_key(ticker, feature_name)
        ttl = get_feature_ttl(feature_name)
        
        try:
            client.set(key, value, ex=ttl)
        except Exception as e:
            print(f"⚠️  Error storing {feature_name} for {ticker}: {e}")


def compute_features_for_ticker(ticker: str):
    """Compute and store all features for a ticker."""
    print(f"\n{'='*60}")
    print(f"Computing features for {ticker}")
    print(f"{'='*60}")
    
    all_features = {}
    
    # Technical indicators
    print(f"📊 Computing technical indicators...")
    tech_indicators = compute_technical_indicators(ticker)
    all_features.update(tech_indicators)
    print(f"   ✅ Computed {len(tech_indicators)} technical indicators")
    
    # Risk metrics
    print(f"⚠️  Computing risk metrics...")
    risk_metrics = compute_risk_metrics(ticker)
    all_features.update(risk_metrics)
    print(f"   ✅ Computed {len(risk_metrics)} risk metrics")
    
    # Valuation metrics
    print(f"💰 Getting valuation metrics...")
    valuation_metrics = compute_valuation_metrics(ticker)
    all_features.update(valuation_metrics)
    print(f"   ✅ Got {len(valuation_metrics)} valuation metrics")
    
    # Store all features
    if all_features:
        print(f"💾 Storing {len(all_features)} features in Redis...")
        store_features(ticker, all_features)
        print(f"   ✅ Stored successfully")
    else:
        print(f"   ⚠️  No features computed")
    
    return all_features


def main():
    parser = argparse.ArgumentParser(description="Compute features for Featureform")
    parser.add_argument(
        "--tickers",
        type=str,
        help="Comma-separated list of tickers (e.g., AAPL,MSFT,GOOGL)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Compute features for all tickers in Redis"
    )
    
    args = parser.parse_args()
    
    # Determine tickers to process
    if args.all:
        tickers = get_all_tickers()
        print(f"Found {len(tickers)} tickers in Redis")
    elif args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    else:
        print("Error: Must specify --tickers or --all")
        return
    
    print(f"\n{'='*60}")
    print(f"FEATUREFORM BATCH JOB - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"Processing {len(tickers)} tickers: {', '.join(tickers[:10])}")
    if len(tickers) > 10:
        print(f"... and {len(tickers) - 10} more")
    
    # Process each ticker
    results = {}
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] {ticker}")
        try:
            features = compute_features_for_ticker(ticker)
            results[ticker] = {"success": True, "features": len(features)}
        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            results[ticker] = {"success": False, "error": str(e)}
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    successful = sum(1 for r in results.values() if r["success"])
    failed = len(results) - successful
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    
    if failed > 0:
        print(f"\nFailed tickers:")
        for ticker, result in results.items():
            if not result["success"]:
                print(f"  - {ticker}: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
