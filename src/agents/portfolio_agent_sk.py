"""
Portfolio Management Agent for Semantic Kernel
ChatCompletionAgent specializing in portfolio tracking and optimization
"""

import asyncio
from typing import Dict, Any, List, Optional
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.contents import ChatMessageContent, AuthorRole
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sk_config import get_kernel, get_redis_client
from plugins.portfolio_plugin import PortfolioPlugin


class PortfolioAgentSK:
    """
    Portfolio Management Agent using Microsoft Semantic Kernel
    
    Provides comprehensive portfolio management including:
    - Position tracking and valuation
    - Performance metrics and returns
    - Allocation analysis and diversification
    - Risk assessment and management
    - Performance tracking over time
    """
    
    def __init__(self, kernel=None, redis_client=None):
        """
        Initialize Portfolio Management Agent
        
        Args:
            kernel: Semantic Kernel instance (uses default if None)
            redis_client: Redis client (uses default if None)
        """
        # Use provided or default kernel/redis
        self.kernel = kernel or get_kernel()
        self.redis_client = redis_client or get_redis_client()
        
        # Create plugin
        self.plugin = PortfolioPlugin(self.redis_client)
        
        # Define agent instructions
        instructions = """You are a Portfolio Management Agent specializing in portfolio 
tracking, performance analysis, and risk management.

Your capabilities include:
- Track portfolio positions with current valuations
- Calculate performance metrics (returns, gains/losses)
- Analyze allocation and diversification
- Assess portfolio risk and volatility
- Monitor performance trends over time
- Provide optimization recommendations

When responding to queries:
1. Always show current portfolio value and composition
2. Calculate and explain returns clearly (both $ and %)
3. Identify best and worst performing positions
4. Assess concentration risk and diversification
5. Quantify portfolio risk using volatility metrics
6. Provide actionable recommendations for improvement
7. Consider risk-adjusted returns, not just absolute returns
8. Explain the importance of diversification

Available tools:
- get_positions: Current holdings and allocations
- calculate_metrics: Performance returns and statistics
- analyze_allocation: Diversification and concentration analysis
- calculate_risk: Volatility and risk assessment
- get_performance: Historical performance tracking

Always:
- Base recommendations on calculated metrics
- Explain risk/return tradeoffs clearly
- Consider both performance and risk together
- Provide specific, actionable advice
- Never recommend individual securities (focus on portfolio structure)
"""
        
        # Create ChatCompletionAgent with plugin
        self.agent = ChatCompletionAgent(
            kernel=self.kernel,
            name="PortfolioAgent",
            instructions=instructions,
            plugins=[self.plugin]
        )
    
    async def analyze(self, query: str) -> str:
        """
        Analyze using natural language query
        
        Args:
            query: Natural language question about portfolio
        
        Returns:
            Analysis result as string
        """
        try:
            # Create chat history
            history = [
                ChatMessageContent(
                    role=AuthorRole.USER,
                    content=query
                )
            ]
            
            # Invoke agent
            response = ""
            async for message in self.agent.invoke(history):
                if message.role == AuthorRole.ASSISTANT:
                    response += message.content
            
            return response
            
        except Exception as e:
            return f"Error during analysis: {str(e)}"
    
    async def analyze_portfolio(
        self,
        portfolio_id: str = "default",
        include_risk: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive portfolio analysis
        
        Args:
            portfolio_id: Portfolio identifier
            include_risk: Include risk analysis
        
        Returns:
            Dictionary with complete portfolio analysis
        """
        try:
            # Get all portfolio data
            positions = await self.plugin.get_positions(portfolio_id)
            metrics = await self.plugin.calculate_metrics(portfolio_id)
            allocation = await self.plugin.analyze_allocation(portfolio_id)
            
            result = {
                "portfolio_id": portfolio_id,
                "positions": positions,
                "metrics": metrics,
                "allocation": allocation
            }
            
            # Add risk if requested
            if include_risk:
                risk = await self.plugin.calculate_risk(portfolio_id)
                result["risk"] = risk
            
            # Generate AI summary if we have data
            if positions.get("success") and metrics.get("success"):
                total_value = positions.get("total_value", 0)
                return_pct = metrics.get("total_return_pct", 0)
                num_positions = positions.get("num_positions", 0)
                diversification = allocation.get("diversification", "unknown")
                
                summary_query = f"""Provide a comprehensive portfolio analysis:
                - Total value: ${total_value:,.2f}
                - Total return: {return_pct:.2f}%
                - Number of positions: {num_positions}
                - Diversification: {diversification}
                - Winners: {metrics.get('winners', 0)} / Losers: {metrics.get('losers', 0)}
                
                Give a 3-4 sentence assessment with key insights and recommendations."""
                
                ai_summary = await self.analyze(summary_query)
                result["ai_summary"] = ai_summary
            
            return result
            
        except Exception as e:
            return {
                "portfolio_id": portfolio_id,
                "error": str(e),
                "message": f"Error analyzing portfolio: {str(e)}"
            }
    
    async def optimize_allocation(
        self,
        portfolio_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Analyze and provide allocation optimization recommendations
        
        Args:
            portfolio_id: Portfolio identifier
        
        Returns:
            Dictionary with optimization recommendations
        """
        try:
            # Get allocation and risk data
            allocation = await self.plugin.analyze_allocation(portfolio_id)
            risk = await self.plugin.calculate_risk(portfolio_id)
            positions = await self.plugin.get_positions(portfolio_id)
            
            if not allocation.get("success"):
                return allocation
            
            recommendations = []
            
            # Check concentration risk
            large_positions = allocation.get("large_positions", 0)
            if large_positions > 0:
                recommendations.append({
                    "type": "concentration",
                    "severity": "high",
                    "issue": f"{large_positions} positions exceed 20% allocation",
                    "recommendation": "Consider reducing position sizes to below 15% each"
                })
            
            # Check diversification
            num_positions = allocation.get("total_positions", 0)
            if num_positions < 5:
                recommendations.append({
                    "type": "diversification",
                    "severity": "high",
                    "issue": "Insufficient diversification with fewer than 5 positions",
                    "recommendation": "Add 5-10 more positions across different sectors"
                })
            elif num_positions < 10:
                recommendations.append({
                    "type": "diversification",
                    "severity": "moderate",
                    "issue": "Limited diversification with fewer than 10 positions",
                    "recommendation": "Consider adding 3-5 more positions for better diversification"
                })
            
            # Check risk level
            if risk.get("success"):
                risk_level = risk.get("risk_level", "unknown")
                if risk_level in ["high", "very high"]:
                    recommendations.append({
                        "type": "risk",
                        "severity": "high",
                        "issue": f"Portfolio volatility is {risk_level}",
                        "recommendation": "Consider adding lower volatility positions or reducing high-risk positions"
                    })
            
            # Generate AI optimization summary
            rec_text = "\n".join([f"- {r['type']}: {r['issue']}" for r in recommendations])
            
            if recommendations:
                optimization_query = f"""Analyze these portfolio optimization opportunities:
                {rec_text}
                
                What are the top 2-3 actions to improve this portfolio? Be specific."""
                
                ai_optimization = await self.analyze(optimization_query)
            else:
                ai_optimization = "Portfolio appears well-balanced with no major optimization opportunities."
            
            return {
                "portfolio_id": portfolio_id,
                "recommendations": recommendations,
                "num_recommendations": len(recommendations),
                "ai_optimization": ai_optimization,
                "message": f"Found {len(recommendations)} optimization opportunities"
            }
            
        except Exception as e:
            return {
                "portfolio_id": portfolio_id,
                "error": str(e),
                "message": f"Error optimizing allocation: {str(e)}"
            }
    
    async def track_performance(
        self,
        portfolio_id: str = "default",
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Track portfolio performance over time
        
        Args:
            portfolio_id: Portfolio identifier
            days: Number of days to track
        
        Returns:
            Dictionary with performance tracking
        """
        try:
            # Get performance data
            performance = await self.plugin.get_performance(portfolio_id, days)
            metrics = await self.plugin.calculate_metrics(portfolio_id)
            
            if not performance.get("success"):
                return performance
            
            # Get detailed breakdown
            change_pct = performance.get("change_pct", 0)
            trend = performance.get("trend", "unknown")
            
            # Performance assessment
            if change_pct > 10:
                assessment = "excellent"
            elif change_pct > 5:
                assessment = "strong"
            elif change_pct > 0:
                assessment = "positive"
            elif change_pct > -5:
                assessment = "slight decline"
            else:
                assessment = "significant decline"
            
            # Generate AI performance summary
            best = metrics.get("best_performer")
            worst = metrics.get("worst_performer")
            
            perf_query = f"""Analyze this portfolio performance:
            - {days}-day return: {change_pct:.2f}%
            - Trend: {trend}
            - Assessment: {assessment}
            - Best performer: {best['ticker'] if best else 'N/A'} ({best['gain_loss_pct']:.2f}% if best else 0)
            - Worst performer: {worst['ticker'] if worst else 'N/A'} ({worst['gain_loss_pct']:.2f}% if worst else 0)
            
            What's driving performance and what should an investor watch? 2-3 sentences."""
            
            ai_performance = await self.analyze(perf_query)
            
            return {
                "portfolio_id": portfolio_id,
                "days": days,
                "performance": performance,
                "metrics": metrics,
                "assessment": assessment,
                "ai_performance": ai_performance,
                "message": f"{assessment} performance over {days} days: {change_pct:+.2f}%"
            }
            
        except Exception as e:
            return {
                "portfolio_id": portfolio_id,
                "error": str(e),
                "message": f"Error tracking performance: {str(e)}"
            }
    
    async def compare_risk_return(
        self,
        portfolio_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Compare risk-adjusted returns
        
        Args:
            portfolio_id: Portfolio identifier
        
        Returns:
            Dictionary with risk-return analysis
        """
        try:
            # Get metrics and risk
            metrics = await self.plugin.calculate_metrics(portfolio_id)
            risk = await self.plugin.calculate_risk(portfolio_id)
            
            if not metrics.get("success") or not risk.get("success"):
                return {
                    "portfolio_id": portfolio_id,
                    "success": False,
                    "message": "Insufficient data for risk-return analysis"
                }
            
            # Calculate risk-adjusted metrics
            total_return = metrics.get("total_return_pct", 0)
            volatility = risk.get("portfolio_volatility", 1)
            
            # Simple Sharpe-like ratio (return / volatility)
            risk_adjusted_return = total_return / volatility if volatility > 0 else 0
            
            # Assessment
            if risk_adjusted_return > 1.0:
                assessment = "excellent"
                note = "Strong returns relative to risk taken"
            elif risk_adjusted_return > 0.5:
                assessment = "good"
                note = "Positive returns justify the risk"
            elif risk_adjusted_return > 0:
                assessment = "acceptable"
                note = "Returns barely compensate for risk"
            else:
                assessment = "poor"
                note = "Returns don't justify the risk taken"
            
            # Generate AI analysis
            analysis_query = f"""Analyze this risk-return profile:
            - Total return: {total_return:.2f}%
            - Portfolio volatility: {volatility:.2f}%
            - Risk-adjusted return: {risk_adjusted_return:.2f}
            - Assessment: {assessment}
            
            Is this an attractive risk-return tradeoff? What could improve it?"""
            
            ai_analysis = await self.analyze(analysis_query)
            
            return {
                "portfolio_id": portfolio_id,
                "total_return": round(total_return, 2),
                "volatility": round(volatility, 2),
                "risk_adjusted_return": round(risk_adjusted_return, 2),
                "assessment": assessment,
                "note": note,
                "ai_analysis": ai_analysis,
                "success": True,
                "message": f"{assessment} risk-return profile: {risk_adjusted_return:.2f} ratio"
            }
            
        except Exception as e:
            return {
                "portfolio_id": portfolio_id,
                "error": str(e),
                "message": f"Error comparing risk-return: {str(e)}"
            }
    
    async def close(self):
        """Cleanup resources"""
        try:
            if hasattr(self.redis_client, 'close'):
                self.redis_client.close()
        except Exception:
            pass


# Example usage and testing
if __name__ == "__main__":
    async def test_agent():
        """Test the Portfolio Management Agent"""
        print("Testing Portfolio Management Agent with Semantic Kernel...\n")
        
        # Create agent
        agent = PortfolioAgentSK()
        
        # Test 1: Natural language query
        print("Test 1: Ask about portfolio status")
        response = await agent.analyze("What's the current status of my portfolio?")
        print(f"Response: {response}\n")
        
        # Test 2: Comprehensive portfolio analysis
        print("Test 2: Analyze portfolio comprehensively")
        result = await agent.analyze_portfolio("default", include_risk=True)
        print(f"Positions: {result.get('positions', {}).get('message')}")
        print(f"Metrics: {result.get('metrics', {}).get('message')}")
        print(f"Allocation: {result.get('allocation', {}).get('message')}")
        if "ai_summary" in result:
            print(f"AI Summary: {result['ai_summary']}\n")
        
        # Test 3: Optimize allocation
        print("Test 3: Get optimization recommendations")
        optimization = await agent.optimize_allocation("default")
        print(f"Recommendations: {optimization.get('message')}")
        if "ai_optimization" in optimization:
            print(f"AI Optimization: {optimization['ai_optimization']}\n")
        
        # Test 4: Track performance
        print("Test 4: Track performance over time")
        performance = await agent.track_performance("default", days=30)
        print(f"Performance: {performance.get('message')}")
        if "ai_performance" in performance:
            print(f"AI Performance: {performance['ai_performance']}\n")
        
        # Test 5: Risk-return analysis
        print("Test 5: Compare risk and return")
        risk_return = await agent.compare_risk_return("default")
        print(f"Risk-Return: {risk_return.get('message')}")
        if "ai_analysis" in risk_return:
            print(f"AI Analysis: {risk_return['ai_analysis']}\n")
        
        print("✅ All tests completed!")
        
        # Cleanup
        await agent.close()
    
    # Run tests
    asyncio.run(test_agent())
