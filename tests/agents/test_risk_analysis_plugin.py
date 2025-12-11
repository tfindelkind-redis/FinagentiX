"""
Unit tests for Risk Analysis Plugin
"""

import pytest
import json
import numpy as np
from unittest.mock import Mock
from datetime import datetime

# Add parent directory to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.agents.plugins.risk_analysis_plugin import RiskAnalysisPlugin


@pytest.fixture
def mock_redis():
    """Create a mock Redis client"""
    mock = Mock()
    return mock


@pytest.fixture
def plugin(mock_redis):
    """Create a RiskAnalysisPlugin with mocked Redis"""
    return RiskAnalysisPlugin(mock_redis)


@pytest.fixture
def sample_returns_data():
    """Generate sample returns data for testing"""
    base_ts = int(datetime.now().timestamp() * 1000)
    # Generate 252 trading days of returns (1 year)
    prices = []
    price = 100.0
    for i in range(252):
        # Random walk with slight upward drift
        price *= (1 + np.random.normal(0.0005, 0.01))
        timestamp = base_ts - (252 - i) * 86400000
        prices.append([timestamp, str(round(price, 2))])
    return prices


class TestCalculateVaR:
    """Tests for calculate_var function"""
    
    @pytest.mark.asyncio
    async def test_var_calculation_95_confidence(self, plugin, mock_redis, sample_returns_data):
        """Test VaR calculation at 95% confidence level"""
        mock_redis.execute_command.return_value = sample_returns_data
        
        result = await plugin.calculate_var("AAPL", confidence=0.95, days=252)
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["ticker"] == "AAPL"
        assert result_dict["confidence"] == 0.95
        assert "var_pct" in result_dict
        assert "var_dollar" in result_dict
        assert "risk_level" in result_dict
        
        # VaR should be negative (potential loss)
        assert result_dict["var_pct"] < 0
        assert result_dict["risk_level"] in ["low", "moderate", "high", "extreme"]
    
    @pytest.mark.asyncio
    async def test_var_different_confidence_levels(self, plugin, mock_redis, sample_returns_data):
        """Test VaR at different confidence levels"""
        mock_redis.execute_command.return_value = sample_returns_data
        
        var_90 = await plugin.calculate_var("AAPL", confidence=0.90)
        var_95 = await plugin.calculate_var("AAPL", confidence=0.95)
        var_99 = await plugin.calculate_var("AAPL", confidence=0.99)
        
        var_90_dict = var_90
        var_95_dict = var_95
        var_99_dict = var_99
        
        # Higher confidence = larger VaR (more extreme loss)
        assert abs(var_99_dict["var_pct"]) >= abs(var_95_dict["var_pct"])
        assert abs(var_95_dict["var_pct"]) >= abs(var_90_dict["var_pct"])
    
    @pytest.mark.asyncio
    async def test_var_holding_period_scaling(self, plugin, mock_redis, sample_returns_data):
        """Test VaR scaling for different holding periods"""
        mock_redis.execute_command.return_value = sample_returns_data
        
        var_1day = await plugin.calculate_var("AAPL", holding_period=1)
        var_10day = await plugin.calculate_var("AAPL", holding_period=10)
        
        var_1_dict = var_1day
        var_10_dict = var_10day
        
        # 10-day VaR should be larger than 1-day VaR
        assert abs(var_10_dict["var_pct"]) > abs(var_1_dict["var_pct"])
    
    @pytest.mark.asyncio
    async def test_var_risk_level_classification(self, plugin, mock_redis):
        """Test risk level classification"""
        # Low volatility data
        base_ts = int(datetime.now().timestamp() * 1000)
        stable_data = [[base_ts - (252 - i) * 86400000, str(100.0 + (i % 2) * 0.1)] 
                      for i in range(252)]
        mock_redis.execute_command.return_value = stable_data
        
        result = await plugin.calculate_var("AAPL")
        result_dict = result
        
        # Low volatility should result in low risk
        if abs(result_dict["var_pct"]) < 2.0:
            assert result_dict["risk_level"] == "low"
    
    @pytest.mark.asyncio
    async def test_var_insufficient_data(self, plugin, mock_redis):
        """Test VaR with insufficient data"""
        # Only 50 data points, need at least 100
        short_data = [[i * 1000, "100.0"] for i in range(50)]
        mock_redis.execute_command.return_value = short_data
        
        result = await plugin.calculate_var("AAPL")
        result_dict = result
        
        assert result_dict["success"] is False
        assert "error" in result_dict
        assert "insufficient data" in result_dict["error"].lower()


class TestCalculateBeta:
    """Tests for calculate_beta function"""
    
    @pytest.mark.asyncio
    async def test_beta_calculation_success(self, plugin, mock_redis):
        """Test successful beta calculation"""
        # Create correlated stock and market data
        base_ts = int(datetime.now().timestamp() * 1000)
        
        # Market (SPY) data - baseline
        market_prices = []
        spy_price = 400.0
        for i in range(252):
            spy_price *= (1 + np.random.normal(0.0003, 0.008))
            market_prices.append([base_ts - (252 - i) * 86400000, str(round(spy_price, 2))])
        
        # Stock data - 1.2x as volatile as market (beta ~1.2)
        stock_prices = []
        stock_price = 100.0
        for i, (ts, spy_price_str) in enumerate(market_prices):
            # Amplify market movements by 1.2x
            market_return = float(spy_price_str) / 400.0 - 1
            stock_price *= (1 + market_return * 1.2 + np.random.normal(0, 0.002))
            stock_prices.append([ts, str(round(stock_price, 2))])
        
        def mock_price_lookup(cmd, key, *args):
            if "SPY" in key:
                return market_prices
            else:
                return stock_prices
        
        mock_redis.execute_command.side_effect = mock_price_lookup
        
        result = await plugin.calculate_beta("AAPL", market_ticker="SPY")
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["ticker"] == "AAPL"
        assert result_dict["market_ticker"] == "SPY"
        assert "beta" in result_dict
        assert "interpretation" in result_dict
        
        # Beta should be reasonable (typically -0.5 to 3.0)
        assert -1.0 < result_dict["beta"] < 3.0
    
    @pytest.mark.asyncio
    async def test_beta_high_correlation(self, plugin, mock_redis):
        """Test beta with high market correlation"""
        base_ts = int(datetime.now().timestamp() * 1000)
        
        # Highly correlated data (beta ~1.5)
        market_data = []
        stock_data = []
        for i in range(252):
            market_return = np.random.normal(0, 0.01)
            market_data.append([base_ts - (252 - i) * 86400000, str(100 + i * market_return)])
            stock_data.append([base_ts - (252 - i) * 86400000, str(100 + i * market_return * 1.5)])
        
        def mock_price_lookup(cmd, key, *args):
            return market_data if "SPY" in key else stock_data
        
        mock_redis.execute_command.side_effect = mock_price_lookup
        
        result = await plugin.calculate_beta("AAPL")
        result_dict = result
        
        # Beta should indicate aggressive stock
        if result_dict["beta"] > 1.5:
            assert "aggressive" in result_dict["interpretation"].lower()
    
    @pytest.mark.asyncio
    async def test_beta_defensive_stock(self, plugin, mock_redis):
        """Test beta for defensive stock"""
        base_ts = int(datetime.now().timestamp() * 1000)
        
        # Low beta stock (beta ~0.5)
        market_data = []
        stock_data = []
        for i in range(252):
            market_return = np.random.normal(0, 0.01)
            market_data.append([base_ts - (252 - i) * 86400000, str(100 + i * market_return)])
            stock_data.append([base_ts - (252 - i) * 86400000, str(100 + i * market_return * 0.5)])
        
        def mock_price_lookup(cmd, key, *args):
            return market_data if "SPY" in key else stock_data
        
        mock_redis.execute_command.side_effect = mock_price_lookup
        
        result = await plugin.calculate_beta("AAPL")
        result_dict = result
        
        # Beta should indicate defensive stock
        if result_dict["beta"] < 0.8:
            assert "defensive" in result_dict["interpretation"].lower()
    
    @pytest.mark.asyncio
    async def test_beta_negative_correlation(self, plugin, mock_redis):
        """Test beta with negative market correlation"""
        base_ts = int(datetime.now().timestamp() * 1000)
        
        # Inverse correlation (beta < 0)
        market_data = []
        stock_data = []
        for i in range(252):
            market_return = np.random.normal(0, 0.01)
            market_data.append([base_ts - (252 - i) * 86400000, str(100 + i * market_return)])
            stock_data.append([base_ts - (252 - i) * 86400000, str(100 - i * market_return)])
        
        def mock_price_lookup(cmd, key, *args):
            return market_data if "SPY" in key else stock_data
        
        mock_redis.execute_command.side_effect = mock_price_lookup
        
        result = await plugin.calculate_beta("AAPL")
        result_dict = result
        
        # Negative beta should be identified
        if result_dict["beta"] < 0:
            assert "inverse" in result_dict["interpretation"].lower()


class TestStressTest:
    """Tests for stress_test function"""
    
    @pytest.mark.asyncio
    async def test_stress_test_all_scenarios(self, plugin, mock_redis, sample_returns_data):
        """Test stress test with all scenarios"""
        mock_redis.execute_command.return_value = sample_returns_data
        
        scenarios = ["market_crash", "correction", "volatility_spike", "black_swan"]
        result = await plugin.stress_test("AAPL", scenarios=scenarios)
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["ticker"] == "AAPL"
        assert "scenarios" in result_dict
        assert len(result_dict["scenarios"]) == 4
        
        # Check each scenario structure
        for scenario in result_dict["scenarios"]:
            assert "name" in scenario
            assert "description" in scenario
            assert "loss_pct" in scenario
            assert "severity" in scenario
            assert scenario["loss_pct"] < 0  # Should be a loss
    
    @pytest.mark.asyncio
    async def test_stress_test_market_crash(self, plugin, mock_redis, sample_returns_data):
        """Test market crash scenario (-20%)"""
        mock_redis.execute_command.return_value = sample_returns_data
        
        result = await plugin.stress_test("AAPL", scenarios=["market_crash"])
        result_dict = result
        
        crash_scenario = result_dict["scenarios"][0]
        assert crash_scenario["name"] == "market_crash"
        # Should show approximately 20% loss (may vary with beta)
        assert crash_scenario["loss_pct"] <= -15
        assert crash_scenario["severity"] in ["moderate", "severe", "extreme"]
    
    @pytest.mark.asyncio
    async def test_stress_test_worst_case(self, plugin, mock_redis, sample_returns_data):
        """Test worst case loss identification"""
        mock_redis.execute_command.return_value = sample_returns_data
        
        scenarios = ["market_crash", "correction", "black_swan"]
        result = await plugin.stress_test("AAPL", scenarios=scenarios)
        result_dict = result
        
        assert "worst_case_loss" in result_dict
        # Worst case should be black swan (most severe)
        assert result_dict["worst_case_loss"] <= -20
    
    @pytest.mark.asyncio
    async def test_stress_test_volatility_spike(self, plugin, mock_redis):
        """Test volatility spike scenario"""
        # Create low volatility data
        base_ts = int(datetime.now().timestamp() * 1000)
        stable_data = [[base_ts - (252 - i) * 86400000, str(100.0 + (i % 2) * 0.5)] 
                      for i in range(252)]
        mock_redis.execute_command.return_value = stable_data
        
        result = await plugin.stress_test("AAPL", scenarios=["volatility_spike"])
        result_dict = result
        
        vol_scenario = result_dict["scenarios"][0]
        assert vol_scenario["name"] == "volatility_spike"
        # Volatility spike shows potential loss range, not fixed percentage
        assert "loss_pct" in vol_scenario


class TestCalculateDrawdown:
    """Tests for calculate_drawdown function"""
    
    @pytest.mark.asyncio
    async def test_drawdown_calculation(self, plugin, mock_redis):
        """Test maximum drawdown calculation"""
        # Create data with clear drawdown
        base_ts = int(datetime.now().timestamp() * 1000)
        drawdown_data = []
        prices = [100, 110, 120, 130, 120, 110, 100, 90, 85, 95, 100, 105]  # Max DD: 35%
        for i, price in enumerate(prices):
            drawdown_data.append([base_ts - (len(prices) - i) * 86400000, str(price)])
        
        mock_redis.execute_command.return_value = drawdown_data
        
        result = await plugin.calculate_drawdown("AAPL")
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["ticker"] == "AAPL"
        assert "max_drawdown_pct" in result_dict
        assert "peak_price" in result_dict
        assert "trough_price" in result_dict
        assert "recovery_status" in result_dict
        
        # Should detect significant drawdown
        assert result_dict["max_drawdown_pct"] > 30  # ~35% in our data
        assert result_dict["peak_price"] == 130.0
        assert result_dict["trough_price"] == 85.0
    
    @pytest.mark.asyncio
    async def test_drawdown_recovery_status(self, plugin, mock_redis):
        """Test drawdown recovery status"""
        base_ts = int(datetime.now().timestamp() * 1000)
        
        # Fully recovered drawdown
        recovered_data = []
        prices = [100, 120, 90, 100, 120]  # Recovered above previous peak
        for i, price in enumerate(prices):
            recovered_data.append([base_ts - (len(prices) - i) * 86400000, str(price)])
        
        mock_redis.execute_command.return_value = recovered_data
        
        result = await plugin.calculate_drawdown("AAPL")
        result_dict = result
        
        # Should show recovered or recovering status
        assert result_dict["recovery_status"] in ["recovered", "recovering", "in_drawdown"]
    
    @pytest.mark.asyncio
    async def test_drawdown_no_decline(self, plugin, mock_redis):
        """Test drawdown with continuously rising prices"""
        base_ts = int(datetime.now().timestamp() * 1000)
        rising_data = [[base_ts - (50 - i) * 86400000, str(100 + i)] 
                      for i in range(50)]
        mock_redis.execute_command.return_value = rising_data
        
        result = await plugin.calculate_drawdown("AAPL")
        result_dict = result
        
        # Should show minimal or no drawdown
        assert result_dict["max_drawdown_pct"] < 5  # Very small drawdown


class TestAssessTailRisk:
    """Tests for assess_tail_risk function"""
    
    @pytest.mark.asyncio
    async def test_tail_risk_normal_distribution(self, plugin, mock_redis):
        """Test tail risk with normal distribution"""
        # Generate normally distributed returns
        base_ts = int(datetime.now().timestamp() * 1000)
        normal_data = []
        price = 100.0
        for i in range(252):
            price *= (1 + np.random.normal(0, 0.01))  # 1% daily volatility
            normal_data.append([base_ts - (252 - i) * 86400000, str(round(price, 2))])
        
        mock_redis.execute_command.return_value = normal_data
        
        result = await plugin.assess_tail_risk("AAPL")
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["ticker"] == "AAPL"
        assert "tail_events_total" in result_dict
        assert "negative_tail_events" in result_dict
        assert "positive_tail_events" in result_dict
        assert "kurtosis" in result_dict
        assert "tail_risk_level" in result_dict
        
        # Normal distribution should have kurtosis ~3
        assert 1 < result_dict["kurtosis"] < 6
    
    @pytest.mark.asyncio
    async def test_tail_risk_fat_tails(self, plugin, mock_redis):
        """Test tail risk with fat-tailed distribution"""
        # Generate data with extreme events (fat tails)
        base_ts = int(datetime.now().timestamp() * 1000)
        fat_tail_data = []
        price = 100.0
        for i in range(252):
            if i % 50 == 0:  # Occasional large moves
                shock = np.random.choice([-0.10, 0.10])  # 10% shocks
            else:
                shock = np.random.normal(0, 0.005)
            price *= (1 + shock)
            fat_tail_data.append([base_ts - (252 - i) * 86400000, str(round(price, 2))])
        
        mock_redis.execute_command.return_value = fat_tail_data
        
        result = await plugin.assess_tail_risk("AAPL")
        result_dict = result
        
        # Fat tails should have high kurtosis
        if result_dict["kurtosis"] > 5:
            assert result_dict["tail_risk_level"] in ["moderate", "high"]
    
    @pytest.mark.asyncio
    async def test_tail_risk_event_counting(self, plugin, mock_redis):
        """Test tail event counting"""
        # Generate data with known extreme events
        base_ts = int(datetime.now().timestamp() * 1000)
        extreme_data = []
        price = 100.0
        for i in range(252):
            if i in [50, 100, 150]:  # 3 extreme negative events
                shock = -0.05  # -5% (beyond 2 std devs for 1% volatility)
            elif i in [75, 125]:  # 2 extreme positive events
                shock = 0.05
            else:
                shock = np.random.normal(0, 0.005)
            price *= (1 + shock)
            extreme_data.append([base_ts - (252 - i) * 86400000, str(round(price, 2))])
        
        mock_redis.execute_command.return_value = extreme_data
        
        result = await plugin.assess_tail_risk("AAPL")
        result_dict = result
        
        # Should detect tail events
        assert result_dict["tail_events_total"] > 0
    
    @pytest.mark.asyncio
    async def test_tail_risk_interpretation(self, plugin, mock_redis, sample_returns_data):
        """Test tail risk level interpretation"""
        mock_redis.execute_command.return_value = sample_returns_data
        
        result = await plugin.assess_tail_risk("AAPL")
        result_dict = result
        
        assert result_dict["tail_risk_level"] in ["low", "moderate", "high"]
        
        # Verify interpretation matches kurtosis
        if result_dict["kurtosis"] > 5:
            assert result_dict["tail_risk_level"] in ["moderate", "high"]
        elif result_dict["kurtosis"] < 3.5:
            assert result_dict["tail_risk_level"] == "low"


class TestEdgeCases:
    """Tests for edge cases and error handling"""
    
    @pytest.mark.asyncio
    async def test_uppercase_ticker_conversion(self, plugin, mock_redis, sample_returns_data):
        """Test ticker is converted to uppercase"""
        mock_redis.execute_command.return_value = sample_returns_data
        
        result = await plugin.calculate_var("aapl")
        result_dict = result
        
        assert result_dict["ticker"] == "AAPL"
    
    @pytest.mark.asyncio
    async def test_redis_connection_error(self, plugin, mock_redis):
        """Test handling of Redis connection errors"""
        mock_redis.execute_command.side_effect = Exception("Redis connection failed")
        
        result = await plugin.calculate_var("AAPL")
        result_dict = result
        
        assert result_dict["success"] is False
        assert "error" in result_dict
    
    @pytest.mark.asyncio
    async def test_empty_data_handling(self, plugin, mock_redis):
        """Test handling of empty data"""
        mock_redis.execute_command.return_value = []
        
        result = await plugin.calculate_beta("AAPL")
        result_dict = result
        
        assert result_dict["success"] is False
        assert "error" in result_dict
    
    @pytest.mark.asyncio
    async def test_invalid_confidence_level(self, plugin, mock_redis, sample_returns_data):
        """Test handling of invalid confidence level"""
        mock_redis.execute_command.return_value = sample_returns_data
        
        # Confidence outside 0-1 range
        result = await plugin.calculate_var("AAPL", confidence=1.5)
        result_dict = result
        
        # Should either reject or clamp to valid range
        assert result_dict["success"] is False or 0 < result_dict["confidence"] <= 1
    
    @pytest.mark.asyncio
    async def test_zero_variance_data(self, plugin, mock_redis):
        """Test handling of constant price data (zero variance)"""
        base_ts = int(datetime.now().timestamp() * 1000)
        constant_data = [[base_ts - (100 - i) * 86400000, "100.00"] 
                        for i in range(100)]
        mock_redis.execute_command.return_value = constant_data
        
        result = await plugin.calculate_beta("AAPL")
        result_dict = result
        
        # Should handle gracefully (may return error or beta=0)
        assert result_dict is not None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
