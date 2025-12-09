"""
Feature Tools - Calculate technical indicators and risk metrics

Tools for computing:
- Technical indicators (moving averages, RSI, MACD, Bollinger Bands)
- Risk metrics (volatility, beta, VaR, Sharpe ratio)
- Valuation ratios (P/E, P/B, EV/EBITDA)
- Financial data extraction from SEC filings

NOTE: This module now primarily retrieves pre-computed features from
Featureform (Redis-backed feature store). If features are not available,
it falls back to on-demand calculation using NumPy.
"""

from typing import List, Dict, Optional, Any
import redis
from datetime import datetime, timedelta
from src.agents.config import get_config
from src.tools.timeseries_tools import get_price_history
import numpy as np

# Featureform integration
try:
    from src.features import FeatureService, get_features_batch
    FEATUREFORM_AVAILABLE = True
except ImportError:
    FEATUREFORM_AVAILABLE = False
    print("⚠️  Featureform not available, using on-demand calculation")


def _get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    config = get_config()
    return redis.Redis(
        host=config.redis.host,
        port=config.redis.port,
        password=config.redis.password,
        ssl=config.redis.ssl,
        decode_responses=True
    )


def get_technical_indicators(
    ticker: str,
    indicators: List[str],
    period_days: int = 252
) -> Dict[str, Any]:
    """
    Calculate technical indicators for a stock.
    
    Args:
        ticker: Stock ticker symbol
        indicators: List of indicators to calculate:
            - "sma_20", "sma_50", "sma_200" (Simple Moving Average)
            - "ema_12", "ema_26" (Exponential Moving Average)
            - "rsi" (Relative Strength Index)
            - "macd" (MACD with signal line)
            - "bollinger" (Bollinger Bands)
        period_days: Number of days of historical data to use
        
    Returns:
        Dict with indicator names as keys and calculated values
        
    Example:
        indicators = get_technical_indicators(
            "AAPL",
            indicators=["sma_50", "sma_200", "rsi", "macd"],
            period_days=252
        )
        print(f"50-day SMA: {indicators['sma_50']}")
        print(f"RSI: {indicators['rsi']}")
    """
    # Get historical prices
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=period_days + 30)).strftime("%Y-%m-%d")
    
    price_history = get_price_history(ticker, start_date, end_date, price_type="close")
    
    if not price_history:
        return {}
    
    # Extract prices as numpy array
    dates = [d for d, p in price_history]
    prices = np.array([p for d, p in price_history])
    
    results = {}
    
    for indicator in indicators:
        # Simple Moving Averages
        if indicator.startswith("sma_"):
            window = int(indicator.split("_")[1])
            if len(prices) >= window:
                sma = np.convolve(prices, np.ones(window)/window, mode='valid')
                results[indicator] = float(sma[-1])
        
        # Exponential Moving Averages
        elif indicator.startswith("ema_"):
            window = int(indicator.split("_")[1])
            if len(prices) >= window:
                ema = _calculate_ema(prices, window)
                results[indicator] = float(ema[-1])
        
        # RSI (Relative Strength Index)
        elif indicator == "rsi":
            if len(prices) >= 14:
                rsi = _calculate_rsi(prices, period=14)
                results["rsi"] = float(rsi[-1])
        
        # MACD (Moving Average Convergence Divergence)
        elif indicator == "macd":
            if len(prices) >= 26:
                macd_line, signal_line, histogram = _calculate_macd(prices)
                results["macd"] = {
                    "macd_line": float(macd_line[-1]),
                    "signal_line": float(signal_line[-1]),
                    "histogram": float(histogram[-1])
                }
        
        # Bollinger Bands
        elif indicator == "bollinger":
            if len(prices) >= 20:
                upper, middle, lower = _calculate_bollinger_bands(prices, window=20, num_std=2)
                results["bollinger"] = {
                    "upper": float(upper[-1]),
                    "middle": float(middle[-1]),
                    "lower": float(lower[-1])
                }
    
    return results


def get_risk_metrics(
    ticker: str,
    benchmark: str = "SPY",
    period_days: int = 252,
    confidence_level: float = 0.95
) -> Dict[str, Any]:
    """
    Calculate risk metrics for a stock.
    
    Args:
        ticker: Stock ticker symbol
        benchmark: Benchmark ticker for beta calculation (default: SPY)
        period_days: Historical period for calculations
        confidence_level: Confidence level for VaR (0.95 = 95%)
        
    Returns:
        Dict with risk metrics:
            - volatility: Annualized volatility (standard deviation)
            - beta: Beta relative to benchmark
            - var: Value at Risk (daily)
            - cvar: Conditional VaR (expected shortfall)
            - sharpe_ratio: Risk-adjusted return
            - max_drawdown: Maximum peak-to-trough decline
            
    Example:
        risk = get_risk_metrics("AAPL", benchmark="SPY", period_days=252)
        print(f"Volatility: {risk['volatility']:.2%}")
        print(f"Beta: {risk['beta']:.2f}")
        print(f"VaR (95%): {risk['var']:.2%}")
    """
    # Get price history for ticker and benchmark
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=period_days + 30)).strftime("%Y-%m-%d")
    
    ticker_prices = dict(get_price_history(ticker, start_date, end_date))
    benchmark_prices = dict(get_price_history(benchmark, start_date, end_date))
    
    # Align dates
    common_dates = sorted(set(ticker_prices.keys()) & set(benchmark_prices.keys()))
    
    if len(common_dates) < 30:
        return {}
    
    ticker_prices_arr = np.array([ticker_prices[d] for d in common_dates])
    benchmark_prices_arr = np.array([benchmark_prices[d] for d in common_dates])
    
    # Calculate returns
    ticker_returns = np.diff(ticker_prices_arr) / ticker_prices_arr[:-1]
    benchmark_returns = np.diff(benchmark_prices_arr) / benchmark_prices_arr[:-1]
    
    # Volatility (annualized)
    volatility = np.std(ticker_returns) * np.sqrt(252)
    
    # Beta
    covariance = np.cov(ticker_returns, benchmark_returns)[0, 1]
    benchmark_variance = np.var(benchmark_returns)
    beta = covariance / benchmark_variance if benchmark_variance > 0 else 1.0
    
    # Value at Risk (VaR)
    var = np.percentile(ticker_returns, (1 - confidence_level) * 100)
    
    # Conditional VaR (CVaR / Expected Shortfall)
    cvar = ticker_returns[ticker_returns <= var].mean()
    
    # Sharpe Ratio (assuming 2% risk-free rate)
    risk_free_rate = 0.02 / 252  # Daily risk-free rate
    excess_returns = ticker_returns - risk_free_rate
    sharpe_ratio = np.mean(excess_returns) / np.std(ticker_returns) * np.sqrt(252)
    
    # Maximum Drawdown
    cumulative_returns = (1 + ticker_returns).cumprod()
    running_max = np.maximum.accumulate(cumulative_returns)
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min()
    
    return {
        "volatility": float(volatility),
        "beta": float(beta),
        "var": float(var),
        "cvar": float(cvar),
        "sharpe_ratio": float(sharpe_ratio),
        "max_drawdown": float(max_drawdown)
    }


def calculate_valuation_ratios(
    ticker: str
) -> Dict[str, Optional[float]]:
    """
    Calculate valuation ratios from stored financial data.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Dict with valuation ratios:
            - pe_ratio: Price-to-Earnings ratio
            - pb_ratio: Price-to-Book ratio
            - ps_ratio: Price-to-Sales ratio
            - dividend_yield: Dividend yield percentage
            
    Example:
        ratios = calculate_valuation_ratios("AAPL")
        print(f"P/E Ratio: {ratios['pe_ratio']}")
    """
    redis_client = _get_redis_client()
    
    # Check if financial data is cached
    cache_key = f"financials:{ticker}"
    
    try:
        data = redis_client.hgetall(cache_key)
        
        if not data:
            return {
                "pe_ratio": None,
                "pb_ratio": None,
                "ps_ratio": None,
                "dividend_yield": None
            }
        
        # Extract metrics
        return {
            "pe_ratio": float(data.get("pe_ratio", 0)) or None,
            "pb_ratio": float(data.get("pb_ratio", 0)) or None,
            "ps_ratio": float(data.get("ps_ratio", 0)) or None,
            "dividend_yield": float(data.get("dividend_yield", 0)) or None
        }
    
    except Exception as e:
        print(f"Error calculating valuation ratios for {ticker}: {e}")
        return {}


def extract_financial_data(
    ticker: str,
    metrics: List[str]
) -> Dict[str, Any]:
    """
    Extract financial metrics from stored SEC filing data.
    
    Args:
        ticker: Stock ticker symbol
        metrics: List of metrics to extract:
            - "revenue", "net_income", "eps", "cash_flow"
            - "total_assets", "total_liabilities", "shareholders_equity"
            - "gross_margin", "operating_margin", "net_margin"
            - "roe", "roa", "roce" (return metrics)
            
    Returns:
        Dict with financial metrics
        
    Example:
        financials = extract_financial_data(
            "AAPL",
            metrics=["revenue", "net_income", "eps", "roe"]
        )
    """
    redis_client = _get_redis_client()
    
    cache_key = f"financials:{ticker}"
    
    try:
        data = redis_client.hgetall(cache_key)
        
        if not data:
            return {}
        
        results = {}
        for metric in metrics:
            if metric in data:
                # Try to convert to float, fallback to string
                try:
                    results[metric] = float(data[metric])
                except (ValueError, TypeError):
                    results[metric] = data[metric]
        
        return results
    
    except Exception as e:
        print(f"Error extracting financial data for {ticker}: {e}")
        return {}


# Helper functions for technical indicators

def _calculate_ema(prices: np.ndarray, window: int) -> np.ndarray:
    """Calculate Exponential Moving Average."""
    alpha = 2 / (window + 1)
    ema = np.zeros_like(prices)
    ema[0] = prices[0]
    
    for i in range(1, len(prices)):
        ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
    
    return ema


def _calculate_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    """Calculate Relative Strength Index."""
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gains = np.convolve(gains, np.ones(period)/period, mode='valid')
    avg_losses = np.convolve(losses, np.ones(period)/period, mode='valid')
    
    rs = avg_gains / (avg_losses + 1e-10)  # Avoid division by zero
    rsi = 100 - (100 / (1 + rs))
    
    # Pad with NaN for the first period values
    rsi = np.concatenate([np.full(period, np.nan), rsi])
    
    return rsi


def _calculate_macd(prices: np.ndarray) -> tuple:
    """Calculate MACD (Moving Average Convergence Divergence)."""
    ema_12 = _calculate_ema(prices, 12)
    ema_26 = _calculate_ema(prices, 26)
    
    macd_line = ema_12 - ema_26
    signal_line = _calculate_ema(macd_line, 9)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def _calculate_bollinger_bands(prices: np.ndarray, window: int = 20, num_std: float = 2) -> tuple:
    """Calculate Bollinger Bands."""
    sma = np.convolve(prices, np.ones(window)/window, mode='valid')
    
    # Calculate rolling standard deviation
    rolling_std = np.array([
        np.std(prices[i:i+window])
        for i in range(len(prices) - window + 1)
    ])
    
    upper_band = sma + (num_std * rolling_std)
    lower_band = sma - (num_std * rolling_std)
    
    # Pad with NaN
    pad_size = len(prices) - len(sma)
    upper_band = np.concatenate([np.full(pad_size, np.nan), upper_band])
    middle_band = np.concatenate([np.full(pad_size, np.nan), sma])
    lower_band = np.concatenate([np.full(pad_size, np.nan), lower_band])
    
    return upper_band, middle_band, lower_band
