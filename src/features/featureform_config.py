"""
Feature Store Configuration for FinagentiX

Defines feature store setup using Redis as the backing store.
Features include technical indicators, risk metrics, and valuation ratios.

This is a Redis-native implementation that follows the Featureform pattern
but without the Featureform dependency (Python 3.13 compatibility).
"""

from typing import List, Dict
import os


# Feature definitions
TECHNICAL_INDICATORS = [
    {
        "name": "sma_20",
        "description": "20-day Simple Moving Average",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "sma_50",
        "description": "50-day Simple Moving Average",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "sma_200",
        "description": "200-day Simple Moving Average",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "ema_12",
        "description": "12-day Exponential Moving Average",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "ema_26",
        "description": "26-day Exponential Moving Average",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "rsi_14",
        "description": "14-day Relative Strength Index",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "macd",
        "description": "MACD (12-26-9)",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "macd_signal",
        "description": "MACD Signal Line (9-day EMA)",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "macd_histogram",
        "description": "MACD Histogram (MACD - Signal)",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "bollinger_upper",
        "description": "Bollinger Band Upper (20-day SMA + 2σ)",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "bollinger_middle",
        "description": "Bollinger Band Middle (20-day SMA)",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "bollinger_lower",
        "description": "Bollinger Band Lower (20-day SMA - 2σ)",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    }
]

RISK_METRICS = [
    {
        "name": "volatility_30d",
        "description": "30-day annualized volatility",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "volatility_90d",
        "description": "90-day annualized volatility",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "beta",
        "description": "Beta vs SPY (252 days)",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "var_95",
        "description": "Value at Risk (95% confidence)",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "cvar_95",
        "description": "Conditional Value at Risk (95%)",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "sharpe_ratio",
        "description": "Sharpe Ratio (252 days, 4% risk-free rate)",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    },
    {
        "name": "max_drawdown",
        "description": "Maximum drawdown (252 days)",
        "variant": "default",
        "source": "market_data",
        "entity": "ticker"
    }
]

VALUATION_METRICS = [
    {
        "name": "pe_ratio",
        "description": "Price-to-Earnings Ratio",
        "variant": "default",
        "source": "financial_data",
        "entity": "ticker"
    },
    {
        "name": "pb_ratio",
        "description": "Price-to-Book Ratio",
        "variant": "default",
        "source": "financial_data",
        "entity": "ticker"
    },
    {
        "name": "ps_ratio",
        "description": "Price-to-Sales Ratio",
        "variant": "default",
        "source": "financial_data",
        "entity": "ticker"
    },
    {
        "name": "dividend_yield",
        "description": "Dividend Yield (%)",
        "variant": "default",
        "source": "financial_data",
        "entity": "ticker"
    },
    {
        "name": "market_cap",
        "description": "Market Capitalization (USD)",
        "variant": "default",
        "source": "financial_data",
        "entity": "ticker"
    }
]


def get_all_features() -> List[str]:
    """Get list of all feature names."""
    all_features = TECHNICAL_INDICATORS + RISK_METRICS + VALUATION_METRICS
    return [f["name"] for f in all_features]


def get_feature_metadata(feature_name: str) -> Dict:
    """Get metadata for a specific feature."""
    all_features = TECHNICAL_INDICATORS + RISK_METRICS + VALUATION_METRICS
    for feature in all_features:
        if feature["name"] == feature_name:
            return feature
    return None


# Feature store key patterns
FEATURE_KEY_PREFIX = "ff:feature"

def get_feature_key(ticker: str, feature_name: str) -> str:
    """
    Generate Redis key for a feature value.
    
    Args:
        ticker: Stock ticker symbol
        feature_name: Name of the feature
        
    Returns:
        Redis key string (e.g., "ff:feature:AAPL:sma_20")
    """
    return f"{FEATURE_KEY_PREFIX}:{ticker.upper()}:{feature_name}"


# TTL configurations
FEATURE_TTL = {
    "technical_indicators": 3600,  # 1 hour
    "risk_metrics": 86400,  # 24 hours
    "valuation_metrics": 86400 * 7  # 7 days
}


def get_feature_ttl(feature_name: str) -> int:
    """Get TTL for a feature in seconds."""
    if feature_name in [f["name"] for f in TECHNICAL_INDICATORS]:
        return FEATURE_TTL["technical_indicators"]
    elif feature_name in [f["name"] for f in RISK_METRICS]:
        return FEATURE_TTL["risk_metrics"]
    elif feature_name in [f["name"] for f in VALUATION_METRICS]:
        return FEATURE_TTL["valuation_metrics"]
    return 3600  # Default 1 hour
