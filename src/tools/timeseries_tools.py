"""
Time Series Tools - Redis TimeSeries operations for stock market data

Tools for retrieving:
- Current and historical stock prices
- Trading volume data
- Price history over time ranges
"""

from typing import List, Dict, Optional, Any, Tuple
import redis
from datetime import datetime, timedelta
from src.agents.config import get_config


def _get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    config = get_config()
    return redis.Redis(
        host=config.redis.host,
        port=config.redis.port,
        password=config.redis.password,
        ssl=config.redis.ssl,
        decode_responses=False  # TimeSeries needs binary mode
    )


def get_stock_price(
    ticker: str,
    date: Optional[str] = None,
    price_type: str = "close"
) -> Optional[float]:
    """
    Get stock price for a specific date or latest price.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        date: Optional date in YYYY-MM-DD format (if None, returns latest)
        price_type: Type of price - "open", "high", "low", "close", "adj_close"
        
    Returns:
        Price as float, or None if not found
        
    Example:
        # Latest closing price
        price = get_stock_price("AAPL")
        
        # Historical price
        price = get_stock_price("AAPL", date="2024-01-15", price_type="open")
    """
    redis_client = _get_redis_client()
    
    # Build TimeSeries key
    ts_key = f"ts:{ticker}:{price_type}"
    
    try:
        if date:
            # Get price for specific date
            timestamp = int(datetime.strptime(date, "%Y-%m-%d").timestamp() * 1000)
            
            # Get value at timestamp (or closest before)
            result = redis_client.execute_command(
                "TS.GET", ts_key, "FILTER", f"timestamp<={timestamp}"
            )
            
            if result and len(result) == 2:
                return float(result[1])
        else:
            # Get latest price
            result = redis_client.execute_command("TS.GET", ts_key)
            
            if result and len(result) == 2:
                return float(result[1])
        
        return None
    
    except Exception as e:
        print(f"Error getting stock price for {ticker}: {e}")
        return None


def get_trading_volume(
    ticker: str,
    date: Optional[str] = None
) -> Optional[int]:
    """
    Get trading volume for a specific date or latest volume.
    
    Args:
        ticker: Stock ticker symbol
        date: Optional date in YYYY-MM-DD format
        
    Returns:
        Volume as integer, or None if not found
        
    Example:
        volume = get_trading_volume("AAPL", date="2024-01-15")
    """
    redis_client = _get_redis_client()
    
    ts_key = f"ts:{ticker}:volume"
    
    try:
        if date:
            timestamp = int(datetime.strptime(date, "%Y-%m-%d").timestamp() * 1000)
            result = redis_client.execute_command(
                "TS.GET", ts_key, "FILTER", f"timestamp<={timestamp}"
            )
        else:
            result = redis_client.execute_command("TS.GET", ts_key)
        
        if result and len(result) == 2:
            return int(float(result[1]))
        
        return None
    
    except Exception as e:
        print(f"Error getting trading volume for {ticker}: {e}")
        return None


def get_price_history(
    ticker: str,
    start_date: str,
    end_date: Optional[str] = None,
    price_type: str = "close",
    aggregation: Optional[str] = None
) -> List[Tuple[str, float]]:
    """
    Get historical price data over a time range.
    
    Args:
        ticker: Stock ticker symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (if None, uses today)
        price_type: Type of price - "open", "high", "low", "close", "adj_close"
        aggregation: Optional aggregation ("avg", "max", "min") with time bucket
        
    Returns:
        List of (date, price) tuples sorted by date
        
    Example:
        # Daily prices
        prices = get_price_history("AAPL", start_date="2024-01-01", end_date="2024-01-31")
        
        # Weekly average prices
        prices = get_price_history(
            "AAPL",
            start_date="2024-01-01",
            aggregation="avg:7d"
        )
    """
    redis_client = _get_redis_client()
    
    ts_key = f"ts:{ticker}:{price_type}"
    
    # Convert dates to timestamps (milliseconds)
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    
    if end_date:
        end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
    else:
        end_ts = int(datetime.now().timestamp() * 1000)
    
    try:
        if aggregation:
            # Parse aggregation (e.g., "avg:7d", "max:1w")
            agg_type, time_bucket = aggregation.split(":")
            time_bucket_ms = _parse_time_bucket(time_bucket)
            
            result = redis_client.execute_command(
                "TS.RANGE", ts_key, start_ts, end_ts,
                "AGGREGATION", agg_type.upper(), time_bucket_ms
            )
        else:
            # Get raw data points
            result = redis_client.execute_command(
                "TS.RANGE", ts_key, start_ts, end_ts
            )
        
        # Convert to list of (date, price) tuples
        price_history = []
        for timestamp, value in result:
            date_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d")
            price_history.append((date_str, float(value)))
        
        return price_history
    
    except Exception as e:
        print(f"Error getting price history for {ticker}: {e}")
        return []


def _parse_time_bucket(bucket: str) -> int:
    """
    Parse time bucket string to milliseconds.
    
    Args:
        bucket: Time bucket like "1d", "7d", "1w", "1M"
        
    Returns:
        Milliseconds
    """
    import re
    
    match = re.match(r"(\d+)([smhdwMy])", bucket)
    if not match:
        raise ValueError(f"Invalid time bucket format: {bucket}")
    
    value, unit = match.groups()
    value = int(value)
    
    conversions = {
        "s": 1000,  # seconds
        "m": 60 * 1000,  # minutes
        "h": 60 * 60 * 1000,  # hours
        "d": 24 * 60 * 60 * 1000,  # days
        "w": 7 * 24 * 60 * 60 * 1000,  # weeks
        "M": 30 * 24 * 60 * 60 * 1000,  # months (approx)
        "y": 365 * 24 * 60 * 60 * 1000,  # years (approx)
    }
    
    return value * conversions[unit]


def get_ohlcv_data(
    ticker: str,
    start_date: str,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get full OHLCV (Open, High, Low, Close, Volume) data.
    
    Args:
        ticker: Stock ticker symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        List of dicts with keys: date, open, high, low, close, volume
        
    Example:
        ohlcv = get_ohlcv_data("AAPL", start_date="2024-01-01", end_date="2024-01-31")
        for day in ohlcv:
            print(f"{day['date']}: O={day['open']} H={day['high']} L={day['low']} C={day['close']} V={day['volume']}")
    """
    # Get each price type
    open_prices = dict(get_price_history(ticker, start_date, end_date, price_type="open"))
    high_prices = dict(get_price_history(ticker, start_date, end_date, price_type="high"))
    low_prices = dict(get_price_history(ticker, start_date, end_date, price_type="low"))
    close_prices = dict(get_price_history(ticker, start_date, end_date, price_type="close"))
    volumes = dict([(date, vol) for date, vol in 
                    [(d, get_trading_volume(ticker, d)) for d in open_prices.keys()]
                    if vol is not None])
    
    # Combine into OHLCV records
    ohlcv_data = []
    for date in sorted(open_prices.keys()):
        if all([
            date in open_prices,
            date in high_prices,
            date in low_prices,
            date in close_prices,
            date in volumes
        ]):
            ohlcv_data.append({
                "date": date,
                "open": open_prices[date],
                "high": high_prices[date],
                "low": low_prices[date],
                "close": close_prices[date],
                "volume": volumes[date]
            })
    
    return ohlcv_data
