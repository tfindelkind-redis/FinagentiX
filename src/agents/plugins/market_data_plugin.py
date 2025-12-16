"""
Market Data Plugin for Semantic Kernel
Provides tools for querying stock prices and technical indicators from Redis TimeSeries
"""

import asyncio
from typing import Dict, Any, List, Optional
import redis
from datetime import datetime, timedelta
from semantic_kernel.functions import kernel_function


class MarketDataPlugin:
    """
    Semantic Kernel plugin for market data operations
    
    Provides tools:
    - get_stock_price: Get current stock price from Redis TimeSeries
    - get_price_history: Get historical price data
    - get_price_change: Calculate price change over period
    - get_technical_indicators: Get moving averages and indicators
    """
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize Market Data Plugin
        
        Args:
            redis_client: Configured Redis client
        """
        self.redis = redis_client
    
    @kernel_function(
        name="get_stock_price",
        description="Get the current (most recent) stock price for a ticker symbol. Returns price, timestamp, and metric."
    )
    async def get_stock_price(
        self,
        ticker: str,
        metric: str = "close"
    ) -> Dict[str, Any]:
        """
        Get current stock price from Redis TimeSeries
        
        Args:
            ticker: Stock ticker symbol (e.g., AAPL, MSFT, GOOGL)
            metric: Price metric - 'open', 'high', 'low', 'close', or 'volume' (default: close)
        
        Returns:
            Dictionary with price data:
            {
                "ticker": str,
                "metric": str,
                "value": float,
                "timestamp": int (Unix timestamp in ms),
                "date": str (formatted date),
                "success": bool
            }
        """
        try:
            key = f"stock:{ticker.upper()}:{metric}"
            
            # Get latest value from TimeSeries
            result = self.redis.execute_command("TS.GET", key)
            
            if result and len(result) == 2:
                timestamp_ms, value = result
                timestamp_sec = timestamp_ms // 1000
                date_str = datetime.fromtimestamp(timestamp_sec).strftime("%Y-%m-%d %H:%M:%S")
                
                return {
                    "ticker": ticker.upper(),
                    "metric": metric,
                    "value": float(value),
                    "timestamp": timestamp_ms,
                    "date": date_str,
                    "success": True,
                    "message": f"{ticker.upper()} {metric}: ${float(value):.2f} as of {date_str}"
                }
            else:
                return {
                    "ticker": ticker.upper(),
                    "metric": metric,
                    "success": False,
                    "error": f"No data found for {ticker.upper()} {metric}",
                    "message": f"No data available for {ticker.upper()}"
                }
                
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "metric": metric,
                "success": False,
                "error": str(e),
                "message": f"Error retrieving {ticker.upper()} price: {str(e)}"
            }
    
    @kernel_function(
        name="get_price_history",
        description="Get historical stock price data for a time range. Returns array of timestamp/value pairs."
    )
    async def get_price_history(
        self,
        ticker: str,
        days: int = 30,
        metric: str = "close"
    ) -> Dict[str, Any]:
        """
        Get historical price data from Redis TimeSeries
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days of history to retrieve (default: 30)
            metric: Price metric (default: close)
        
        Returns:
            Dictionary with historical data and statistics
        """
        try:
            key = f"stock:{ticker.upper()}:{metric}"
            
            # Calculate timestamp range
            end_ts = int(datetime.now().timestamp() * 1000)
            start_ts = end_ts - (days * 24 * 60 * 60 * 1000)
            
            # Query range
            result = self.redis.execute_command(
                "TS.RANGE", key, start_ts, end_ts
            )
            
            if result and len(result) > 0:
                # Parse data
                data = [
                    {
                        "timestamp": ts,
                        "date": datetime.fromtimestamp(ts // 1000).strftime("%Y-%m-%d"),
                        "value": float(val)
                    }
                    for ts, val in result
                ]
                
                # Calculate statistics
                values = [d["value"] for d in data]
                stats = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "first": values[0],
                    "last": values[-1],
                    "change": values[-1] - values[0],
                    "change_pct": ((values[-1] - values[0]) / values[0]) * 100 if values[0] != 0 else 0
                }
                
                return {
                    "ticker": ticker.upper(),
                    "metric": metric,
                    "days": days,
                    "data": data,
                    "stats": stats,
                    "success": True,
                    "message": f"{ticker.upper()} {metric} over {days} days: ${stats['first']:.2f} → ${stats['last']:.2f} ({stats['change_pct']:+.2f}%)"
                }
            else:
                return {
                    "ticker": ticker.upper(),
                    "metric": metric,
                    "days": days,
                    "success": False,
                    "error": f"No historical data found for {ticker.upper()}",
                    "message": f"No historical data available for {ticker.upper()}"
                }
                
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "metric": metric,
                "days": days,
                "success": False,
                "error": str(e),
                "message": f"Error retrieving {ticker.upper()} history: {str(e)}"
            }
    
    @kernel_function(
        name="get_price_change",
        description="Calculate price change and percent change over a time period. Returns change amount and percentage."
    )
    async def get_price_change(
        self,
        ticker: str,
        days: int = 1,
        metric: str = "close"
    ) -> Dict[str, Any]:
        """
        Calculate price change over period
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back (default: 1 for daily change)
            metric: Price metric (default: close)
        
        Returns:
            Dictionary with price change information
        """
        try:
            # Get historical data
            history = await self.get_price_history(ticker, days=days + 1, metric=metric)
            
            if not history.get("success"):
                return history
            
            data = history["data"]
            if len(data) < 2:
                return {
                    "ticker": ticker.upper(),
                    "metric": metric,
                    "days": days,
                    "success": False,
                    "error": "Insufficient data for comparison",
                    "message": f"Not enough data to calculate change for {ticker.upper()}"
                }
            
            # Compare first and last values
            start_price = data[0]["value"]
            end_price = data[-1]["value"]
            change = end_price - start_price
            change_pct = (change / start_price) * 100 if start_price != 0 else 0
            
            # Determine trend
            if change_pct > 5:
                trend = "strong uptrend"
            elif change_pct > 0:
                trend = "uptrend"
            elif change_pct < -5:
                trend = "strong downtrend"
            elif change_pct < 0:
                trend = "downtrend"
            else:
                trend = "flat"
            
            return {
                "ticker": ticker.upper(),
                "metric": metric,
                "days": days,
                "start_price": start_price,
                "end_price": end_price,
                "change": change,
                "change_pct": change_pct,
                "trend": trend,
                "success": True,
                "message": f"{ticker.upper()} {days}-day change: ${start_price:.2f} → ${end_price:.2f} ({change_pct:+.2f}%) - {trend}"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "metric": metric,
                "days": days,
                "success": False,
                "error": str(e),
                "message": f"Error calculating price change for {ticker.upper()}: {str(e)}"
            }

    @kernel_function(
        name="get_technical_indicators",
        description="Calculate technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands) for a ticker."
    )
    async def get_technical_indicators(
        self,
        ticker: str,
        metric: str = "close",
        short_window: int = 20,
        long_window: int = 50,
        rsi_period: int = 14,
    ) -> Dict[str, Any]:
        """Compute a collection of technical indicators from historical data."""

        def compute_sma(values: List[float], window: int) -> Optional[float]:
            if not values:
                return None
            window = min(window, len(values))
            if window == 0:
                return None
            return sum(values[-window:]) / window

        def compute_ema_series(values: List[float], window: int) -> List[float]:
            if len(values) < window or window <= 1:
                return []
            smoothing = 2 / (window + 1)
            ema_values: List[float] = []
            ema = sum(values[:window]) / window
            ema_values.append(ema)
            for price in values[window:]:
                ema = (price - ema) * smoothing + ema
                ema_values.append(ema)
            return ema_values

        def compute_rsi(values: List[float], period: int) -> Optional[float]:
            if len(values) <= period:
                return None
            gains: List[float] = []
            losses: List[float] = []
            for i in range(1, len(values)):
                delta = values[i] - values[i - 1]
                if delta > 0:
                    gains.append(delta)
                    losses.append(0.0)
                else:
                    gains.append(0.0)
                    losses.append(abs(delta))
            gains_window = gains[-period:]
            losses_window = losses[-period:]
            if len(gains_window) < period or len(losses_window) < period:
                return None
            avg_gain = sum(gains_window) / period
            avg_loss = sum(losses_window) / period
            if avg_loss == 0:
                return 100.0
            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))

        def compute_bollinger(values: List[float], window: int) -> Optional[Dict[str, float]]:
            if len(values) < window:
                return None
            recent = values[-window:]
            mid = sum(recent) / window
            variance = sum((price - mid) ** 2 for price in recent) / window
            std_dev = variance ** 0.5
            return {
                "middle": mid,
                "upper": mid + (2 * std_dev),
                "lower": mid - (2 * std_dev),
            }

        try:
            lookback_days = max(long_window * 2, 120)
            history = await self.get_price_history(ticker, days=lookback_days, metric=metric)
            if not history.get("success"):
                return history

            data_points = history.get("data") or []
            values = [point["value"] for point in data_points if "value" in point]
            if len(values) < max(long_window, rsi_period + 1):
                return {
                    "ticker": ticker.upper(),
                    "metric": metric,
                    "success": False,
                    "error": "insufficient_data",
                    "message": f"Not enough data to compute indicators for {ticker.upper()}"
                }

            latest_price = values[-1]
            sma_short = compute_sma(values, short_window)
            sma_long = compute_sma(values, long_window)
            ema_short_series = compute_ema_series(values, 12)
            ema_long_series = compute_ema_series(values, 26)
            ema_short = ema_short_series[-1] if ema_short_series else None
            ema_long = ema_long_series[-1] if ema_long_series else None

            macd_series: List[float] = []
            if ema_short_series and ema_long_series:
                overlap = min(len(ema_short_series), len(ema_long_series))
                macd_series = [
                    ema_short_series[-overlap + idx] - ema_long_series[-overlap + idx]
                    for idx in range(overlap)
                ]
            macd_line = macd_series[-1] if macd_series else None
            signal_series = compute_ema_series(macd_series, 9) if macd_series else []
            signal_line = signal_series[-1] if signal_series else None
            histogram = macd_line - signal_line if macd_line is not None and signal_line is not None else None

            rsi = compute_rsi(values, rsi_period)
            bollinger = compute_bollinger(values, 20)

            support_window = min(30, len(values))
            support_range = values[-support_window:]
            support = min(support_range) if support_range else None
            resistance = max(support_range) if support_range else None

            trend = "neutral"
            if sma_short and sma_long:
                if abs(sma_short - sma_long) / sma_long < 0.01:
                    trend = "neutral"
                elif sma_short > sma_long:
                    trend = "bullish"
                else:
                    trend = "bearish"

            momentum = "neutral"
            if rsi is not None:
                if rsi >= 70:
                    momentum = "overbought"
                elif rsi <= 30:
                    momentum = "oversold"
                elif 55 <= rsi < 70:
                    momentum = "positive"
                elif 30 < rsi <= 45:
                    momentum = "negative"

            macd_note = None
            if macd_line is not None and signal_line is not None:
                if macd_line > signal_line:
                    macd_note = "MACD above signal"
                elif macd_line < signal_line:
                    macd_note = "MACD below signal"

            summary_parts = [f"Trend {trend}"]
            if momentum != "neutral":
                summary_parts.append(f"Momentum {momentum}")
            if macd_note:
                summary_parts.append(macd_note)
            summary = ", ".join(summary_parts)

            return {
                "ticker": ticker.upper(),
                "metric": metric,
                "success": True,
                "latest_price": latest_price,
                "sma": {
                    "short": sma_short,
                    "long": sma_long,
                },
                "ema": {
                    "short": ema_short,
                    "long": ema_long,
                },
                "macd": {
                    "line": macd_line,
                    "signal": signal_line,
                    "histogram": histogram,
                },
                "rsi": rsi,
                "bollinger": bollinger,
                "support": support,
                "resistance": resistance,
                "trend": trend,
                "momentum": momentum,
                "message": summary,
            }

        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "metric": metric,
                "success": False,
                "error": str(e),
                "message": f"Error computing indicators for {ticker.upper()}: {str(e)}"
            }
    
    @kernel_function(
        name="get_multiple_tickers",
        description="Get current prices for multiple ticker symbols at once. Useful for portfolio or comparison analysis."
    )
    async def get_multiple_tickers(
        self,
        tickers: str,
        metric: str = "close"
    ) -> Dict[str, Any]:
        """
        Get prices for multiple tickers
        
        Args:
            tickers: Comma-separated list of ticker symbols (e.g., "AAPL,MSFT,GOOGL")
            metric: Price metric (default: close)
        
        Returns:
            Dictionary with prices for all tickers
        """
        try:
            # Parse ticker list
            ticker_list = [t.strip().upper() for t in tickers.split(",")]
            
            # Get price for each ticker
            results = []
            for ticker in ticker_list:
                result = await self.get_stock_price(ticker, metric)
                results.append(result)
            
            # Summarize
            successful = [r for r in results if r.get("success")]
            failed = [r for r in results if not r.get("success")]
            
            return {
                "tickers": ticker_list,
                "metric": metric,
                "count": len(ticker_list),
                "successful": len(successful),
                "failed": len(failed),
                "results": results,
                "success": len(successful) > 0,
                "message": f"Retrieved prices for {len(successful)}/{len(ticker_list)} tickers"
            }
            
        except Exception as e:
            return {
                "tickers": tickers,
                "metric": metric,
                "success": False,
                "error": str(e),
                "message": f"Error retrieving multiple tickers: {str(e)}"
            }
    
    @kernel_function(
        name="get_volume_analysis",
        description="Analyze trading volume for a ticker. Returns volume statistics and trends."
    )
    async def get_volume_analysis(
        self,
        ticker: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze trading volume
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to analyze (default: 30)
        
        Returns:
            Dictionary with volume analysis
        """
        try:
            # Get volume history
            history = await self.get_price_history(ticker, days=days, metric="volume")
            
            if not history.get("success"):
                return history
            
            volumes = [d["value"] for d in history["data"]]
            avg_volume = sum(volumes) / len(volumes)
            current_volume = volumes[-1]
            
            # Calculate volume trend
            recent_avg = sum(volumes[-7:]) / min(7, len(volumes))  # Last week average
            volume_trend = ((current_volume - avg_volume) / avg_volume) * 100 if avg_volume != 0 else 0
            
            # Determine analysis
            if volume_trend > 50:
                analysis = "significantly above average - high interest"
            elif volume_trend > 20:
                analysis = "above average - increased interest"
            elif volume_trend < -50:
                analysis = "significantly below average - low interest"
            elif volume_trend < -20:
                analysis = "below average - decreased interest"
            else:
                analysis = "around average - normal trading"
            
            return {
                "ticker": ticker.upper(),
                "days": days,
                "current_volume": current_volume,
                "avg_volume": avg_volume,
                "volume_trend_pct": volume_trend,
                "analysis": analysis,
                "success": True,
                "message": f"{ticker.upper()} volume: {current_volume:,.0f} ({volume_trend:+.1f}% vs avg) - {analysis}"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "days": days,
                "success": False,
                "error": str(e),
                "message": f"Error analyzing volume for {ticker.upper()}: {str(e)}"
            }


# Example usage and testing
if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from sk_config import get_redis_client
    
    async def test_plugin():
        """Test the Market Data Plugin"""
        print("Testing Market Data Plugin...\n")
        
        # Get Redis client
        redis_client = get_redis_client()
        
        # Create plugin
        plugin = MarketDataPlugin(redis_client)
        
        # Test 1: Get current price
        print("Test 1: Get current AAPL price")
        result = await plugin.get_stock_price("AAPL", "close")
        print(f"Result: {result.get('message')}\n")
        
        # Test 2: Get price history
        print("Test 2: Get AAPL price history (30 days)")
        result = await plugin.get_price_history("AAPL", days=30)
        if result.get("success"):
            stats = result["stats"]
            print(f"Result: {stats['count']} data points, ${stats['first']:.2f} → ${stats['last']:.2f} ({stats['change_pct']:+.2f}%)\n")
        
        # Test 3: Get price change
        print("Test 3: Get AAPL 7-day price change")
        result = await plugin.get_price_change("AAPL", days=7)
        print(f"Result: {result.get('message')}\n")
        
        # Test 4: Get multiple tickers
        print("Test 4: Get prices for multiple tickers")
        result = await plugin.get_multiple_tickers("AAPL,MSFT,GOOGL")
        print(f"Result: {result.get('message')}\n")
        
        # Test 5: Volume analysis
        print("Test 5: Analyze AAPL trading volume")
        result = await plugin.get_volume_analysis("AAPL", days=30)
        print(f"Result: {result.get('message')}\n")
        
        print("✅ All tests completed!")
    
    # Run tests
    asyncio.run(test_plugin())
