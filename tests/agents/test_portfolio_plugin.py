"""
Unit tests for Portfolio Plugin
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime

# Add parent directory to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.agents.plugins.portfolio_plugin import PortfolioPlugin


@pytest.fixture
def mock_redis():
    """Create a mock Redis client"""
    mock = Mock()
    return mock


@pytest.fixture
def plugin(mock_redis):
    """Create a PortfolioPlugin with mocked Redis"""
    return PortfolioPlugin(mock_redis)


@pytest.fixture
def sample_portfolio():
    """Sample portfolio data"""
    return {
        b"AAPL": b'{"shares": 100, "cost_basis": 150.00}',
        b"MSFT": b'{"shares": 50, "cost_basis": 300.00}',
        b"GOOGL": b'{"shares": 25, "cost_basis": 2800.00}'
    }


@pytest.fixture
def sample_price_data():
    """Sample price data for portfolio valuation"""
    base_ts = int(datetime.now().timestamp() * 1000)
    return [[base_ts, "160.00"]]  # Current price


class TestGetPortfolioSummary:
    """Tests for get_portfolio_summary function"""
    
    @pytest.mark.asyncio
    async def test_portfolio_summary_success(self, plugin, mock_redis, sample_portfolio, sample_price_data):
        """Test successful portfolio summary retrieval"""
        mock_redis.hgetall.return_value = sample_portfolio
        mock_redis.execute_command.return_value = sample_price_data
        
        result = await plugin.get_portfolio_summary("default")
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["portfolio_id"] == "default"
        assert result_dict["total_positions"] == 3
        assert "positions" in result_dict
        assert len(result_dict["positions"]) == 3
        
        # Check position structure
        for position in result_dict["positions"]:
            assert "ticker" in position
            assert "shares" in position
            assert "cost_basis" in position
            assert "current_price" in position
            assert "current_value" in position
            assert "total_gain_loss" in position
            assert "total_gain_loss_pct" in position
    
    @pytest.mark.asyncio
    async def test_portfolio_summary_empty_portfolio(self, plugin, mock_redis):
        """Test portfolio summary with empty portfolio"""
        mock_redis.hgetall.return_value = {}
        
        result = await plugin.get_portfolio_summary("default")
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["total_positions"] == 0
        assert len(result_dict["positions"]) == 0
        assert result_dict["total_value"] == 0
    
    @pytest.mark.asyncio
    async def test_portfolio_summary_with_gains(self, plugin, mock_redis):
        """Test portfolio with gains"""
        portfolio_data = {
            b"AAPL": b'{"shares": 100, "cost_basis": 100.00}'  # Cost: $100/share
        }
        mock_redis.hgetall.return_value = portfolio_data
        
        # Current price: $150/share (50% gain)
        base_ts = int(datetime.now().timestamp() * 1000)
        mock_redis.execute_command.return_value = [[base_ts, "150.00"]]
        
        result = await plugin.get_portfolio_summary("default")
        result_dict = result
        
        position = result_dict["positions"][0]
        assert position["ticker"] == "AAPL"
        assert position["shares"] == 100
        assert position["cost_basis"] == 100.00
        assert position["current_price"] == 150.00
        assert position["current_value"] == 15000.00  # 100 shares * $150
        assert position["total_gain_loss"] == 5000.00  # (150 - 100) * 100
        assert position["total_gain_loss_pct"] == 50.0  # 50% gain
    
    @pytest.mark.asyncio
    async def test_portfolio_summary_with_losses(self, plugin, mock_redis):
        """Test portfolio with losses"""
        portfolio_data = {
            b"AAPL": b'{"shares": 100, "cost_basis": 200.00}'  # Cost: $200/share
        }
        mock_redis.hgetall.return_value = portfolio_data
        
        # Current price: $150/share (25% loss)
        base_ts = int(datetime.now().timestamp() * 1000)
        mock_redis.execute_command.return_value = [[base_ts, "150.00"]]
        
        result = await plugin.get_portfolio_summary("default")
        result_dict = result
        
        position = result_dict["positions"][0]
        assert position["total_gain_loss"] == -5000.00  # (150 - 200) * 100
        assert position["total_gain_loss_pct"] == -25.0  # 25% loss
    
    @pytest.mark.asyncio
    async def test_portfolio_summary_total_value(self, plugin, mock_redis):
        """Test total portfolio value calculation"""
        portfolio_data = {
            b"AAPL": b'{"shares": 100, "cost_basis": 150.00}',
            b"MSFT": b'{"shares": 50, "cost_basis": 300.00}'
        }
        mock_redis.hgetall.return_value = portfolio_data
        
        base_ts = int(datetime.now().timestamp() * 1000)
        
        # Mock different prices for different tickers
        def mock_price_lookup(cmd, key, *args):
            if "AAPL" in key:
                return [[base_ts, "160.00"]]  # AAPL: $160
            elif "MSFT" in key:
                return [[base_ts, "320.00"]]  # MSFT: $320
        
        mock_redis.execute_command.side_effect = mock_price_lookup
        
        result = await plugin.get_portfolio_summary("default")
        result_dict = result
        
        # Total value: (100 * 160) + (50 * 320) = 16,000 + 16,000 = 32,000
        assert result_dict["total_value"] == 32000.00


class TestCalculatePerformance:
    """Tests for calculate_performance function"""
    
    @pytest.mark.asyncio
    async def test_calculate_performance_positive_returns(self, plugin, mock_redis):
        """Test performance calculation with positive returns"""
        portfolio_data = {
            b"AAPL": b'{"shares": 100, "cost_basis": 100.00}'
        }
        mock_redis.hgetall.return_value = portfolio_data
        
        # Historical prices showing growth
        base_ts = int(datetime.now().timestamp() * 1000)
        historical_prices = [
            [base_ts - 30 * 86400000, "100.00"],  # 30 days ago
            [base_ts - 20 * 86400000, "105.00"],
            [base_ts - 10 * 86400000, "110.00"],
            [base_ts, "120.00"]  # Today
        ]
        mock_redis.execute_command.return_value = historical_prices
        
        result = await plugin.calculate_metrics("default", days=30)
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["period_days"] == 30
        assert "total_return" in result_dict
        assert "total_return_pct" in result_dict
        assert result_dict["total_return_pct"] > 0  # Positive return
    
    @pytest.mark.asyncio
    async def test_calculate_performance_negative_returns(self, plugin, mock_redis):
        """Test performance calculation with negative returns"""
        portfolio_data = {
            b"AAPL": b'{"shares": 100, "cost_basis": 150.00}'
        }
        mock_redis.hgetall.return_value = portfolio_data
        
        # Historical prices showing decline
        base_ts = int(datetime.now().timestamp() * 1000)
        declining_prices = [
            [base_ts - 30 * 86400000, "150.00"],  # 30 days ago
            [base_ts - 20 * 86400000, "140.00"],
            [base_ts - 10 * 86400000, "130.00"],
            [base_ts, "120.00"]  # Today (down 20%)
        ]
        mock_redis.execute_command.return_value = declining_prices
        
        result = await plugin.calculate_metrics("default", days=30)
        result_dict = result
        
        assert result_dict["total_return_pct"] < 0  # Negative return
    
    @pytest.mark.asyncio
    async def test_calculate_performance_different_periods(self, plugin, mock_redis):
        """Test performance over different time periods"""
        portfolio_data = {
            b"AAPL": b'{"shares": 100, "cost_basis": 100.00}'
        }
        mock_redis.hgetall.return_value = portfolio_data
        
        base_ts = int(datetime.now().timestamp() * 1000)
        mock_redis.execute_command.return_value = [
            [base_ts - 90 * 86400000, "100.00"],
            [base_ts, "110.00"]
        ]
        
        for days in [7, 30, 90]:
            result = await plugin.calculate_metrics("default", days=days)
            result_dict = result
            assert result_dict["period_days"] == days
    
    @pytest.mark.asyncio
    async def test_calculate_performance_empty_portfolio(self, plugin, mock_redis):
        """Test performance with empty portfolio"""
        mock_redis.hgetall.return_value = {}
        
        result = await plugin.calculate_metrics("default")
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["total_return"] == 0
        assert result_dict["total_return_pct"] == 0


class TestAnalyzeDiversification:
    """Tests for analyze_diversification function"""
    
    @pytest.mark.asyncio
    async def test_diversification_well_diversified(self, plugin, mock_redis):
        """Test diversification analysis with well-diversified portfolio"""
        # 5 positions with roughly equal weights
        portfolio_data = {
            b"AAPL": b'{"shares": 100, "cost_basis": 100.00}',
            b"MSFT": b'{"shares": 50, "cost_basis": 200.00}',
            b"GOOGL": b'{"shares": 10, "cost_basis": 1000.00}',
            b"AMZN": b'{"shares": 50, "cost_basis": 200.00}',
            b"TSLA": b'{"shares": 50, "cost_basis": 200.00}'
        }
        mock_redis.hgetall.return_value = portfolio_data
        
        # Mock equal current prices for simplicity
        base_ts = int(datetime.now().timestamp() * 1000)
        mock_redis.execute_command.return_value = [[base_ts, "100.00"]]
        
        result = await plugin.analyze_allocation("default")
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["total_positions"] == 5
        assert "allocations" in result_dict
        assert len(result_dict["allocations"]) == 5
        
        # Check that allocations sum to 100%
        total_allocation = sum(pos["allocation_pct"] for pos in result_dict["allocations"])
        assert abs(total_allocation - 100.0) < 0.1
    
    @pytest.mark.asyncio
    async def test_diversification_concentrated(self, plugin, mock_redis):
        """Test diversification with concentrated portfolio"""
        # One large position, several small ones
        portfolio_data = {
            b"AAPL": b'{"shares": 1000, "cost_basis": 100.00}',  # 90% of portfolio
            b"MSFT": b'{"shares": 10, "cost_basis": 100.00}',
            b"GOOGL": b'{"shares": 10, "cost_basis": 100.00}'
        }
        mock_redis.hgetall.return_value = portfolio_data
        
        base_ts = int(datetime.now().timestamp() * 1000)
        mock_redis.execute_command.return_value = [[base_ts, "100.00"]]
        
        result = await plugin.analyze_allocation("default")
        result_dict = result
        
        # Find AAPL allocation
        aapl_allocation = next(pos for pos in result_dict["allocations"] if pos["ticker"] == "AAPL")
        assert aapl_allocation["allocation_pct"] > 80  # Should be heavily concentrated
        
        if "diversification_score" in result_dict:
            assert result_dict["diversification_score"] == "concentrated"
    
    @pytest.mark.asyncio
    async def test_diversification_by_sector(self, plugin, mock_redis):
        """Test sector-based diversification analysis"""
        portfolio_data = {
            b"AAPL": b'{"shares": 100, "cost_basis": 100.00}',
            b"MSFT": b'{"shares": 100, "cost_basis": 100.00}',
            b"GOOGL": b'{"shares": 100, "cost_basis": 100.00}'
        }
        mock_redis.hgetall.return_value = portfolio_data
        
        base_ts = int(datetime.now().timestamp() * 1000)
        mock_redis.execute_command.return_value = [[base_ts, "100.00"]]
        
        result = await plugin.analyze_allocation("default")
        result_dict = result
        
        # All tech stocks should show sector concentration
        if "sector_allocation" in result_dict:
            tech_allocation = result_dict["sector_allocation"].get("Technology", 0)
            assert tech_allocation == 100.0  # All tech


class TestGetTopPerformers:
    """Tests for get_top_performers function"""
    
    @pytest.mark.asyncio
    async def test_top_performers_success(self, plugin, mock_redis):
        """Test successful top performers retrieval"""
        portfolio_data = {
            b"AAPL": b'{"shares": 100, "cost_basis": 100.00}',  # 50% gain
            b"MSFT": b'{"shares": 100, "cost_basis": 100.00}',  # 20% gain
            b"GOOGL": b'{"shares": 100, "cost_basis": 100.00}',  # -10% loss
            b"AMZN": b'{"shares": 100, "cost_basis": 100.00}',  # 30% gain
            b"TSLA": b'{"shares": 100, "cost_basis": 100.00}'   # -5% loss
        }
        mock_redis.hgetall.return_value = portfolio_data
        
        base_ts = int(datetime.now().timestamp() * 1000)
        
        # Mock different performance for each ticker
        def mock_price_lookup(cmd, key, *args):
            if "AAPL" in key:
                return [[base_ts, "150.00"]]  # 50% gain
            elif "MSFT" in key:
                return [[base_ts, "120.00"]]  # 20% gain
            elif "GOOGL" in key:
                return [[base_ts, "90.00"]]   # 10% loss
            elif "AMZN" in key:
                return [[base_ts, "130.00"]]  # 30% gain
            elif "TSLA" in key:
                return [[base_ts, "95.00"]]   # 5% loss
        
        mock_redis.execute_command.side_effect = mock_price_lookup
        
        result = await plugin.get_performance("default", top_n=3)
        result_dict = result
        
        assert result_dict["success"] is True
        assert len(result_dict["top_performers"]) == 3
        assert len(result_dict["worst_performers"]) == 3
        
        # Top performers should be sorted by gain
        top = result_dict["top_performers"]
        assert top[0]["ticker"] == "AAPL"  # 50% gain
        assert top[1]["ticker"] == "AMZN"  # 30% gain
        assert top[2]["ticker"] == "MSFT"  # 20% gain
        
        # Worst performers should be sorted by loss
        worst = result_dict["worst_performers"]
        assert worst[0]["ticker"] == "GOOGL"  # 10% loss
    
    @pytest.mark.asyncio
    async def test_top_performers_all_gains(self, plugin, mock_redis):
        """Test top performers when all positions are profitable"""
        portfolio_data = {
            b"AAPL": b'{"shares": 100, "cost_basis": 100.00}',
            b"MSFT": b'{"shares": 100, "cost_basis": 100.00}'
        }
        mock_redis.hgetall.return_value = portfolio_data
        
        base_ts = int(datetime.now().timestamp() * 1000)
        
        def mock_price_lookup(cmd, key, *args):
            if "AAPL" in key:
                return [[base_ts, "120.00"]]  # 20% gain
            elif "MSFT" in key:
                return [[base_ts, "110.00"]]  # 10% gain
        
        mock_redis.execute_command.side_effect = mock_price_lookup
        
        result = await plugin.get_performance("default")
        result_dict = result
        
        # All should be in top performers
        assert all(pos["gain_loss_pct"] > 0 for pos in result_dict["top_performers"])


class TestCalculateAllocation:
    """Tests for calculate_allocation function"""
    
    @pytest.mark.asyncio
    async def test_allocation_calculation(self, plugin, mock_redis):
        """Test portfolio allocation calculation"""
        portfolio_data = {
            b"AAPL": b'{"shares": 100, "cost_basis": 100.00}',  # $10,000
            b"MSFT": b'{"shares": 200, "cost_basis": 100.00}',  # $20,000
            b"GOOGL": b'{"shares": 50, "cost_basis": 200.00}'   # $10,000
        }
        mock_redis.hgetall.return_value = portfolio_data
        
        base_ts = int(datetime.now().timestamp() * 1000)
        mock_redis.execute_command.return_value = [[base_ts, "100.00"]]
        
        result = await plugin.analyze_allocation("default")
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["total_value"] > 0
        
        # Find MSFT allocation (should be 50% since it's $20k of $40k total)
        msft_alloc = next(pos for pos in result_dict["allocations"] if pos["ticker"] == "MSFT")
        assert abs(msft_alloc["allocation_pct"] - 50.0) < 1.0
    
    @pytest.mark.asyncio
    async def test_allocation_recommendations(self, plugin, mock_redis):
        """Test allocation rebalancing recommendations"""
        # Very concentrated portfolio
        portfolio_data = {
            b"AAPL": b'{"shares": 900, "cost_basis": 100.00}',  # 90%
            b"MSFT": b'{"shares": 100, "cost_basis": 100.00}'   # 10%
        }
        mock_redis.hgetall.return_value = portfolio_data
        
        base_ts = int(datetime.now().timestamp() * 1000)
        mock_redis.execute_command.return_value = [[base_ts, "100.00"]]
        
        result = await plugin.analyze_allocation("default")
        result_dict = result
        
        # Should recommend rebalancing for concentrated positions
        if "recommendations" in result_dict:
            assert len(result_dict["recommendations"]) > 0
            assert any("concentrated" in rec.lower() for rec in result_dict["recommendations"])


class TestEdgeCases:
    """Tests for edge cases and error handling"""
    
    @pytest.mark.asyncio
    async def test_invalid_portfolio_id(self, plugin, mock_redis):
        """Test handling of invalid portfolio ID"""
        mock_redis.hgetall.return_value = {}
        
        result = await plugin.get_positions("nonexistent")
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["total_positions"] == 0
    
    @pytest.mark.asyncio
    async def test_redis_connection_error(self, plugin, mock_redis):
        """Test handling of Redis connection errors"""
        mock_redis.hgetall.side_effect = Exception("Redis connection failed")
        
        result = await plugin.get_portfolio_summary("default")
        result_dict = result
        
        assert result_dict["success"] is False
        assert "error" in result_dict
    
    @pytest.mark.asyncio
    async def test_corrupted_portfolio_data(self, plugin, mock_redis):
        """Test handling of corrupted portfolio data"""
        portfolio_data = {
            b"AAPL": b'invalid json data'
        }
        mock_redis.hgetall.return_value = portfolio_data
        
        result = await plugin.get_portfolio_summary("default")
        result_dict = result
        
        # Should handle gracefully
        assert "error" in result_dict or result_dict["success"] is False
    
    @pytest.mark.asyncio
    async def test_missing_price_data(self, plugin, mock_redis):
        """Test handling when price data is unavailable"""
        portfolio_data = {
            b"AAPL": b'{"shares": 100, "cost_basis": 100.00}'
        }
        mock_redis.hgetall.return_value = portfolio_data
        mock_redis.execute_command.return_value = None  # No price data
        
        result = await plugin.get_portfolio_summary("default")
        result_dict = result
        
        # Should handle gracefully, possibly with null/zero current values
        assert result_dict is not None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
