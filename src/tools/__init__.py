"""
FinagentiX Redis Tools - Phase 5.3

This module contains all Redis-based tools for agents to use:
- Vector search tools (SEC filings, news articles, semantic cache)
- Time series tools (stock prices, volume data)
- Feature tools (technical indicators, risk metrics)
- Cache tools (tool output caching, query response caching)

Usage:
    from src.tools import search_sec_filings, get_stock_price
    
    filings = search_sec_filings(query="revenue recognition", ticker="AAPL", top_k=5)
    price = get_stock_price(ticker="AAPL", date="2024-12-01")
"""

from src.tools.vector_tools import (
    search_sec_filings,
    search_news,
    search_similar_queries,
)

from src.tools.timeseries_tools import (
    get_stock_price,
    get_trading_volume,
    get_price_history,
)

from src.tools.feature_tools import (
    get_technical_indicators,
    get_risk_metrics,
    calculate_valuation_ratios,
    extract_financial_data,
)

from src.tools.cache_tools import (
    check_semantic_cache,
    cache_query_response,
    invalidate_cache,
    get_cache_stats,
)

__all__ = [
    # Vector search
    "search_sec_filings",
    "search_news",
    "search_similar_queries",
    
    # Time series
    "get_stock_price",
    "get_trading_volume",
    "get_price_history",
    
    # Features
    "get_technical_indicators",
    "get_risk_metrics",
    "calculate_valuation_ratios",
    "extract_financial_data",
    
    # Caching
    "check_semantic_cache",
    "cache_query_response",
    "invalidate_cache",
    "get_cache_stats",
]
