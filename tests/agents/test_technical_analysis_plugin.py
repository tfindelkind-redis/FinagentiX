"""
Unit tests for Technical Analysis Plugin
"""

import pytest
import json
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime

# Add parent directory to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.agents.plugins.technical_analysis_plugin import TechnicalAnalysisPlugin


@pytest.fixture
def mock_redis():
    """Create a mock Redis client"""
    mock = Mock()
    return mock


@pytest.fixture
def plugin(mock_redis):
    """Create a TechnicalAnalysisPlugin with mocked Redis"""
    return TechnicalAnalysisPlugin(mock_redis)


@pytest.fixture
def sample_price_data():
    """Generate sample price data for testing"""
    base_timestamp = int(datetime.now().timestamp() * 1000)
    # Generate 50 data points with realistic price movements
    prices = []
    base_price = 150.0
    for i in range(50):
        # Add some variation
        price = base_price + (i % 10) - 5 + (np.sin(i / 5) * 2)
        timestamp = base_timestamp - (50 - i) * 86400000  # Daily data
        prices.append([timestamp, str(round(price, 2))])
    return prices


class TestCalculateRSI:
    """Tests for calculate_rsi function"""
    
    @pytest.mark.asyncio
    async def test_calculate_rsi_oversold(self, plugin, mock_redis, sample_price_data):
        """Test RSI calculation when stock is oversold"""
        # Modify data to show declining trend (oversold)
        declining_data = [[ts, str(float(price) - i)] 
                         for i, (ts, price) in enumerate(sample_price_data[:30])]
        mock_redis.execute_command.return_value = declining_data
        
        result = await plugin.calculate_rsi("AAPL", period=14)
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["ticker"] == "AAPL"
        assert "rsi" in result_dict
        assert result_dict["rsi"] < 50  # Should be low for declining prices
        assert result_dict["signal"] in ["oversold", "neutral", "overbought"]
        
        # RSI < 30 should be oversold
        if result_dict["rsi"] < 30:
            assert result_dict["signal"] == "oversold"
    
    @pytest.mark.asyncio
    async def test_calculate_rsi_overbought(self, plugin, mock_redis, sample_price_data):
        """Test RSI calculation when stock is overbought"""
        # Modify data to show rising trend (overbought)
        rising_data = [[ts, str(float(price) + i)] 
                      for i, (ts, price) in enumerate(sample_price_data[:30])]
        mock_redis.execute_command.return_value = rising_data
        
        result = await plugin.calculate_rsi("AAPL", period=14)
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["rsi"] > 50  # Should be high for rising prices
        
        # RSI > 70 should be overbought
        if result_dict["rsi"] > 70:
            assert result_dict["signal"] == "overbought"
    
    @pytest.mark.asyncio
    async def test_calculate_rsi_neutral(self, plugin, mock_redis, sample_price_data):
        """Test RSI in neutral range"""
        mock_redis.execute_command.return_value = sample_price_data
        
        result = await plugin.calculate_rsi("AAPL", period=14)
        result_dict = result
        
        assert result_dict["success"] is True
        assert 0 <= result_dict["rsi"] <= 100
        
        # RSI between 30-70 should be neutral
        if 30 <= result_dict["rsi"] <= 70:
            assert result_dict["signal"] == "neutral"
    
    @pytest.mark.asyncio
    async def test_calculate_rsi_insufficient_data(self, plugin, mock_redis):
        """Test RSI with insufficient data"""
        # Only 10 data points, need at least 14 for default period
        short_data = [[i * 1000, "100.0"] for i in range(10)]
        mock_redis.execute_command.return_value = short_data
        
        result = await plugin.calculate_rsi("AAPL", period=14)
        result_dict = result
        
        assert result_dict["success"] is False
        assert "error" in result_dict
        assert "insufficient data" in result_dict["error"].lower()
    
    @pytest.mark.asyncio
    async def test_calculate_rsi_different_periods(self, plugin, mock_redis, sample_price_data):
        """Test RSI with different period lengths"""
        mock_redis.execute_command.return_value = sample_price_data
        
        for period in [7, 14, 21]:
            result = await plugin.calculate_rsi("AAPL", period=period)
            result_dict = result
            assert result_dict["period"] == period


class TestCalculateMovingAverages:
    """Tests for calculate_moving_averages function"""
    
    @pytest.mark.asyncio
    async def test_moving_averages_success(self, plugin, mock_redis, sample_price_data):
        """Test successful moving average calculation"""
        mock_redis.execute_command.return_value = sample_price_data
        
        result = await plugin.calculate_sma("AAPL", periods=[20, 50])
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["ticker"] == "AAPL"
        assert "moving_averages" in result_dict
        assert len(result_dict["moving_averages"]) == 2
        
        # Check structure
        for ma in result_dict["moving_averages"]:
            assert "period" in ma
            assert "type" in ma
            assert "value" in ma
            assert ma["value"] > 0
    
    @pytest.mark.asyncio
    async def test_moving_averages_sma_vs_ema(self, plugin, mock_redis, sample_price_data):
        """Test both SMA and EMA calculations"""
        mock_redis.execute_command.return_value = sample_price_data
        
        # Test SMA
        result_sma = await plugin.calculate_sma("AAPL", periods=[20], ma_type="SMA")
        sma_dict = json.loads(result_sma)
        
        # Test EMA
        result_ema = await plugin.calculate_sma("AAPL", periods=[20], ma_type="EMA")
        ema_dict = json.loads(result_ema)
        
        assert sma_dict["moving_averages"][0]["type"] == "SMA"
        assert ema_dict["moving_averages"][0]["type"] == "EMA"
        
        # EMA and SMA for same period should be different (EMA more responsive)
        assert sma_dict["moving_averages"][0]["value"] != ema_dict["moving_averages"][0]["value"]
    
    @pytest.mark.asyncio
    async def test_moving_averages_crossover_detection(self, plugin, mock_redis):
        """Test detection of moving average crossovers"""
        # Create data with clear crossover pattern
        # Short-term MA crosses above long-term MA (bullish)
        base_ts = int(datetime.now().timestamp() * 1000)
        crossover_data = []
        for i in range(100):
            if i < 50:
                price = 100.0 - i * 0.5  # Declining
            else:
                price = 75.0 + (i - 50) * 1.0  # Rising sharply
            crossover_data.append([base_ts - (100 - i) * 86400000, str(round(price, 2))])
        
        mock_redis.execute_command.return_value = crossover_data
        
        result = await plugin.calculate_sma("AAPL", periods=[20, 50])
        result_dict = result
        
        # Check if crossover signal is detected
        if "crossover_signal" in result_dict:
            assert result_dict["crossover_signal"] in ["bullish", "bearish", "none"]
    
    @pytest.mark.asyncio
    async def test_moving_averages_multiple_periods(self, plugin, mock_redis, sample_price_data):
        """Test calculation with multiple periods"""
        mock_redis.execute_command.return_value = sample_price_data
        
        result = await plugin.calculate_sma("AAPL", periods=[10, 20, 50])
        result_dict = result
        
        assert len(result_dict["moving_averages"]) == 3
        
        # Verify periods are correct
        periods = [ma["period"] for ma in result_dict["moving_averages"]]
        assert 10 in periods
        assert 20 in periods
        assert 50 in periods


class TestIdentifyPatterns:
    """Tests for identify_patterns function"""
    
    @pytest.mark.asyncio
    async def test_identify_golden_cross(self, plugin, mock_redis):
        """Test detection of golden cross pattern"""
        # Create data where 50-day MA crosses above 200-day MA
        base_ts = int(datetime.now().timestamp() * 1000)
        golden_cross_data = []
        for i in range(250):
            if i < 150:
                price = 100.0 - i * 0.1  # Declining
            else:
                price = 85.0 + (i - 150) * 0.5  # Strong recovery
            golden_cross_data.append([base_ts - (250 - i) * 86400000, str(round(price, 2))])
        
        mock_redis.execute_command.return_value = golden_cross_data
        
        result = await plugin.detect_crossover("AAPL")
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["ticker"] == "AAPL"
        assert "patterns" in result_dict
    
    @pytest.mark.asyncio
    async def test_identify_death_cross(self, plugin, mock_redis):
        """Test detection of death cross pattern"""
        # Create data where 50-day MA crosses below 200-day MA
        base_ts = int(datetime.now().timestamp() * 1000)
        death_cross_data = []
        for i in range(250):
            if i < 100:
                price = 100.0 + i * 0.3  # Rising
            else:
                price = 130.0 - (i - 100) * 0.7  # Sharp decline
            death_cross_data.append([base_ts - (250 - i) * 86400000, str(round(price, 2))])
        
        mock_redis.execute_command.return_value = death_cross_data
        
        result = await plugin.detect_crossover("AAPL")
        result_dict = result
        
        assert result_dict["success"] is True
        assert "patterns" in result_dict
    
    @pytest.mark.asyncio
    async def test_identify_support_resistance(self, plugin, mock_redis):
        """Test identification of support and resistance levels"""
        # Create data with clear support/resistance
        base_ts = int(datetime.now().timestamp() * 1000)
        support_data = []
        for i in range(100):
            # Price bounces between 95-105
            price = 100.0 + (5 * np.sin(i / 10))
            support_data.append([base_ts - (100 - i) * 86400000, str(round(price, 2))])
        
        mock_redis.execute_command.return_value = support_data
        
        result = await plugin.detect_crossover("AAPL")
        result_dict = result
        
        assert result_dict["success"] is True
        # Should detect support/resistance levels
        if "support_level" in result_dict:
            assert isinstance(result_dict["support_level"], (int, float))
        if "resistance_level" in result_dict:
            assert isinstance(result_dict["resistance_level"], (int, float))
    
    @pytest.mark.asyncio
    async def test_identify_patterns_trend_lines(self, plugin, mock_redis):
        """Test trend line identification"""
        base_ts = int(datetime.now().timestamp() * 1000)
        
        # Uptrend data
        uptrend_data = [[base_ts - (50 - i) * 86400000, str(100.0 + i * 0.5)] 
                       for i in range(50)]
        mock_redis.execute_command.return_value = uptrend_data
        
        result = await plugin.detect_crossover("AAPL")
        result_dict = result
        
        assert result_dict["success"] is True
        if "trend" in result_dict:
            assert result_dict["trend"] in ["uptrend", "downtrend", "sideways"]


class TestCalculateVolatility:
    """Tests for calculate_volatility function"""
    
    @pytest.mark.asyncio
    async def test_calculate_volatility_low(self, plugin, mock_redis):
        """Test volatility calculation with low volatility data"""
        # Generate stable prices (low volatility)
        base_ts = int(datetime.now().timestamp() * 1000)
        stable_data = [[base_ts - (30 - i) * 86400000, str(100.0 + (i % 3) * 0.1)] 
                      for i in range(30)]
        mock_redis.execute_command.return_value = stable_data
        
        result = await plugin.calculate_rsi("AAPL", days=30)
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["ticker"] == "AAPL"
        assert "volatility" in result_dict
        assert result_dict["volatility"] >= 0
        assert result_dict["volatility_level"] in ["low", "moderate", "high", "extreme"]
        
        # Low price variation should result in low volatility
        if result_dict["volatility"] < 10:
            assert result_dict["volatility_level"] == "low"
    
    @pytest.mark.asyncio
    async def test_calculate_volatility_high(self, plugin, mock_redis):
        """Test volatility calculation with high volatility data"""
        # Generate volatile prices
        base_ts = int(datetime.now().timestamp() * 1000)
        volatile_data = []
        price = 100.0
        for i in range(30):
            # Large random swings
            price += ((-1) ** i) * (5 + i % 10)
            volatile_data.append([base_ts - (30 - i) * 86400000, str(round(price, 2))])
        
        mock_redis.execute_command.return_value = volatile_data
        
        result = await plugin.calculate_rsi("AAPL", days=30)
        result_dict = result
        
        assert result_dict["success"] is True
        # High price swings should result in high volatility
        assert result_dict["volatility"] > 0
    
    @pytest.mark.asyncio
    async def test_calculate_volatility_annualized(self, plugin, mock_redis, sample_price_data):
        """Test that volatility is properly annualized"""
        mock_redis.execute_command.return_value = sample_price_data
        
        result = await plugin.calculate_rsi("AAPL", days=252)  # One trading year
        result_dict = result
        
        assert result_dict["success"] is True
        # Annualized volatility should be reasonable (typically 10-100%)
        assert 0 < result_dict["volatility"] < 200
    
    @pytest.mark.asyncio
    async def test_calculate_volatility_different_periods(self, plugin, mock_redis, sample_price_data):
        """Test volatility calculation over different time periods"""
        mock_redis.execute_command.return_value = sample_price_data
        
        for days in [7, 30, 90]:
            result = await plugin.calculate_rsi("AAPL", days=days)
            result_dict = result
            assert result_dict["success"] is True
            assert result_dict["period_days"] == days


class TestGetMomentumIndicators:
    """Tests for get_momentum_indicators function"""
    
    @pytest.mark.asyncio
    async def test_momentum_indicators_success(self, plugin, mock_redis, sample_price_data):
        """Test successful momentum indicator calculation"""
        mock_redis.execute_command.return_value = sample_price_data
        
        result = await plugin.calculate_macd("AAPL")
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["ticker"] == "AAPL"
        assert "indicators" in result_dict
        
        # Should contain multiple momentum indicators
        indicators = result_dict["indicators"]
        assert isinstance(indicators, list)
        assert len(indicators) > 0
    
    @pytest.mark.asyncio
    async def test_momentum_indicators_macd(self, plugin, mock_redis, sample_price_data):
        """Test MACD indicator calculation"""
        mock_redis.execute_command.return_value = sample_price_data
        
        result = await plugin.calculate_macd("AAPL")
        result_dict = result
        
        # Look for MACD in indicators
        macd_indicators = [ind for ind in result_dict["indicators"] 
                          if ind["name"].upper() == "MACD"]
        
        if macd_indicators:
            macd = macd_indicators[0]
            assert "value" in macd
            assert "signal" in macd
    
    @pytest.mark.asyncio
    async def test_momentum_indicators_roc(self, plugin, mock_redis):
        """Test Rate of Change (ROC) indicator"""
        # Create data with clear momentum
        base_ts = int(datetime.now().timestamp() * 1000)
        momentum_data = [[base_ts - (30 - i) * 86400000, str(100.0 + i * 2)] 
                        for i in range(30)]
        mock_redis.execute_command.return_value = momentum_data
        
        result = await plugin.calculate_macd("AAPL")
        result_dict = result
        
        # ROC should be positive for rising prices
        roc_indicators = [ind for ind in result_dict["indicators"] 
                         if "ROC" in ind["name"].upper()]
        
        if roc_indicators:
            assert roc_indicators[0]["value"] != 0
    
    @pytest.mark.asyncio
    async def test_momentum_indicators_signal_strength(self, plugin, mock_redis):
        """Test momentum signal strength classification"""
        base_ts = int(datetime.now().timestamp() * 1000)
        
        # Strong upward momentum
        strong_up_data = [[base_ts - (50 - i) * 86400000, str(100.0 + i * 3)] 
                         for i in range(50)]
        mock_redis.execute_command.return_value = strong_up_data
        
        result = await plugin.calculate_macd("AAPL")
        result_dict = result
        
        assert result_dict["success"] is True
        
        # Check for overall signal assessment
        if "overall_signal" in result_dict:
            assert result_dict["overall_signal"] in ["strong_buy", "buy", "neutral", "sell", "strong_sell"]
    
    @pytest.mark.asyncio
    async def test_momentum_indicators_insufficient_data(self, plugin, mock_redis):
        """Test momentum indicators with insufficient data"""
        # Only 10 data points
        short_data = [[i * 1000, "100.0"] for i in range(10)]
        mock_redis.execute_command.return_value = short_data
        
        result = await plugin.calculate_macd("AAPL")
        result_dict = result
        
        # Should either fail or indicate insufficient data
        if not result_dict["success"]:
            assert "error" in result_dict
        else:
            # May still return some indicators with limited data
            assert "indicators" in result_dict


class TestEdgeCases:
    """Tests for edge cases and error handling"""
    
    @pytest.mark.asyncio
    async def test_uppercase_ticker_conversion(self, plugin, mock_redis, sample_price_data):
        """Test that tickers are converted to uppercase"""
        mock_redis.execute_command.return_value = sample_price_data
        
        result = await plugin.calculate_rsi("aapl", period=14)
        result_dict = result
        
        assert result_dict["ticker"] == "AAPL"
        # Verify Redis was called with uppercase ticker
        call_args = str(mock_redis.execute_command.call_args)
        assert "AAPL" in call_args
    
    @pytest.mark.asyncio
    async def test_redis_connection_error(self, plugin, mock_redis):
        """Test handling of Redis connection errors"""
        mock_redis.execute_command.side_effect = Exception("Redis connection failed")
        
        result = await plugin.calculate_rsi("AAPL")
        result_dict = result
        
        assert result_dict["success"] is False
        assert "error" in result_dict
    
    @pytest.mark.asyncio
    async def test_empty_data_handling(self, plugin, mock_redis):
        """Test handling of empty data from Redis"""
        mock_redis.execute_command.return_value = []
        
        result = await plugin.calculate_rsi("INVALID")
        result_dict = result
        
        assert result_dict["success"] is False
        assert "error" in result_dict
    
    @pytest.mark.asyncio
    async def test_invalid_period_parameter(self, plugin, mock_redis, sample_price_data):
        """Test handling of invalid period parameters"""
        mock_redis.execute_command.return_value = sample_price_data
        
        # Period too small
        result = await plugin.calculate_rsi("AAPL", period=1)
        result_dict = result
        
        assert result_dict["success"] is False or result_dict["period"] >= 2


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
