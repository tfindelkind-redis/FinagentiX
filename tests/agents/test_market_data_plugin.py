"""
Unit tests for Market Data Plugin
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Add parent directory to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.agents.plugins.market_data_plugin import MarketDataPlugin


@pytest.fixture
def mock_redis():
    """Create a mock Redis client"""
    mock = Mock()
    return mock


@pytest.fixture
def plugin(mock_redis):
    """Create a MarketDataPlugin with mocked Redis"""
    return MarketDataPlugin(mock_redis)


class TestGetStockPrice:
    """Tests for get_stock_price function"""
    
    @pytest.mark.asyncio
    async def test_get_stock_price_success(self, plugin, mock_redis):
        """Test successful stock price retrieval"""
        # Mock Redis response
        timestamp = int(datetime.now().timestamp() * 1000)
        mock_redis.execute_command.return_value = [timestamp, "150.25"]
        
        result = await plugin.get_stock_price("AAPL", "close")
        
        assert result["success"] is True
        assert result["ticker"] == "AAPL"
        assert result["metric"] == "close"
        assert result["value"] == 150.25
        assert "timestamp" in result
        assert "date" in result
        assert "message" in result
        
        # Verify Redis was called correctly
        mock_redis.execute_command.assert_called_once_with("TS.GET", "stock:AAPL:close")
    
    @pytest.mark.asyncio
    async def test_get_stock_price_not_found(self, plugin, mock_redis):
        """Test stock price not found"""
        mock_redis.execute_command.return_value = None
        
        result = await plugin.get_stock_price("INVALID", "close")
        
        assert result["success"] is False
        assert result["ticker"] == "INVALID"
        assert "error" in result
        assert "No data found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_stock_price_uppercase_ticker(self, plugin, mock_redis):
        """Test ticker is converted to uppercase"""
        timestamp = int(datetime.now().timestamp() * 1000)
        mock_redis.execute_command.return_value = [timestamp, "100.50"]
        
        result = await plugin.get_stock_price("aapl", "close")
        
        assert result["ticker"] == "AAPL"
        mock_redis.execute_command.assert_called_once_with("TS.GET", "stock:AAPL:close")
    
    @pytest.mark.asyncio
    async def test_get_stock_price_different_metrics(self, plugin, mock_redis):
        """Test different price metrics"""
        timestamp = int(datetime.now().timestamp() * 1000)
        
        for metric in ["open", "high", "low", "close", "volume"]:
            mock_redis.execute_command.return_value = [timestamp, "100.00"]
            result = await plugin.get_stock_price("AAPL", metric)
            assert result["metric"] == metric
            mock_redis.execute_command.assert_called_with("TS.GET", f"stock:AAPL:{metric}")


class TestGetPriceHistory:
    """Tests for get_price_history function"""
    
    @pytest.mark.asyncio
    async def test_get_price_history_success(self, plugin, mock_redis):
        """Test successful price history retrieval"""
        # Mock historical data (5 data points)
        base_timestamp = int(datetime.now().timestamp() * 1000)
        mock_data = [
            [base_timestamp - 4000, "100.00"],
            [base_timestamp - 3000, "101.00"],
            [base_timestamp - 2000, "99.00"],
            [base_timestamp - 1000, "102.00"],
            [base_timestamp, "103.00"]
        ]
        mock_redis.execute_command.return_value = mock_data
        
        result = await plugin.get_price_history("AAPL", days=5, metric="close")
        
        assert result["success"] is True
        assert result["ticker"] == "AAPL"
        assert result["days"] == 5
        assert len(result["data"]) == 5
        
        # Check statistics
        stats = result["stats"]
        assert stats["count"] == 5
        assert stats["min"] == 99.0
        assert stats["max"] == 103.0
        assert stats["first"] == 100.0
        assert stats["last"] == 103.0
        assert stats["change"] == 3.0
        assert stats["change_pct"] == 3.0
    
    @pytest.mark.asyncio
    async def test_get_price_history_empty(self, plugin, mock_redis):
        """Test empty price history"""
        mock_redis.execute_command.return_value = []
        
        result = await plugin.get_price_history("INVALID", days=30)
        
        assert result["success"] is False
        assert "No historical data found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_price_history_date_formatting(self, plugin, mock_redis):
        """Test date formatting in results"""
        base_timestamp = int(datetime.now().timestamp() * 1000)
        mock_data = [[base_timestamp, "100.00"]]
        mock_redis.execute_command.return_value = mock_data
        
        result = await plugin.get_price_history("AAPL", days=1)
        
        assert len(result["data"]) == 1
        assert "date" in result["data"][0]
        assert "timestamp" in result["data"][0]
        assert "value" in result["data"][0]


class TestGetPriceChange:
    """Tests for get_price_change function"""
    
    @pytest.mark.asyncio
    async def test_get_price_change_uptrend(self, plugin, mock_redis):
        """Test upward price change"""
        base_timestamp = int(datetime.now().timestamp() * 1000)
        mock_data = [
            [base_timestamp - 86400000, "100.00"],
            [base_timestamp, "105.00"]
        ]
        mock_redis.execute_command.return_value = mock_data
        
        result = await plugin.get_price_change("AAPL", days=1)
        
        assert result["success"] is True
        assert result["start_price"] == 100.0
        assert result["end_price"] == 105.0
        assert result["change"] == 5.0
        assert result["change_pct"] == 5.0
        assert result["trend"] == "uptrend"
    
    @pytest.mark.asyncio
    async def test_get_price_change_downtrend(self, plugin, mock_redis):
        """Test downward price change"""
        base_timestamp = int(datetime.now().timestamp() * 1000)
        mock_data = [
            [base_timestamp - 86400000, "100.00"],
            [base_timestamp, "95.00"]
        ]
        mock_redis.execute_command.return_value = mock_data
        
        result = await plugin.get_price_change("AAPL", days=1)
        
        assert result["success"] is True
        assert result["change"] == -5.0
        assert result["change_pct"] == -5.0
        assert result["trend"] == "downtrend"
    
    @pytest.mark.asyncio
    async def test_get_price_change_strong_uptrend(self, plugin, mock_redis):
        """Test strong upward trend (>5%)"""
        base_timestamp = int(datetime.now().timestamp() * 1000)
        mock_data = [
            [base_timestamp - 86400000, "100.00"],
            [base_timestamp, "110.00"]
        ]
        mock_redis.execute_command.return_value = mock_data
        
        result = await plugin.get_price_change("AAPL", days=1)
        
        assert result["change_pct"] == 10.0
        assert result["trend"] == "strong uptrend"
    
    @pytest.mark.asyncio
    async def test_get_price_change_insufficient_data(self, plugin, mock_redis):
        """Test insufficient data for comparison"""
        mock_redis.execute_command.return_value = [[int(datetime.now().timestamp() * 1000), "100.00"]]
        
        result = await plugin.get_price_change("AAPL", days=1)
        
        assert result["success"] is False
        assert "Insufficient data" in result["error"]


class TestGetMultipleTickers:
    """Tests for get_multiple_tickers function"""
    
    @pytest.mark.asyncio
    async def test_get_multiple_tickers_success(self, plugin, mock_redis):
        """Test multiple ticker retrieval"""
        timestamp = int(datetime.now().timestamp() * 1000)
        mock_redis.execute_command.return_value = [timestamp, "100.00"]
        
        result = await plugin.get_multiple_tickers("AAPL,MSFT,GOOGL")
        
        assert result["success"] is True
        assert result["tickers"] == ["AAPL", "MSFT", "GOOGL"]
        assert result["count"] == 3
        assert result["successful"] == 3
        assert len(result["results"]) == 3
    
    @pytest.mark.asyncio
    async def test_get_multiple_tickers_mixed_results(self, plugin, mock_redis):
        """Test mixed successful and failed tickers"""
        def mock_execute(cmd, key):
            if "AAPL" in key:
                return [int(datetime.now().timestamp() * 1000), "100.00"]
            return None
        
        mock_redis.execute_command.side_effect = mock_execute
        
        result = await plugin.get_multiple_tickers("AAPL,INVALID")
        
        assert result["successful"] == 1
        assert result["failed"] == 1
    
    @pytest.mark.asyncio
    async def test_get_multiple_tickers_whitespace(self, plugin, mock_redis):
        """Test ticker list with whitespace"""
        timestamp = int(datetime.now().timestamp() * 1000)
        mock_redis.execute_command.return_value = [timestamp, "100.00"]
        
        result = await plugin.get_multiple_tickers(" AAPL , MSFT , GOOGL ")
        
        assert result["tickers"] == ["AAPL", "MSFT", "GOOGL"]


class TestGetVolumeAnalysis:
    """Tests for get_volume_analysis function"""
    
    @pytest.mark.asyncio
    async def test_get_volume_analysis_above_average(self, plugin, mock_redis):
        """Test volume above average"""
        base_timestamp = int(datetime.now().timestamp() * 1000)
        # Create 30 days of volume data with last day significantly higher
        mock_data = [[base_timestamp - (i * 86400000), "1000000"] for i in range(29, -1, -1)]
        mock_data[-1][1] = "2000000"  # Last day is 2x average
        mock_redis.execute_command.return_value = mock_data
        
        result = await plugin.get_volume_analysis("AAPL", days=30)
        
        assert result["success"] is True
        assert result["ticker"] == "AAPL"
        assert result["current_volume"] > result["avg_volume"]
        assert result["volume_trend_pct"] > 0
        assert "analysis" in result
    
    @pytest.mark.asyncio
    async def test_get_volume_analysis_below_average(self, plugin, mock_redis):
        """Test volume below average"""
        base_timestamp = int(datetime.now().timestamp() * 1000)
        # Create data with last day lower
        mock_data = [[base_timestamp - (i * 86400000), "1000000"] for i in range(29, -1, -1)]
        mock_data[-1][1] = "500000"  # Last day is 50% of average
        mock_redis.execute_command.return_value = mock_data
        
        result = await plugin.get_volume_analysis("AAPL", days=30)
        
        assert result["success"] is True
        assert result["current_volume"] < result["avg_volume"]
        assert result["volume_trend_pct"] < 0


class TestGetTechnicalIndicators:
    """Tests for get_technical_indicators function"""

    @pytest.mark.asyncio
    async def test_get_technical_indicators_success(self, plugin, monkeypatch):
        """Test successful indicator computation"""

        values = [float(i) for i in range(1, 201)]
        history_response = {
            "success": True,
            "data": [
                {
                    "timestamp": 1_700_000_000_000 + idx,
                    "date": "2024-01-01",
                    "value": value,
                }
                for idx, value in enumerate(values)
            ],
        }

        async def fake_history(ticker, days, metric):
            return history_response

        monkeypatch.setattr(plugin, "get_price_history", fake_history)

        result = await plugin.get_technical_indicators("AAPL")

        assert result["success"] is True
        assert result["trend"] == "bullish"
        assert pytest.approx(result["sma"]["short"], rel=1e-5) == 190.5
        assert pytest.approx(result["sma"]["long"], rel=1e-5) == 175.5
        assert result["bollinger"]["upper"] > result["bollinger"]["lower"]
        assert result["support"] == pytest.approx(171.0)
        assert result["resistance"] == pytest.approx(200.0)
        assert "Trend bullish" in result["message"]

    @pytest.mark.asyncio
    async def test_get_technical_indicators_insufficient_data(self, plugin, monkeypatch):
        """Test insufficient history handling"""

        history_response = {
            "success": True,
            "data": [
                {
                    "timestamp": 1_700_000_000_000,
                    "date": "2024-01-01",
                    "value": 100.0,
                }
            ],
        }

        async def fake_history(ticker, days, metric):
            return history_response

        monkeypatch.setattr(plugin, "get_price_history", fake_history)

        result = await plugin.get_technical_indicators("AAPL")

        assert result["success"] is False
        assert result["error"] == "insufficient_data"

    @pytest.mark.asyncio
    async def test_get_technical_indicators_propagates_failure(self, plugin, monkeypatch):
        """Test that history failure is surfaced"""

        history_response = {
            "success": False,
            "error": "not_found",
            "message": "No data",
        }

        async def fake_history(ticker, days, metric):
            return history_response

        monkeypatch.setattr(plugin, "get_price_history", fake_history)

        result = await plugin.get_technical_indicators("MSFT")

        assert result["success"] is False
        assert result["error"] == "not_found"

class TestErrorHandling:
    """Tests for error handling"""
    
    @pytest.mark.asyncio
    async def test_redis_exception_handling(self, plugin, mock_redis):
        """Test handling of Redis exceptions"""
        mock_redis.execute_command.side_effect = Exception("Redis connection error")
        
        result = await plugin.get_stock_price("AAPL", "close")
        
        assert result["success"] is False
        assert "error" in result
        assert "Redis connection error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_invalid_data_format(self, plugin, mock_redis):
        """Test handling of invalid data format"""
        mock_redis.execute_command.return_value = ["invalid"]  # Wrong format
        
        result = await plugin.get_stock_price("AAPL", "close")
        
        assert result["success"] is False


# Integration test (requires actual Redis)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_with_real_redis():
    """Integration test with real Redis (skipped by default)"""
    import redis
    import os
    
    # Skip if Redis not configured
    redis_host = os.getenv("REDIS_HOST")
    if not redis_host:
        pytest.skip("Redis not configured")
    
    redis_client = redis.Redis(
        host=redis_host,
        port=int(os.getenv("REDIS_PORT", 6379)),
        password=os.getenv("REDIS_PASSWORD"),
        ssl=True,
        decode_responses=True
    )
    
    plugin = MarketDataPlugin(redis_client)
    
    # Test real data retrieval
    result = await plugin.get_stock_price("AAPL", "close")
    
    # Just verify it doesn't crash - actual data depends on what's loaded
    assert "success" in result
    assert "ticker" in result


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
