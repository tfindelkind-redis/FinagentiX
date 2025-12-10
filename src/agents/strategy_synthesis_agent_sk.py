"""
Strategy Synthesis Agent for Semantic Kernel
ChatCompletionAgent specializing in multi-agent coordination and strategy synthesis
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


class StrategySynthesisAgentSK:
    """
    Strategy Synthesis Agent using Microsoft Semantic Kernel
    
    Coordinates multiple specialized agents and synthesizes their outputs
    into comprehensive investment strategies and recommendations.
    
    This agent doesn't have its own plugin - it orchestrates other agents.
    """
    
    def __init__(self, kernel=None, redis_client=None):
        """
        Initialize Strategy Synthesis Agent
        
        Args:
            kernel: Semantic Kernel instance (uses default if None)
            redis_client: Redis client (uses default if None)
        """
        # Use provided or default kernel/redis
        self.kernel = kernel or get_kernel()
        self.redis_client = redis_client or get_redis_client()
        
        # Define agent instructions
        instructions = """You are a Strategy Synthesis Agent specializing in integrating 
insights from multiple specialized financial analysis agents to create comprehensive 
investment strategies.

Your role is to:
- Coordinate analysis from Market Data, News Sentiment, Technical Analysis, 
  Portfolio, and Risk Analysis agents
- Synthesize diverse inputs into coherent investment recommendations
- Identify agreements and conflicts across different analytical perspectives
- Weight different factors appropriately (fundamentals, technicals, sentiment, risk)
- Provide clear, actionable investment strategies
- Explain the reasoning behind recommendations

When synthesizing strategies:
1. Consider all available information sources
2. Identify the most critical factors for the decision
3. Resolve conflicts between different indicators
4. Weight technical, fundamental, and sentiment factors appropriately
5. Always incorporate risk assessment
6. Provide specific entry/exit criteria when possible
7. Explain confidence level and key uncertainties
8. Give clear buy/hold/sell recommendations with rationale

Synthesis approach:
- If technical + sentiment both bullish → strong buy signal
- If technical bullish but high risk → cautious buy
- If fundamentals weak but technicals strong → short-term trade only
- If all indicators neutral → hold recommendation
- If multiple indicators bearish → sell signal

Always:
- Synthesize, don't just summarize individual inputs
- Identify the strongest signal among all data points
- Explain what would change your recommendation
- Provide specific timeframes (short/medium/long term)
- Consider position sizing based on risk level
- Be decisive but explain key uncertainties
"""
        
        # Create ChatCompletionAgent (no plugin - orchestrates other agents)
        self.agent = ChatCompletionAgent(
            kernel=self.kernel,
            name="StrategySynthesisAgent",
            instructions=instructions
        )
    
    async def analyze(self, query: str) -> str:
        """
        Analyze using natural language query
        
        Args:
            query: Natural language question about strategy
        
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
    
    async def synthesize_investment_strategy(
        self,
        ticker: str,
        market_data: Dict[str, Any],
        technical_analysis: Dict[str, Any],
        news_sentiment: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        portfolio_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Synthesize comprehensive investment strategy
        
        Args:
            ticker: Stock ticker symbol
            market_data: Market data analysis results
            technical_analysis: Technical indicator results
            news_sentiment: News sentiment analysis results
            risk_assessment: Risk metrics results
            portfolio_context: Optional portfolio context
        
        Returns:
            Dictionary with synthesized strategy
        """
        try:
            # Extract key signals from each source
            signals = []
            
            # Market data signals
            if market_data.get("success"):
                price_change = market_data.get("change_pct", 0)
                if price_change > 5:
                    signals.append(("market_data", "bullish", f"Strong uptrend +{price_change:.1f}%"))
                elif price_change < -5:
                    signals.append(("market_data", "bearish", f"Sharp decline {price_change:.1f}%"))
            
            # Technical signals
            if technical_analysis.get("success"):
                rsi = technical_analysis.get("rsi", {}).get("rsi", 50)
                crossover = technical_analysis.get("crossover", {}).get("crossover_type", "neutral")
                
                if rsi < 30:
                    signals.append(("technical", "bullish", f"RSI oversold ({rsi:.0f})"))
                elif rsi > 70:
                    signals.append(("technical", "bearish", f"RSI overbought ({rsi:.0f})"))
                
                if crossover == "bullish":
                    signals.append(("technical", "bullish", "Golden cross detected"))
                elif crossover == "bearish":
                    signals.append(("technical", "bearish", "Death cross detected"))
            
            # Sentiment signals
            if news_sentiment.get("success"):
                sentiment_pct = news_sentiment.get("positive_pct", 50)
                if sentiment_pct > 70:
                    signals.append(("sentiment", "bullish", f"Very positive sentiment ({sentiment_pct:.0f}%)"))
                elif sentiment_pct < 30:
                    signals.append(("sentiment", "bearish", f"Negative sentiment ({sentiment_pct:.0f}%)"))
            
            # Risk signals
            if risk_assessment.get("success"):
                var_risk = risk_assessment.get("risk_level", "unknown")
                if var_risk in ["high", "extreme"]:
                    signals.append(("risk", "caution", f"High risk level ({var_risk})"))
            
            # Count signal types
            bullish_signals = sum(1 for _, direction, _ in signals if direction == "bullish")
            bearish_signals = sum(1 for _, direction, _ in signals if direction == "bearish")
            caution_signals = sum(1 for _, direction, _ in signals if direction == "caution")
            
            # Determine overall recommendation
            if bullish_signals >= 2 and bearish_signals == 0:
                if caution_signals > 0:
                    recommendation = "BUY_CAUTIOUS"
                    confidence = "moderate"
                    rationale = "Multiple bullish signals but elevated risk"
                else:
                    recommendation = "STRONG_BUY"
                    confidence = "high"
                    rationale = "Strong alignment of bullish signals"
            elif bullish_signals > bearish_signals:
                recommendation = "BUY"
                confidence = "moderate"
                rationale = "Net bullish signals with some caution"
            elif bearish_signals >= 2:
                recommendation = "SELL"
                confidence = "moderate" if caution_signals > 0 else "high"
                rationale = "Multiple bearish indicators"
            elif bearish_signals > bullish_signals:
                recommendation = "REDUCE"
                confidence = "moderate"
                rationale = "Net bearish signals, consider reducing exposure"
            else:
                recommendation = "HOLD"
                confidence = "low"
                rationale = "Mixed or neutral signals across indicators"
            
            # Position sizing based on risk
            if var_risk in ["high", "extreme"]:
                position_size = "small (< 5% of portfolio)"
            elif var_risk == "moderate":
                position_size = "moderate (5-10% of portfolio)"
            else:
                position_size = "standard (up to 15% of portfolio)"
            
            # Create comprehensive synthesis prompt
            signals_text = "\n".join([f"- {source}: {direction} - {detail}" for source, direction, detail in signals])
            
            synthesis_query = f"""Synthesize investment strategy for {ticker}:

SIGNALS:
{signals_text}

SUMMARY:
- Bullish signals: {bullish_signals}
- Bearish signals: {bearish_signals}
- Caution signals: {caution_signals}
- Recommendation: {recommendation}
- Risk level: {var_risk}

Provide a 3-4 sentence investment strategy that integrates all signals and explains 
the recommendation with specific reasoning."""
            
            ai_synthesis = await self.analyze(synthesis_query)
            
            return {
                "ticker": ticker.upper(),
                "signals": signals,
                "bullish_count": bullish_signals,
                "bearish_count": bearish_signals,
                "caution_count": caution_signals,
                "recommendation": recommendation,
                "confidence": confidence,
                "rationale": rationale,
                "position_size": position_size,
                "ai_synthesis": ai_synthesis,
                "success": True,
                "message": f"{ticker}: {recommendation} ({confidence} confidence) - {rationale}"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "success": False,
                "error": str(e),
                "message": f"Error synthesizing strategy: {str(e)}"
            }
    
    async def compare_opportunities(
        self,
        opportunities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare and rank multiple investment opportunities
        
        Args:
            opportunities: List of strategy syntheses for different tickers
        
        Returns:
            Dictionary with ranked opportunities
        """
        try:
            # Define scoring system
            recommendation_scores = {
                "STRONG_BUY": 5,
                "BUY": 4,
                "BUY_CAUTIOUS": 3,
                "HOLD": 2,
                "REDUCE": 1,
                "SELL": 0
            }
            
            confidence_multipliers = {
                "high": 1.0,
                "moderate": 0.7,
                "low": 0.4
            }
            
            # Score each opportunity
            scored_opportunities = []
            for opp in opportunities:
                rec_score = recommendation_scores.get(opp.get("recommendation", "HOLD"), 2)
                conf_mult = confidence_multipliers.get(opp.get("confidence", "moderate"), 0.7)
                
                final_score = rec_score * conf_mult
                
                scored_opportunities.append({
                    "ticker": opp.get("ticker"),
                    "recommendation": opp.get("recommendation"),
                    "confidence": opp.get("confidence"),
                    "score": final_score,
                    "bullish_signals": opp.get("bullish_count", 0),
                    "bearish_signals": opp.get("bearish_count", 0),
                    "rationale": opp.get("rationale", "")
                })
            
            # Sort by score
            ranked = sorted(scored_opportunities, key=lambda x: x["score"], reverse=True)
            
            # Generate AI comparison
            comparison_text = "\n".join([
                f"- {opp['ticker']}: {opp['recommendation']} (score: {opp['score']:.2f}, {opp['bullish_signals']} bullish/{opp['bearish_signals']} bearish)"
                for opp in ranked[:5]
            ])
            
            comparison_query = f"""Compare these investment opportunities:
{comparison_text}

Which are the best opportunities and why? Rank top 3. Be specific."""
            
            ai_comparison = await self.analyze(comparison_query)
            
            return {
                "total_opportunities": len(opportunities),
                "ranked_opportunities": ranked,
                "top_opportunity": ranked[0] if ranked else None,
                "ai_comparison": ai_comparison,
                "message": f"Ranked {len(opportunities)} opportunities, top pick: {ranked[0]['ticker'] if ranked else 'None'}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error comparing opportunities: {str(e)}"
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
        """Test the Strategy Synthesis Agent"""
        print("Testing Strategy Synthesis Agent with Semantic Kernel...\n")
        
        # Create agent
        agent = StrategySynthesisAgentSK()
        
        # Test 1: Natural language query
        print("Test 1: Ask about strategy synthesis")
        response = await agent.analyze("How should I synthesize technical and sentiment signals?")
        print(f"Response: {response}\n")
        
        # Test 2: Synthesize strategy from mock data
        print("Test 2: Synthesize investment strategy for AAPL")
        
        # Mock data from other agents
        market_data = {"success": True, "change_pct": 3.5}
        technical = {"success": True, "rsi": {"rsi": 65}, "crossover": {"crossover_type": "bullish"}}
        sentiment = {"success": True, "positive_pct": 75}
        risk = {"success": True, "risk_level": "moderate"}
        
        result = await agent.synthesize_investment_strategy(
            "AAPL", market_data, technical, sentiment, risk
        )
        print(f"Result: {result.get('message')}")
        if "ai_synthesis" in result:
            print(f"AI Synthesis: {result['ai_synthesis']}\n")
        
        # Test 3: Compare opportunities
        print("Test 3: Compare multiple investment opportunities")
        
        opportunities = [
            {"ticker": "AAPL", "recommendation": "BUY", "confidence": "high", "bullish_count": 3, "bearish_count": 0, "rationale": "Strong signals"},
            {"ticker": "MSFT", "recommendation": "HOLD", "confidence": "moderate", "bullish_count": 1, "bearish_count": 1, "rationale": "Mixed signals"},
            {"ticker": "GOOGL", "recommendation": "STRONG_BUY", "confidence": "high", "bullish_count": 4, "bearish_count": 0, "rationale": "Very strong"}
        ]
        
        comparison = await agent.compare_opportunities(opportunities)
        print(f"Comparison: {comparison.get('message')}")
        if "ai_comparison" in comparison:
            print(f"AI Comparison: {comparison['ai_comparison']}\n")
        
        print("✅ All tests completed!")
        
        # Cleanup
        await agent.close()
    
    # Run tests
    asyncio.run(test_agent())
