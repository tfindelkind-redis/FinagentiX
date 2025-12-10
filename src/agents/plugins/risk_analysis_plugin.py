"""
Risk Analysis Plugin for Semantic Kernel
Provides tools for portfolio risk assessment and stress testing
"""

import asyncio
from typing import Dict, Any, List, Optional
import redis
from datetime import datetime, timedelta
import math
from semantic_kernel.functions import kernel_function


class RiskAnalysisPlugin:
    """
    Semantic Kernel plugin for risk analysis operations
    
    Provides tools:
    - calculate_var: Value at Risk calculation
    - calculate_beta: Market correlation (beta)
    - stress_test: Portfolio stress testing
    - calculate_drawdown: Maximum drawdown analysis
    - assess_tail_risk: Extreme event risk assessment
    """
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize Risk Analysis Plugin
        
        Args:
            redis_client: Configured Redis client with TimeSeries
        """
        self.redis = redis_client
    
    @kernel_function(
        name="calculate_var",
        description="Calculate Value at Risk (VaR) for a position or portfolio. Returns VaR estimate and confidence level."
    )
    async def calculate_var(
        self,
        ticker: str,
        confidence: float = 0.95,
        days: int = 252,
        holding_period: int = 1
    ) -> Dict[str, Any]:
        """
        Calculate Value at Risk
        
        Args:
            ticker: Stock ticker symbol
            confidence: Confidence level (default: 0.95 for 95%)
            days: Historical data period
            holding_period: VaR holding period in days
        
        Returns:
            Dictionary with VaR calculation
        """
        try:
            key = f"stock:{ticker.upper()}:close"
            
            # Get historical data
            end_ts = int(datetime.now().timestamp() * 1000)
            start_ts = end_ts - (days * 24 * 60 * 60 * 1000)
            
            result = self.redis.execute_command("TS.RANGE", key, start_ts, end_ts)
            
            if not result or len(result) < days:
                return {
                    "ticker": ticker.upper(),
                    "success": False,
                    "error": f"Insufficient data (need {days} days, got {len(result) if result else 0})"
                }
            
            # Calculate returns
            values = [float(val) for ts, val in result]
            returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
            
            # Sort returns
            sorted_returns = sorted(returns)
            
            # Calculate VaR at confidence level (historical method)
            var_index = int((1 - confidence) * len(sorted_returns))
            var_return = sorted_returns[var_index]
            
            # Scale to holding period
            var_scaled = var_return * math.sqrt(holding_period)
            
            # Convert to percentage
            var_pct = abs(var_scaled) * 100
            
            # Current position value (assume $10,000 for example)
            position_value = 10000
            var_dollar = position_value * abs(var_scaled)
            
            # Risk assessment
            if var_pct > 10:
                risk_level = "extreme"
                assessment = f"Very high risk - potential loss exceeds 10%"
            elif var_pct > 5:
                risk_level = "high"
                assessment = f"High risk - significant potential loss"
            elif var_pct > 2:
                risk_level = "moderate"
                assessment = f"Moderate risk - manageable potential loss"
            else:
                risk_level = "low"
                assessment = f"Low risk - limited potential loss"
            
            return {
                "ticker": ticker.upper(),
                "confidence_level": confidence,
                "holding_period_days": holding_period,
                "var_pct": round(var_pct, 2),
                "var_dollar": round(var_dollar, 2),
                "risk_level": risk_level,
                "assessment": assessment,
                "success": True,
                "message": f"{ticker.upper()} VaR({confidence*100:.0f}%, {holding_period}d): {var_pct:.2f}% (${var_dollar:.2f}) - {risk_level} risk"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "success": False,
                "error": str(e),
                "message": f"Error calculating VaR: {str(e)}"
            }
    
    @kernel_function(
        name="calculate_beta",
        description="Calculate beta (market correlation) for a stock. Returns beta value and correlation strength."
    )
    async def calculate_beta(
        self,
        ticker: str,
        market_ticker: str = "SPY",
        days: int = 252
    ) -> Dict[str, Any]:
        """
        Calculate stock beta vs market
        
        Args:
            ticker: Stock ticker symbol
            market_ticker: Market index ticker (default: SPY)
            days: Historical data period
        
        Returns:
            Dictionary with beta calculation
        """
        try:
            stock_key = f"stock:{ticker.upper()}:close"
            market_key = f"stock:{market_ticker.upper()}:close"
            
            # Get historical data
            end_ts = int(datetime.now().timestamp() * 1000)
            start_ts = end_ts - (days * 24 * 60 * 60 * 1000)
            
            stock_result = self.redis.execute_command("TS.RANGE", stock_key, start_ts, end_ts)
            market_result = self.redis.execute_command("TS.RANGE", market_key, start_ts, end_ts)
            
            if not stock_result or not market_result:
                return {
                    "ticker": ticker.upper(),
                    "success": False,
                    "error": "Insufficient data for beta calculation"
                }
            
            # Calculate returns
            stock_values = [float(val) for ts, val in stock_result]
            market_values = [float(val) for ts, val in market_result]
            
            # Ensure same length
            min_len = min(len(stock_values), len(market_values))
            stock_values = stock_values[:min_len]
            market_values = market_values[:min_len]
            
            stock_returns = [(stock_values[i] - stock_values[i-1]) / stock_values[i-1] 
                           for i in range(1, len(stock_values))]
            market_returns = [(market_values[i] - market_values[i-1]) / market_values[i-1] 
                            for i in range(1, len(market_values))]
            
            # Calculate covariance and variance
            mean_stock = sum(stock_returns) / len(stock_returns)
            mean_market = sum(market_returns) / len(market_returns)
            
            covariance = sum((stock_returns[i] - mean_stock) * (market_returns[i] - mean_market) 
                           for i in range(len(stock_returns))) / len(stock_returns)
            
            market_variance = sum((r - mean_market) ** 2 for r in market_returns) / len(market_returns)
            
            # Calculate beta
            beta = covariance / market_variance if market_variance > 0 else 1.0
            
            # Interpret beta
            if beta > 1.5:
                interpretation = "very aggressive - amplifies market moves significantly"
            elif beta > 1.2:
                interpretation = "aggressive - more volatile than market"
            elif beta > 0.8:
                interpretation = "neutral - moves with market"
            elif beta > 0:
                interpretation = "defensive - less volatile than market"
            else:
                interpretation = "inverse - moves opposite to market"
            
            # Risk assessment based on beta
            if abs(beta - 1) > 0.5:
                risk_note = "High market sensitivity"
            else:
                risk_note = "Moderate market sensitivity"
            
            return {
                "ticker": ticker.upper(),
                "market_ticker": market_ticker.upper(),
                "beta": round(beta, 2),
                "interpretation": interpretation,
                "risk_note": risk_note,
                "success": True,
                "message": f"{ticker.upper()} beta: {beta:.2f} - {interpretation}"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "success": False,
                "error": str(e),
                "message": f"Error calculating beta: {str(e)}"
            }
    
    @kernel_function(
        name="stress_test",
        description="Run stress test scenarios on a position. Returns impact under various market conditions."
    )
    async def stress_test(
        self,
        ticker: str,
        scenarios: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Stress test portfolio position
        
        Args:
            ticker: Stock ticker symbol
            scenarios: List of scenarios (default: market crash, correction, volatility spike)
        
        Returns:
            Dictionary with stress test results
        """
        try:
            if scenarios is None:
                scenarios = ["market_crash", "correction", "volatility_spike"]
            
            # Get current price and volatility
            key = f"stock:{ticker.upper()}:close"
            end_ts = int(datetime.now().timestamp() * 1000)
            start_ts = end_ts - (30 * 24 * 60 * 60 * 1000)
            
            result = self.redis.execute_command("TS.RANGE", key, start_ts, end_ts)
            
            if not result or len(result) < 20:
                return {
                    "ticker": ticker.upper(),
                    "success": False,
                    "error": "Insufficient data for stress test"
                }
            
            values = [float(val) for ts, val in result]
            current_price = values[-1]
            
            # Calculate historical volatility
            returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            volatility = math.sqrt(variance)
            
            # Define stress scenarios
            scenario_definitions = {
                "market_crash": {
                    "name": "Market Crash (-20%)",
                    "shock": -0.20,
                    "description": "Severe market downturn"
                },
                "correction": {
                    "name": "Market Correction (-10%)",
                    "shock": -0.10,
                    "description": "Standard market correction"
                },
                "volatility_spike": {
                    "name": "Volatility Spike (2x)",
                    "shock": volatility * -2,
                    "description": "Extreme volatility event"
                },
                "black_swan": {
                    "name": "Black Swan Event (-30%)",
                    "shock": -0.30,
                    "description": "Extreme tail risk event"
                }
            }
            
            # Calculate impacts
            results = []
            position_value = 10000  # Assume $10k position
            
            for scenario in scenarios:
                if scenario in scenario_definitions:
                    scenario_def = scenario_definitions[scenario]
                    shock = scenario_def["shock"]
                    
                    # Apply shock
                    new_price = current_price * (1 + shock)
                    loss = position_value * shock
                    loss_pct = shock * 100
                    
                    # Severity
                    if abs(loss_pct) > 25:
                        severity = "catastrophic"
                    elif abs(loss_pct) > 15:
                        severity = "severe"
                    elif abs(loss_pct) > 10:
                        severity = "high"
                    else:
                        severity = "moderate"
                    
                    results.append({
                        "scenario": scenario_def["name"],
                        "description": scenario_def["description"],
                        "shock_pct": round(shock * 100, 2),
                        "new_price": round(new_price, 2),
                        "loss_dollar": round(loss, 2),
                        "loss_pct": round(loss_pct, 2),
                        "severity": severity
                    })
            
            # Overall assessment
            max_loss = min(r["loss_pct"] for r in results)
            if max_loss < -20:
                overall_risk = "high"
                recommendation = "Consider hedging or reducing position size"
            elif max_loss < -10:
                overall_risk = "moderate"
                recommendation = "Monitor position closely during volatility"
            else:
                overall_risk = "manageable"
                recommendation = "Standard risk monitoring sufficient"
            
            return {
                "ticker": ticker.upper(),
                "current_price": round(current_price, 2),
                "position_value": position_value,
                "scenarios": results,
                "worst_case_loss": round(max_loss, 2),
                "overall_risk": overall_risk,
                "recommendation": recommendation,
                "success": True,
                "message": f"{ticker.upper()} stress test: worst case {max_loss:.1f}% loss - {overall_risk} risk"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "success": False,
                "error": str(e),
                "message": f"Error in stress test: {str(e)}"
            }
    
    @kernel_function(
        name="calculate_drawdown",
        description="Calculate maximum drawdown for a position. Returns peak-to-trough decline."
    )
    async def calculate_drawdown(
        self,
        ticker: str,
        days: int = 252
    ) -> Dict[str, Any]:
        """
        Calculate maximum drawdown
        
        Args:
            ticker: Stock ticker symbol
            days: Historical period to analyze
        
        Returns:
            Dictionary with drawdown analysis
        """
        try:
            key = f"stock:{ticker.upper()}:close"
            
            # Get historical data
            end_ts = int(datetime.now().timestamp() * 1000)
            start_ts = end_ts - (days * 24 * 60 * 60 * 1000)
            
            result = self.redis.execute_command("TS.RANGE", key, start_ts, end_ts)
            
            if not result or len(result) < 30:
                return {
                    "ticker": ticker.upper(),
                    "success": False,
                    "error": "Insufficient data for drawdown calculation"
                }
            
            # Calculate running maximum and drawdown
            values = [float(val) for ts, val in result]
            timestamps = [ts for ts, val in result]
            
            running_max = values[0]
            max_drawdown = 0
            max_drawdown_pct = 0
            peak_idx = 0
            trough_idx = 0
            
            for i in range(len(values)):
                if values[i] > running_max:
                    running_max = values[i]
                    peak_idx = i
                
                drawdown = running_max - values[i]
                drawdown_pct = (drawdown / running_max) * 100 if running_max > 0 else 0
                
                if drawdown_pct > max_drawdown_pct:
                    max_drawdown_pct = drawdown_pct
                    max_drawdown = drawdown
                    trough_idx = i
            
            # Recovery status
            current_price = values[-1]
            if current_price >= running_max * 0.95:
                recovery_status = "recovered"
                recovery_note = "Position has recovered to near peak"
            elif current_price >= running_max * 0.80:
                recovery_status = "recovering"
                recovery_note = "Position is recovering from drawdown"
            else:
                recovery_status = "in_drawdown"
                recovery_note = "Position still significantly below peak"
            
            # Risk assessment
            if max_drawdown_pct > 40:
                risk_level = "extreme"
                assessment = "Extremely high drawdown risk"
            elif max_drawdown_pct > 25:
                risk_level = "high"
                assessment = "High drawdown risk"
            elif max_drawdown_pct > 15:
                risk_level = "moderate"
                assessment = "Moderate drawdown risk"
            else:
                risk_level = "low"
                assessment = "Low drawdown risk"
            
            # Convert timestamps to dates
            peak_date = datetime.fromtimestamp(timestamps[peak_idx] / 1000).strftime('%Y-%m-%d')
            trough_date = datetime.fromtimestamp(timestamps[trough_idx] / 1000).strftime('%Y-%m-%d')
            
            return {
                "ticker": ticker.upper(),
                "days_analyzed": days,
                "max_drawdown_pct": round(max_drawdown_pct, 2),
                "max_drawdown_dollar": round(max_drawdown, 2),
                "peak_price": round(running_max, 2),
                "trough_price": round(values[trough_idx], 2),
                "current_price": round(current_price, 2),
                "peak_date": peak_date,
                "trough_date": trough_date,
                "recovery_status": recovery_status,
                "recovery_note": recovery_note,
                "risk_level": risk_level,
                "assessment": assessment,
                "success": True,
                "message": f"{ticker.upper()} max drawdown: {max_drawdown_pct:.1f}% - {risk_level} risk, {recovery_status}"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "success": False,
                "error": str(e),
                "message": f"Error calculating drawdown: {str(e)}"
            }
    
    @kernel_function(
        name="assess_tail_risk",
        description="Assess extreme event (tail) risk. Returns tail risk metrics and probability."
    )
    async def assess_tail_risk(
        self,
        ticker: str,
        days: int = 252
    ) -> Dict[str, Any]:
        """
        Assess tail risk (extreme events)
        
        Args:
            ticker: Stock ticker symbol
            days: Historical period to analyze
        
        Returns:
            Dictionary with tail risk assessment
        """
        try:
            key = f"stock:{ticker.upper()}:close"
            
            # Get historical data
            end_ts = int(datetime.now().timestamp() * 1000)
            start_ts = end_ts - (days * 24 * 60 * 60 * 1000)
            
            result = self.redis.execute_command("TS.RANGE", key, start_ts, end_ts)
            
            if not result or len(result) < 100:
                return {
                    "ticker": ticker.upper(),
                    "success": False,
                    "error": "Insufficient data for tail risk assessment"
                }
            
            # Calculate returns
            values = [float(val) for ts, val in result]
            returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
            
            # Calculate statistics
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            std_dev = math.sqrt(variance)
            
            # Identify tail events (beyond 2 standard deviations)
            tail_threshold_negative = mean_return - (2 * std_dev)
            tail_threshold_positive = mean_return + (2 * std_dev)
            
            negative_tail_events = [r for r in returns if r < tail_threshold_negative]
            positive_tail_events = [r for r in returns if r > tail_threshold_positive]
            
            # Calculate tail statistics
            tail_event_count = len(negative_tail_events) + len(positive_tail_events)
            tail_probability = tail_event_count / len(returns)
            
            # Worst tail events
            worst_negative = min(negative_tail_events) if negative_tail_events else 0
            worst_positive = max(positive_tail_events) if positive_tail_events else 0
            
            # Kurtosis approximation (measure of tail heaviness)
            fourth_moment = sum((r - mean_return) ** 4 for r in returns) / len(returns)
            kurtosis = fourth_moment / (variance ** 2) if variance > 0 else 3
            
            # Assess tail risk
            if kurtosis > 5 or len(negative_tail_events) > len(returns) * 0.05:
                tail_risk = "high"
                assessment = "Significant tail risk - frequent extreme events"
            elif kurtosis > 3.5 or len(negative_tail_events) > len(returns) * 0.03:
                tail_risk = "moderate"
                assessment = "Moderate tail risk - some extreme events"
            else:
                tail_risk = "low"
                assessment = "Low tail risk - rare extreme events"
            
            return {
                "ticker": ticker.upper(),
                "days_analyzed": days,
                "tail_events_total": tail_event_count,
                "negative_tail_events": len(negative_tail_events),
                "positive_tail_events": len(positive_tail_events),
                "tail_probability": round(tail_probability * 100, 2),
                "worst_negative_return": round(worst_negative * 100, 2),
                "worst_positive_return": round(worst_positive * 100, 2),
                "kurtosis": round(kurtosis, 2),
                "tail_risk": tail_risk,
                "assessment": assessment,
                "success": True,
                "message": f"{ticker.upper()} tail risk: {tail_risk} - {len(negative_tail_events)} negative tail events ({tail_probability*100:.1f}% probability)"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "success": False,
                "error": str(e),
                "message": f"Error assessing tail risk: {str(e)}"
            }


# Example usage and testing
if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from sk_config import get_redis_client
    
    async def test_plugin():
        """Test the Risk Analysis Plugin"""
        print("Testing Risk Analysis Plugin...\n")
        
        # Get Redis client
        redis_client = get_redis_client()
        
        # Create plugin
        plugin = RiskAnalysisPlugin(redis_client)
        
        # Test 1: Calculate VaR
        print("Test 1: Calculate Value at Risk for AAPL")
        result = await plugin.calculate_var("AAPL", confidence=0.95, days=252)
        print(f"Result: {result.get('message')}\n")
        
        # Test 2: Calculate Beta
        print("Test 2: Calculate beta for AAPL")
        result = await plugin.calculate_beta("AAPL", market_ticker="SPY", days=252)
        print(f"Result: {result.get('message')}\n")
        
        # Test 3: Stress Test
        print("Test 3: Run stress test for AAPL")
        result = await plugin.stress_test("AAPL", scenarios=["market_crash", "correction"])
        print(f"Result: {result.get('message')}\n")
        
        # Test 4: Calculate Drawdown
        print("Test 4: Calculate maximum drawdown for AAPL")
        result = await plugin.calculate_drawdown("AAPL", days=252)
        print(f"Result: {result.get('message')}\n")
        
        # Test 5: Assess Tail Risk
        print("Test 5: Assess tail risk for AAPL")
        result = await plugin.assess_tail_risk("AAPL", days=252)
        print(f"Result: {result.get('message')}\n")
        
        print("✅ All tests completed!")
    
    # Run tests
    asyncio.run(test_plugin())
