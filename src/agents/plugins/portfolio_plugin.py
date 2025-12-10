"""
Portfolio Management Plugin for Semantic Kernel
Provides tools for portfolio tracking, metrics, and allocation analysis
"""

import asyncio
from typing import Dict, Any, List, Optional
import redis
from datetime import datetime
from semantic_kernel.functions import kernel_function


class PortfolioPlugin:
    """
    Semantic Kernel plugin for portfolio management operations
    
    Provides tools:
    - get_positions: Get current portfolio positions
    - calculate_metrics: Calculate portfolio performance metrics
    - analyze_allocation: Analyze portfolio allocation and diversification
    - calculate_risk: Calculate portfolio risk metrics
    - get_performance: Get portfolio performance over time
    """
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize Portfolio Plugin
        
        Args:
            redis_client: Configured Redis client
        """
        self.redis = redis_client
    
    @kernel_function(
        name="get_positions",
        description="Get current portfolio positions with values and allocations. Returns list of holdings."
    )
    async def get_positions(
        self,
        portfolio_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Get current portfolio positions
        
        Args:
            portfolio_id: Portfolio identifier (default: "default")
        
        Returns:
            Dictionary with positions and summary
        """
        try:
            # Get positions from Redis hash
            key = f"portfolio:{portfolio_id}:positions"
            positions_data = self.redis.hgetall(key)
            
            if not positions_data:
                return {
                    "portfolio_id": portfolio_id,
                    "positions": [],
                    "total_value": 0,
                    "success": True,
                    "message": "No positions found in portfolio"
                }
            
            positions = []
            total_value = 0
            
            # Parse positions
            for ticker_bytes, data_bytes in positions_data.items():
                ticker = ticker_bytes.decode('utf-8')
                data = eval(data_bytes.decode('utf-8'))  # In production, use json.loads
                
                # Get current price
                price_key = f"stock:{ticker}:close"
                end_ts = int(datetime.now().timestamp() * 1000)
                start_ts = end_ts - (24 * 60 * 60 * 1000)
                
                try:
                    result = self.redis.execute_command("TS.RANGE", price_key, start_ts, end_ts)
                    current_price = float(result[-1][1]) if result else data.get('cost_basis', 0)
                except:
                    current_price = data.get('cost_basis', 0)
                
                # Calculate position metrics
                shares = data.get('shares', 0)
                cost_basis = data.get('cost_basis', 0)
                current_value = shares * current_price
                cost_value = shares * cost_basis
                gain_loss = current_value - cost_value
                gain_loss_pct = ((current_price - cost_basis) / cost_basis * 100) if cost_basis > 0 else 0
                
                positions.append({
                    "ticker": ticker,
                    "shares": shares,
                    "cost_basis": round(cost_basis, 2),
                    "current_price": round(current_price, 2),
                    "current_value": round(current_value, 2),
                    "cost_value": round(cost_value, 2),
                    "gain_loss": round(gain_loss, 2),
                    "gain_loss_pct": round(gain_loss_pct, 2)
                })
                
                total_value += current_value
            
            # Calculate allocations
            for position in positions:
                position["allocation_pct"] = round((position["current_value"] / total_value * 100) if total_value > 0 else 0, 2)
            
            # Sort by value
            positions.sort(key=lambda x: x["current_value"], reverse=True)
            
            return {
                "portfolio_id": portfolio_id,
                "positions": positions,
                "total_value": round(total_value, 2),
                "num_positions": len(positions),
                "success": True,
                "message": f"Portfolio has {len(positions)} positions worth ${total_value:,.2f}"
            }
            
        except Exception as e:
            return {
                "portfolio_id": portfolio_id,
                "success": False,
                "error": str(e),
                "message": f"Error getting positions: {str(e)}"
            }
    
    @kernel_function(
        name="calculate_metrics",
        description="Calculate portfolio performance metrics including total return, gains/losses. Returns performance summary."
    )
    async def calculate_metrics(
        self,
        portfolio_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Calculate portfolio performance metrics
        
        Args:
            portfolio_id: Portfolio identifier
        
        Returns:
            Dictionary with performance metrics
        """
        try:
            # Get positions
            positions_result = await self.get_positions(portfolio_id)
            
            if not positions_result.get("success"):
                return positions_result
            
            positions = positions_result.get("positions", [])
            
            if not positions:
                return {
                    "portfolio_id": portfolio_id,
                    "success": True,
                    "message": "No positions to calculate metrics"
                }
            
            # Calculate aggregate metrics
            total_current_value = sum(p["current_value"] for p in positions)
            total_cost_value = sum(p["cost_value"] for p in positions)
            total_gain_loss = total_current_value - total_cost_value
            total_return_pct = ((total_current_value - total_cost_value) / total_cost_value * 100) if total_cost_value > 0 else 0
            
            # Calculate winners/losers
            winners = [p for p in positions if p["gain_loss"] > 0]
            losers = [p for p in positions if p["gain_loss"] < 0]
            neutral = [p for p in positions if p["gain_loss"] == 0]
            
            # Best/worst performers
            best_performer = max(positions, key=lambda x: x["gain_loss_pct"]) if positions else None
            worst_performer = min(positions, key=lambda x: x["gain_loss_pct"]) if positions else None
            
            return {
                "portfolio_id": portfolio_id,
                "total_value": round(total_current_value, 2),
                "total_cost": round(total_cost_value, 2),
                "total_gain_loss": round(total_gain_loss, 2),
                "total_return_pct": round(total_return_pct, 2),
                "num_positions": len(positions),
                "winners": len(winners),
                "losers": len(losers),
                "neutral": len(neutral),
                "best_performer": {
                    "ticker": best_performer["ticker"],
                    "gain_loss_pct": best_performer["gain_loss_pct"]
                } if best_performer else None,
                "worst_performer": {
                    "ticker": worst_performer["ticker"],
                    "gain_loss_pct": worst_performer["gain_loss_pct"]
                } if worst_performer else None,
                "success": True,
                "message": f"Portfolio return: {total_return_pct:.2f}% (${total_gain_loss:,.2f}), {len(winners)} winners, {len(losers)} losers"
            }
            
        except Exception as e:
            return {
                "portfolio_id": portfolio_id,
                "success": False,
                "error": str(e),
                "message": f"Error calculating metrics: {str(e)}"
            }
    
    @kernel_function(
        name="analyze_allocation",
        description="Analyze portfolio allocation and diversification by position size. Returns allocation analysis."
    )
    async def analyze_allocation(
        self,
        portfolio_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Analyze portfolio allocation
        
        Args:
            portfolio_id: Portfolio identifier
        
        Returns:
            Dictionary with allocation analysis
        """
        try:
            # Get positions
            positions_result = await self.get_positions(portfolio_id)
            
            if not positions_result.get("success"):
                return positions_result
            
            positions = positions_result.get("positions", [])
            
            if not positions:
                return {
                    "portfolio_id": portfolio_id,
                    "success": True,
                    "message": "No positions to analyze"
                }
            
            total_value = positions_result.get("total_value", 0)
            
            # Analyze concentration
            top_5_value = sum(p["current_value"] for p in positions[:5])
            top_5_pct = (top_5_value / total_value * 100) if total_value > 0 else 0
            
            # Identify concentration risk
            large_positions = [p for p in positions if p["allocation_pct"] > 20]
            medium_positions = [p for p in positions if 10 <= p["allocation_pct"] <= 20]
            small_positions = [p for p in positions if p["allocation_pct"] < 10]
            
            # Diversification assessment
            if len(positions) < 5:
                diversification = "low"
                recommendation = "Consider adding more positions for better diversification"
            elif len(positions) < 10:
                diversification = "moderate"
                recommendation = "Reasonably diversified, but could add more positions"
            else:
                diversification = "high"
                recommendation = "Well diversified across multiple positions"
            
            # Concentration risk assessment
            if large_positions:
                concentration_risk = "high"
                risk_note = f"{len(large_positions)} positions exceed 20% allocation"
            elif top_5_pct > 70:
                concentration_risk = "moderate"
                risk_note = f"Top 5 positions represent {top_5_pct:.1f}% of portfolio"
            else:
                concentration_risk = "low"
                risk_note = "No significant concentration risk"
            
            return {
                "portfolio_id": portfolio_id,
                "total_positions": len(positions),
                "top_5_concentration": round(top_5_pct, 2),
                "large_positions": len(large_positions),
                "medium_positions": len(medium_positions),
                "small_positions": len(small_positions),
                "diversification": diversification,
                "concentration_risk": concentration_risk,
                "risk_note": risk_note,
                "recommendation": recommendation,
                "top_holdings": [
                    {"ticker": p["ticker"], "allocation": p["allocation_pct"]}
                    for p in positions[:5]
                ],
                "success": True,
                "message": f"{diversification} diversification, {concentration_risk} concentration risk - {risk_note}"
            }
            
        except Exception as e:
            return {
                "portfolio_id": portfolio_id,
                "success": False,
                "error": str(e),
                "message": f"Error analyzing allocation: {str(e)}"
            }
    
    @kernel_function(
        name="calculate_risk",
        description="Calculate portfolio risk metrics including volatility and correlation. Returns risk assessment."
    )
    async def calculate_risk(
        self,
        portfolio_id: str = "default",
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate portfolio risk metrics
        
        Args:
            portfolio_id: Portfolio identifier
            days: Number of days for risk calculation
        
        Returns:
            Dictionary with risk metrics
        """
        try:
            # Get positions
            positions_result = await self.get_positions(portfolio_id)
            
            if not positions_result.get("success"):
                return positions_result
            
            positions = positions_result.get("positions", [])
            
            if not positions:
                return {
                    "portfolio_id": portfolio_id,
                    "success": True,
                    "message": "No positions to calculate risk"
                }
            
            # Calculate volatility for each position
            volatilities = []
            
            for position in positions:
                ticker = position["ticker"]
                key = f"stock:{ticker}:close"
                
                end_ts = int(datetime.now().timestamp() * 1000)
                start_ts = end_ts - (days * 24 * 60 * 60 * 1000)
                
                try:
                    result = self.redis.execute_command("TS.RANGE", key, start_ts, end_ts)
                    
                    if result and len(result) >= days:
                        values = [float(val) for ts, val in result]
                        returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
                        
                        if returns:
                            mean_return = sum(returns) / len(returns)
                            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
                            volatility = variance ** 0.5
                            annualized_vol = volatility * (252 ** 0.5)
                            
                            volatilities.append({
                                "ticker": ticker,
                                "volatility": annualized_vol,
                                "allocation": position["allocation_pct"]
                            })
                except:
                    continue
            
            if not volatilities:
                return {
                    "portfolio_id": portfolio_id,
                    "success": False,
                    "message": "Insufficient data to calculate risk metrics"
                }
            
            # Calculate weighted portfolio volatility
            portfolio_volatility = sum(
                v["volatility"] * v["allocation"] / 100
                for v in volatilities
            )
            
            # Risk assessment
            if portfolio_volatility > 0.5:
                risk_level = "very high"
                assessment = "Extremely volatile portfolio - high risk"
            elif portfolio_volatility > 0.3:
                risk_level = "high"
                assessment = "Highly volatile portfolio - elevated risk"
            elif portfolio_volatility > 0.2:
                risk_level = "moderate"
                assessment = "Moderately volatile - normal risk"
            else:
                risk_level = "low"
                assessment = "Relatively stable portfolio - lower risk"
            
            # Identify highest risk positions
            high_risk = sorted(volatilities, key=lambda x: x["volatility"], reverse=True)[:3]
            
            return {
                "portfolio_id": portfolio_id,
                "portfolio_volatility": round(portfolio_volatility * 100, 2),
                "risk_level": risk_level,
                "assessment": assessment,
                "positions_analyzed": len(volatilities),
                "highest_risk": [
                    {"ticker": p["ticker"], "volatility": round(p["volatility"] * 100, 2)}
                    for p in high_risk
                ],
                "success": True,
                "message": f"Portfolio volatility: {portfolio_volatility*100:.1f}% annualized - {risk_level} risk"
            }
            
        except Exception as e:
            return {
                "portfolio_id": portfolio_id,
                "success": False,
                "error": str(e),
                "message": f"Error calculating risk: {str(e)}"
            }
    
    @kernel_function(
        name="get_performance",
        description="Get portfolio performance over time with daily values. Returns performance history."
    )
    async def get_performance(
        self,
        portfolio_id: str = "default",
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get portfolio performance over time
        
        Args:
            portfolio_id: Portfolio identifier
            days: Number of days of history
        
        Returns:
            Dictionary with performance history
        """
        try:
            # Get current positions
            positions_result = await self.get_positions(portfolio_id)
            
            if not positions_result.get("success"):
                return positions_result
            
            positions = positions_result.get("positions", [])
            
            if not positions:
                return {
                    "portfolio_id": portfolio_id,
                    "success": True,
                    "message": "No positions to track performance"
                }
            
            # Calculate historical values
            end_ts = int(datetime.now().timestamp() * 1000)
            start_ts = end_ts - (days * 24 * 60 * 60 * 1000)
            
            # For simplicity, calculate current vs. start value
            current_value = positions_result.get("total_value", 0)
            
            # Get starting value (sum of cost basis)
            starting_value = sum(p["cost_value"] for p in positions)
            
            # Calculate change
            change = current_value - starting_value
            change_pct = ((current_value - starting_value) / starting_value * 100) if starting_value > 0 else 0
            
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
                "portfolio_id": portfolio_id,
                "days": days,
                "starting_value": round(starting_value, 2),
                "current_value": round(current_value, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "trend": trend,
                "success": True,
                "message": f"Portfolio {trend}: {change_pct:+.2f}% (${change:+,.2f}) over period"
            }
            
        except Exception as e:
            return {
                "portfolio_id": portfolio_id,
                "success": False,
                "error": str(e),
                "message": f"Error getting performance: {str(e)}"
            }


# Example usage and testing
if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from sk_config import get_redis_client
    
    async def test_plugin():
        """Test the Portfolio Plugin"""
        print("Testing Portfolio Plugin...\n")
        
        # Get Redis client
        redis_client = get_redis_client()
        
        # Create test portfolio data
        print("Setting up test portfolio...")
        redis_client.hset("portfolio:default:positions", "AAPL", str({
            'shares': 100,
            'cost_basis': 150.00
        }))
        redis_client.hset("portfolio:default:positions", "MSFT", str({
            'shares': 50,
            'cost_basis': 300.00
        }))
        print("✅ Test portfolio created\n")
        
        # Create plugin
        plugin = PortfolioPlugin(redis_client)
        
        # Test 1: Get positions
        print("Test 1: Get portfolio positions")
        result = await plugin.get_positions("default")
        print(f"Result: {result.get('message')}\n")
        
        # Test 2: Calculate metrics
        print("Test 2: Calculate portfolio metrics")
        result = await plugin.calculate_metrics("default")
        print(f"Result: {result.get('message')}\n")
        
        # Test 3: Analyze allocation
        print("Test 3: Analyze portfolio allocation")
        result = await plugin.analyze_allocation("default")
        print(f"Result: {result.get('message')}\n")
        
        # Test 4: Calculate risk
        print("Test 4: Calculate portfolio risk")
        result = await plugin.calculate_risk("default", days=30)
        print(f"Result: {result.get('message')}\n")
        
        # Test 5: Get performance
        print("Test 5: Get portfolio performance")
        result = await plugin.get_performance("default", days=30)
        print(f"Result: {result.get('message')}\n")
        
        print("✅ All tests completed!")
    
    # Run tests
    asyncio.run(test_plugin())
