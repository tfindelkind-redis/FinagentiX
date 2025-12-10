"""
Technical Analysis Plugin for Semantic Kernel
Provides tools for calculating technical indicators and chart patterns
"""

import asyncio
from typing import Dict, Any, List, Optional
import redis
from datetime import datetime
from semantic_kernel.functions import kernel_function


class TechnicalAnalysisPlugin:
    """
    Semantic Kernel plugin for technical analysis operations
    
    Provides tools:
    - calculate_sma: Calculate Simple Moving Average
    - calculate_rsi: Calculate Relative Strength Index
    - calculate_macd: Calculate MACD indicator
    - detect_crossover: Detect moving average crossovers
    - get_support_resistance: Identify support and resistance levels
    """
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize Technical Analysis Plugin
        
        Args:
            redis_client: Configured Redis client with TimeSeries
        """
        self.redis = redis_client
    
    @kernel_function(
        name="calculate_sma",
        description="Calculate Simple Moving Average for a stock. Returns SMA value and trend analysis."
    )
    async def calculate_sma(
        self,
        ticker: str,
        period: int = 20,
        metric: str = "close"
    ) -> Dict[str, Any]:
        """
        Calculate Simple Moving Average
        
        Args:
            ticker: Stock ticker symbol
            period: Number of periods for SMA (default: 20)
            metric: Price metric (default: close)
        
        Returns:
            Dictionary with SMA calculation
        """
        try:
            key = f"stock:{ticker.upper()}:{metric}"
            
            # Get recent data
            end_ts = int(datetime.now().timestamp() * 1000)
            start_ts = end_ts - (period * 2 * 24 * 60 * 60 * 1000)  # Double period for safety
            
            result = self.redis.execute_command("TS.RANGE", key, start_ts, end_ts)
            
            if not result or len(result) < period:
                return {
                    "ticker": ticker.upper(),
                    "period": period,
                    "success": False,
                    "error": f"Insufficient data (need {period} points, got {len(result) if result else 0})"
                }
            
            # Extract values
            values = [float(val) for ts, val in result[-period:]]
            current_price = values[-1]
            sma = sum(values) / len(values)
            
            # Determine trend
            if current_price > sma * 1.02:
                trend = "above SMA - bullish"
            elif current_price < sma * 0.98:
                trend = "below SMA - bearish"
            else:
                trend = "near SMA - neutral"
            
            return {
                "ticker": ticker.upper(),
                "metric": metric,
                "period": period,
                "sma": round(sma, 2),
                "current_price": round(current_price, 2),
                "difference": round(current_price - sma, 2),
                "difference_pct": round(((current_price - sma) / sma) * 100, 2),
                "trend": trend,
                "success": True,
                "message": f"{ticker.upper()} {period}-period SMA: ${sma:.2f} (current: ${current_price:.2f}, {trend})"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "period": period,
                "success": False,
                "error": str(e),
                "message": f"Error calculating SMA: {str(e)}"
            }
    
    @kernel_function(
        name="calculate_rsi",
        description="Calculate Relative Strength Index for a stock. Returns RSI value and overbought/oversold status."
    )
    async def calculate_rsi(
        self,
        ticker: str,
        period: int = 14,
        metric: str = "close"
    ) -> Dict[str, Any]:
        """
        Calculate Relative Strength Index
        
        Args:
            ticker: Stock ticker symbol
            period: Number of periods for RSI (default: 14)
            metric: Price metric (default: close)
        
        Returns:
            Dictionary with RSI calculation
        """
        try:
            key = f"stock:{ticker.upper()}:{metric}"
            
            # Get recent data
            end_ts = int(datetime.now().timestamp() * 1000)
            start_ts = end_ts - ((period + 1) * 2 * 24 * 60 * 60 * 1000)
            
            result = self.redis.execute_command("TS.RANGE", key, start_ts, end_ts)
            
            if not result or len(result) < period + 1:
                return {
                    "ticker": ticker.upper(),
                    "period": period,
                    "success": False,
                    "error": "Insufficient data for RSI calculation"
                }
            
            # Calculate price changes
            values = [float(val) for ts, val in result[-(period + 1):]]
            changes = [values[i] - values[i-1] for i in range(1, len(values))]
            
            # Separate gains and losses
            gains = [c if c > 0 else 0 for c in changes]
            losses = [abs(c) if c < 0 else 0 for c in changes]
            
            # Calculate average gain and loss
            avg_gain = sum(gains) / period
            avg_loss = sum(losses) / period
            
            # Calculate RSI
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            # Determine status
            if rsi >= 70:
                status = "overbought"
                signal = "consider selling or taking profits"
            elif rsi <= 30:
                status = "oversold"
                signal = "consider buying or accumulating"
            else:
                status = "neutral"
                signal = "no strong signal"
            
            return {
                "ticker": ticker.upper(),
                "period": period,
                "rsi": round(rsi, 2),
                "status": status,
                "signal": signal,
                "success": True,
                "message": f"{ticker.upper()} RSI({period}): {rsi:.1f} - {status}, {signal}"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "period": period,
                "success": False,
                "error": str(e),
                "message": f"Error calculating RSI: {str(e)}"
            }
    
    @kernel_function(
        name="detect_crossover",
        description="Detect moving average crossovers (bullish/bearish signals). Returns crossover detection and trading signal."
    )
    async def detect_crossover(
        self,
        ticker: str,
        short_period: int = 10,
        long_period: int = 20,
        metric: str = "close"
    ) -> Dict[str, Any]:
        """
        Detect moving average crossover
        
        Args:
            ticker: Stock ticker symbol
            short_period: Short MA period (default: 10)
            long_period: Long MA period (default: 20)
            metric: Price metric (default: close)
        
        Returns:
            Dictionary with crossover detection
        """
        try:
            # Calculate both SMAs
            short_sma = await self.calculate_sma(ticker, short_period, metric)
            long_sma = await self.calculate_sma(ticker, long_period, metric)
            
            if not short_sma.get("success") or not long_sma.get("success"):
                return {
                    "ticker": ticker.upper(),
                    "success": False,
                    "error": "Unable to calculate moving averages"
                }
            
            short_value = short_sma["sma"]
            long_value = long_sma["sma"]
            current_price = short_sma["current_price"]
            
            # Detect crossover
            if short_value > long_value * 1.01:
                crossover_type = "bullish"
                signal = f"Golden Cross - Short MA ({short_period}) above Long MA ({long_period})"
                recommendation = "buy signal"
            elif short_value < long_value * 0.99:
                crossover_type = "bearish"
                signal = f"Death Cross - Short MA ({short_period}) below Long MA ({long_period})"
                recommendation = "sell signal"
            else:
                crossover_type = "neutral"
                signal = "MAs are converging"
                recommendation = "wait for clearer signal"
            
            return {
                "ticker": ticker.upper(),
                "short_ma": {"period": short_period, "value": round(short_value, 2)},
                "long_ma": {"period": long_period, "value": round(long_value, 2)},
                "current_price": round(current_price, 2),
                "crossover_type": crossover_type,
                "signal": signal,
                "recommendation": recommendation,
                "success": True,
                "message": f"{ticker.upper()}: {signal} - {recommendation}"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "success": False,
                "error": str(e),
                "message": f"Error detecting crossover: {str(e)}"
            }
    
    @kernel_function(
        name="get_support_resistance",
        description="Identify support and resistance levels based on price history. Returns key price levels."
    )
    async def get_support_resistance(
        self,
        ticker: str,
        days: int = 30,
        metric: str = "close"
    ) -> Dict[str, Any]:
        """
        Identify support and resistance levels
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to analyze (default: 30)
            metric: Price metric (default: close)
        
        Returns:
            Dictionary with support/resistance levels
        """
        try:
            key = f"stock:{ticker.upper()}:{metric}"
            
            # Get historical data
            end_ts = int(datetime.now().timestamp() * 1000)
            start_ts = end_ts - (days * 24 * 60 * 60 * 1000)
            
            result = self.redis.execute_command("TS.RANGE", key, start_ts, end_ts)
            
            if not result or len(result) < 10:
                return {
                    "ticker": ticker.upper(),
                    "success": False,
                    "error": "Insufficient data"
                }
            
            # Extract values
            values = [float(val) for ts, val in result]
            current_price = values[-1]
            
            # Calculate levels
            max_price = max(values)
            min_price = min(values)
            avg_price = sum(values) / len(values)
            
            # Support: recent lows
            recent_lows = sorted(values)[:5]
            support = sum(recent_lows) / len(recent_lows)
            
            # Resistance: recent highs
            recent_highs = sorted(values, reverse=True)[:5]
            resistance = sum(recent_highs) / len(recent_highs)
            
            # Distance from levels
            dist_to_support = ((current_price - support) / support) * 100
            dist_to_resistance = ((resistance - current_price) / current_price) * 100
            
            # Position analysis
            if current_price >= resistance * 0.98:
                position = "near resistance"
                analysis = "may face selling pressure"
            elif current_price <= support * 1.02:
                position = "near support"
                analysis = "may find buying support"
            else:
                position = "between levels"
                analysis = "trading in range"
            
            return {
                "ticker": ticker.upper(),
                "days": days,
                "current_price": round(current_price, 2),
                "support": round(support, 2),
                "resistance": round(resistance, 2),
                "range_high": round(max_price, 2),
                "range_low": round(min_price, 2),
                "distance_to_support": round(dist_to_support, 2),
                "distance_to_resistance": round(dist_to_resistance, 2),
                "position": position,
                "analysis": analysis,
                "success": True,
                "message": f"{ticker.upper()}: ${current_price:.2f} ({position}) - Support: ${support:.2f}, Resistance: ${resistance:.2f}"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "success": False,
                "error": str(e),
                "message": f"Error calculating support/resistance: {str(e)}"
            }
    
    @kernel_function(
        name="get_volatility",
        description="Calculate price volatility (standard deviation). Returns volatility metrics and risk assessment."
    )
    async def get_volatility(
        self,
        ticker: str,
        days: int = 20,
        metric: str = "close"
    ) -> Dict[str, Any]:
        """
        Calculate price volatility
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to analyze (default: 20)
            metric: Price metric (default: close)
        
        Returns:
            Dictionary with volatility metrics
        """
        try:
            key = f"stock:{ticker.upper()}:{metric}"
            
            # Get historical data
            end_ts = int(datetime.now().timestamp() * 1000)
            start_ts = end_ts - (days * 24 * 60 * 60 * 1000)
            
            result = self.redis.execute_command("TS.RANGE", key, start_ts, end_ts)
            
            if not result or len(result) < days:
                return {
                    "ticker": ticker.upper(),
                    "success": False,
                    "error": "Insufficient data"
                }
            
            # Calculate returns
            values = [float(val) for ts, val in result]
            returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
            
            # Calculate volatility (standard deviation of returns)
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            volatility = variance ** 0.5
            
            # Annualize volatility (assuming 252 trading days)
            annualized_volatility = volatility * (252 ** 0.5)
            
            # Risk assessment
            if annualized_volatility > 0.5:
                risk_level = "very high"
                assessment = "extremely volatile - high risk"
            elif annualized_volatility > 0.3:
                risk_level = "high"
                assessment = "highly volatile - elevated risk"
            elif annualized_volatility > 0.2:
                risk_level = "moderate"
                assessment = "moderately volatile - normal risk"
            else:
                risk_level = "low"
                assessment = "relatively stable - lower risk"
            
            return {
                "ticker": ticker.upper(),
                "days": days,
                "volatility": round(volatility * 100, 2),
                "annualized_volatility": round(annualized_volatility * 100, 2),
                "risk_level": risk_level,
                "assessment": assessment,
                "success": True,
                "message": f"{ticker.upper()} volatility: {annualized_volatility*100:.1f}% annualized - {risk_level} risk"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "success": False,
                "error": str(e),
                "message": f"Error calculating volatility: {str(e)}"
            }


# Example usage and testing
if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from sk_config import get_redis_client
    
    async def test_plugin():
        """Test the Technical Analysis Plugin"""
        print("Testing Technical Analysis Plugin...\n")
        
        # Get Redis client
        redis_client = get_redis_client()
        
        # Create plugin
        plugin = TechnicalAnalysisPlugin(redis_client)
        
        # Test 1: Calculate SMA
        print("Test 1: Calculate 20-period SMA for AAPL")
        result = await plugin.calculate_sma("AAPL", period=20)
        print(f"Result: {result.get('message')}\n")
        
        # Test 2: Calculate RSI
        print("Test 2: Calculate RSI for AAPL")
        result = await plugin.calculate_rsi("AAPL", period=14)
        print(f"Result: {result.get('message')}\n")
        
        # Test 3: Detect crossover
        print("Test 3: Detect MA crossover for AAPL")
        result = await plugin.detect_crossover("AAPL", short_period=10, long_period=20)
        print(f"Result: {result.get('message')}\n")
        
        # Test 4: Support/Resistance
        print("Test 4: Identify support/resistance for AAPL")
        result = await plugin.get_support_resistance("AAPL", days=30)
        print(f"Result: {result.get('message')}\n")
        
        # Test 5: Volatility
        print("Test 5: Calculate volatility for AAPL")
        result = await plugin.get_volatility("AAPL", days=20)
        print(f"Result: {result.get('message')}\n")
        
        print("✅ All tests completed!")
    
    # Run tests
    asyncio.run(test_plugin())
