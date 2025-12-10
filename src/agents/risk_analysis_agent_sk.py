"""
Risk Analysis Agent for Semantic Kernel
ChatCompletionAgent specializing in portfolio risk assessment
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
from plugins.risk_analysis_plugin import RiskAnalysisPlugin


class RiskAnalysisAgentSK:
    """
    Risk Analysis Agent using Microsoft Semantic Kernel
    
    Provides comprehensive risk assessment including:
    - Value at Risk (VaR) calculations
    - Beta and market correlation
    - Stress testing scenarios
    - Maximum drawdown analysis
    - Tail risk assessment
    """
    
    def __init__(self, kernel=None, redis_client=None):
        """
        Initialize Risk Analysis Agent
        
        Args:
            kernel: Semantic Kernel instance (uses default if None)
            redis_client: Redis client (uses default if None)
        """
        # Use provided or default kernel/redis
        self.kernel = kernel or get_kernel()
        self.redis_client = redis_client or get_redis_client()
        
        # Create plugin
        self.plugin = RiskAnalysisPlugin(self.redis_client)
        
        # Define agent instructions
        instructions = """You are a Risk Analysis Agent specializing in portfolio risk 
assessment and management.

Your capabilities include:
- Calculate Value at Risk (VaR) for positions
- Assess market correlation through beta analysis
- Run stress test scenarios
- Analyze maximum drawdown and recovery
- Evaluate tail risk and extreme events

When responding to queries:
1. Quantify risk using standard metrics (VaR, beta, drawdown)
2. Explain risk levels in terms investors understand
3. Compare risk across different positions
4. Identify the most significant risk factors
5. Provide specific risk mitigation recommendations
6. Consider both normal and extreme scenarios
7. Assess probability and impact of risk events
8. Explain risk-return tradeoffs clearly

Available tools:
- calculate_var: Value at Risk calculation
- calculate_beta: Market correlation metrics
- stress_test: Scenario analysis
- calculate_drawdown: Peak-to-trough analysis
- assess_tail_risk: Extreme event probability

Always:
- Base assessments on calculated risk metrics
- Explain what each risk metric means
- Identify the highest priority risks
- Provide actionable risk management advice
- Consider both upside and downside risk
- Never minimize or exaggerate risk levels
"""
        
        # Create ChatCompletionAgent with plugin
        self.agent = ChatCompletionAgent(
            kernel=self.kernel,
            name="RiskAnalysisAgent",
            instructions=instructions,
            plugins=[self.plugin]
        )
    
    async def analyze(self, query: str) -> str:
        """
        Analyze using natural language query
        
        Args:
            query: Natural language question about risk
        
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
    
    async def comprehensive_risk_assessment(
        self,
        ticker: str
    ) -> Dict[str, Any]:
        """
        Comprehensive risk assessment for a position
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with complete risk analysis
        """
        try:
            # Calculate all risk metrics
            var = await self.plugin.calculate_var(ticker, confidence=0.95)
            beta = await self.plugin.calculate_beta(ticker)
            stress = await self.plugin.stress_test(ticker)
            drawdown = await self.plugin.calculate_drawdown(ticker)
            tail_risk = await self.plugin.assess_tail_risk(ticker)
            
            result = {
                "ticker": ticker.upper(),
                "var": var,
                "beta": beta,
                "stress_test": stress,
                "drawdown": drawdown,
                "tail_risk": tail_risk
            }
            
            # Generate AI summary
            if var.get("success") and beta.get("success"):
                var_pct = var.get("var_pct", 0)
                beta_value = beta.get("beta", 1)
                max_drawdown = drawdown.get("max_drawdown_pct", 0)
                worst_stress = stress.get("worst_case_loss", 0) if stress.get("success") else 0
                
                summary_query = f"""Provide comprehensive risk assessment for {ticker}:
                - VaR (95%): {var_pct:.2f}%
                - Beta: {beta_value:.2f}
                - Max Drawdown: {max_drawdown:.1f}%
                - Stress Test Worst Case: {worst_stress:.1f}%
                
                What are the key risks and recommendations? 3-4 sentences."""
                
                ai_summary = await self.analyze(summary_query)
                result["ai_summary"] = ai_summary
            
            return result
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "error": str(e),
                "message": f"Error in comprehensive assessment: {str(e)}"
            }
    
    async def compare_risk(
        self,
        tickers: List[str]
    ) -> Dict[str, Any]:
        """
        Compare risk across multiple positions
        
        Args:
            tickers: List of ticker symbols
        
        Returns:
            Dictionary with risk comparison
        """
        try:
            risk_profiles = {}
            
            # Calculate key metrics for each ticker
            for ticker in tickers:
                var = await self.plugin.calculate_var(ticker, confidence=0.95)
                beta = await self.plugin.calculate_beta(ticker)
                drawdown = await self.plugin.calculate_drawdown(ticker)
                
                if var.get("success"):
                    risk_profiles[ticker] = {
                        "var_pct": var.get("var_pct", 0),
                        "beta": beta.get("beta", 1) if beta.get("success") else 1,
                        "drawdown": drawdown.get("max_drawdown_pct", 0) if drawdown.get("success") else 0,
                        "var_risk": var.get("risk_level", "unknown"),
                        "drawdown_risk": drawdown.get("risk_level", "unknown") if drawdown.get("success") else "unknown"
                    }
            
            # Rank by risk
            sorted_by_var = sorted(risk_profiles.items(), key=lambda x: x[1]["var_pct"], reverse=True)
            sorted_by_drawdown = sorted(risk_profiles.items(), key=lambda x: x[1]["drawdown"], reverse=True)
            
            # Generate AI comparison
            comparison_text = "\n".join([
                f"- {ticker}: VaR {profile['var_pct']:.2f}%, Beta {profile['beta']:.2f}, Drawdown {profile['drawdown']:.1f}%"
                for ticker, profile in risk_profiles.items()
            ])
            
            comparison_query = f"""Compare risk profiles:
            {comparison_text}
            
            Which position has the highest risk? What's the safest? Brief 2-3 sentence comparison."""
            
            ai_comparison = await self.analyze(comparison_query)
            
            return {
                "tickers": tickers,
                "risk_profiles": risk_profiles,
                "highest_var": sorted_by_var[0] if sorted_by_var else None,
                "highest_drawdown": sorted_by_drawdown[0] if sorted_by_drawdown else None,
                "lowest_var": sorted_by_var[-1] if sorted_by_var else None,
                "ai_comparison": ai_comparison,
                "message": f"Risk comparison complete for {len(tickers)} positions"
            }
            
        except Exception as e:
            return {
                "tickers": tickers,
                "error": str(e),
                "message": f"Error comparing risk: {str(e)}"
            }
    
    async def identify_portfolio_risks(
        self,
        portfolio_tickers: List[str]
    ) -> Dict[str, Any]:
        """
        Identify key portfolio-level risks
        
        Args:
            portfolio_tickers: List of tickers in portfolio
        
        Returns:
            Dictionary with portfolio risk analysis
        """
        try:
            risks = []
            
            # Analyze each position
            for ticker in portfolio_tickers:
                var = await self.plugin.calculate_var(ticker)
                beta = await self.plugin.calculate_beta(ticker)
                tail = await self.plugin.assess_tail_risk(ticker)
                
                # Identify high-risk positions
                if var.get("success"):
                    var_risk = var.get("risk_level", "unknown")
                    if var_risk in ["high", "extreme"]:
                        risks.append({
                            "ticker": ticker,
                            "type": "high_var",
                            "severity": var_risk,
                            "detail": f"VaR {var.get('var_pct', 0):.2f}%",
                            "recommendation": f"Consider reducing {ticker} position size"
                        })
                
                # Identify high beta (market sensitive) positions
                if beta.get("success"):
                    beta_value = beta.get("beta", 1)
                    if abs(beta_value) > 1.5:
                        risks.append({
                            "ticker": ticker,
                            "type": "high_beta",
                            "severity": "moderate",
                            "detail": f"Beta {beta_value:.2f}",
                            "recommendation": f"{ticker} is highly correlated with market moves"
                        })
                
                # Identify tail risk
                if tail.get("success"):
                    tail_risk_level = tail.get("tail_risk", "low")
                    if tail_risk_level in ["high", "moderate"]:
                        risks.append({
                            "ticker": ticker,
                            "type": "tail_risk",
                            "severity": tail_risk_level,
                            "detail": f"{tail.get('negative_tail_events', 0)} tail events",
                            "recommendation": f"Monitor {ticker} for extreme events"
                        })
            
            # Prioritize risks
            high_severity = [r for r in risks if r["severity"] in ["high", "extreme"]]
            moderate_severity = [r for r in risks if r["severity"] == "moderate"]
            
            # Generate AI summary
            risk_summary = "\n".join([
                f"- {r['ticker']}: {r['type']} ({r['severity']}) - {r['detail']}"
                for r in risks[:5]  # Top 5
            ])
            
            if risks:
                summary_query = f"""Portfolio risk analysis found {len(risks)} risk factors:
                {risk_summary}
                
                What are the top 2-3 priorities for risk management? Be specific."""
                
                ai_summary = await self.analyze(summary_query)
            else:
                ai_summary = "No significant portfolio risks identified. Continue standard monitoring."
            
            return {
                "portfolio_tickers": portfolio_tickers,
                "total_risks": len(risks),
                "high_severity_risks": len(high_severity),
                "moderate_severity_risks": len(moderate_severity),
                "risks": risks,
                "ai_summary": ai_summary,
                "message": f"Identified {len(risks)} risk factors ({len(high_severity)} high severity)"
            }
            
        except Exception as e:
            return {
                "portfolio_tickers": portfolio_tickers,
                "error": str(e),
                "message": f"Error identifying risks: {str(e)}"
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
        """Test the Risk Analysis Agent"""
        print("Testing Risk Analysis Agent with Semantic Kernel...\n")
        
        # Create agent
        agent = RiskAnalysisAgentSK()
        
        # Test 1: Natural language query
        print("Test 1: Ask about VaR")
        response = await agent.analyze("What is the Value at Risk for AAPL at 95% confidence?")
        print(f"Response: {response}\n")
        
        # Test 2: Comprehensive risk assessment
        print("Test 2: Comprehensive risk assessment for AAPL")
        result = await agent.comprehensive_risk_assessment("AAPL")
        print(f"VaR: {result.get('var', {}).get('message')}")
        print(f"Beta: {result.get('beta', {}).get('message')}")
        print(f"Drawdown: {result.get('drawdown', {}).get('message')}")
        if "ai_summary" in result:
            print(f"AI Summary: {result['ai_summary']}\n")
        
        # Test 3: Compare risk across tickers
        print("Test 3: Compare risk across multiple stocks")
        comparison = await agent.compare_risk(["AAPL", "MSFT", "GOOGL"])
        print(f"Comparison: {comparison.get('message')}")
        if "ai_comparison" in comparison:
            print(f"AI Comparison: {comparison['ai_comparison']}\n")
        
        # Test 4: Identify portfolio risks
        print("Test 4: Identify portfolio-level risks")
        risks = await agent.identify_portfolio_risks(["AAPL", "MSFT", "GOOGL"])
        print(f"Risks: {risks.get('message')}")
        if "ai_summary" in risks:
            print(f"AI Summary: {risks['ai_summary']}\n")
        
        print("✅ All tests completed!")
        
        # Cleanup
        await agent.close()
    
    # Run tests
    asyncio.run(test_agent())
