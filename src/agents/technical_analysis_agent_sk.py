"""
Technical Analysis Agent for Semantic Kernel
ChatCompletionAgent specializing in technical analysis and chart patterns
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
from plugins.technical_analysis_plugin import TechnicalAnalysisPlugin


class TechnicalAnalysisAgentSK:
    """
    Technical Analysis Agent using Microsoft Semantic Kernel
    
    Provides comprehensive technical analysis including:
    - Moving averages (SMA)
    - Relative Strength Index (RSI)
    - MA crossover detection
    - Support/resistance levels
    - Volatility analysis
    """
    
    def __init__(self, kernel=None, redis_client=None):
        """
        Initialize Technical Analysis Agent
        
        Args:
            kernel: Semantic Kernel instance (uses default if None)
            redis_client: Redis client (uses default if None)
        """
        # Use provided or default kernel/redis
        self.kernel = kernel or get_kernel()
        self.redis_client = redis_client or get_redis_client()
        
        # Create plugin
        self.plugin = TechnicalAnalysisPlugin(self.redis_client)
        
        # Define agent instructions
        instructions = """You are a Technical Analysis Agent specializing in stock market 
technical indicators and chart pattern analysis.

Your capabilities include:
- Calculate moving averages (SMA) and trend analysis
- Calculate Relative Strength Index (RSI) for momentum
- Detect moving average crossovers (golden/death cross)
- Identify support and resistance levels
- Calculate price volatility and risk assessment

When responding to queries:
1. Use technical indicators to assess price trends
2. Explain overbought/oversold conditions clearly
3. Identify potential entry/exit points based on indicators
4. Quantify risk levels using volatility metrics
5. Provide actionable trading signals when indicators align
6. Consider multiple timeframes when possible
7. Explain the significance of support/resistance breaks

Available tools:
- calculate_sma: Simple Moving Average calculations
- calculate_rsi: RSI momentum indicator
- detect_crossover: MA crossover signals
- get_support_resistance: Key price levels
- get_volatility: Risk and volatility metrics

Always:
- Base analysis on actual calculated indicators
- Explain what indicators mean in plain language
- Note when indicators give conflicting signals
- Provide context for technical readings
- Never fabricate technical indicator values
"""
        
        # Create ChatCompletionAgent with plugin
        self.agent = ChatCompletionAgent(
            kernel=self.kernel,
            name="TechnicalAnalysisAgent",
            instructions=instructions,
            plugins=[self.plugin]
        )
    
    async def analyze(self, query: str) -> str:
        """
        Analyze using natural language query
        
        Args:
            query: Natural language question about technical analysis
        
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
    
    async def analyze_ticker(
        self,
        ticker: str,
        include_volatility: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive technical analysis for a ticker
        
        Args:
            ticker: Stock ticker symbol
            include_volatility: Include volatility analysis
        
        Returns:
            Dictionary with technical analysis
        """
        try:
            # Calculate indicators
            sma_20 = await self.plugin.calculate_sma(ticker, period=20)
            sma_50 = await self.plugin.calculate_sma(ticker, period=50)
            rsi = await self.plugin.calculate_rsi(ticker, period=14)
            crossover = await self.plugin.detect_crossover(ticker, short_period=20, long_period=50)
            support_resistance = await self.plugin.get_support_resistance(ticker, days=30)
            
            result = {
                "ticker": ticker.upper(),
                "sma_20": sma_20,
                "sma_50": sma_50,
                "rsi": rsi,
                "crossover": crossover,
                "support_resistance": support_resistance
            }
            
            # Add volatility if requested
            if include_volatility:
                volatility = await self.plugin.get_volatility(ticker, days=20)
                result["volatility"] = volatility
            
            # Generate AI summary if we have data
            if sma_20.get("success") and rsi.get("success"):
                current_price = sma_20.get("current_price", 0)
                sma_trend = sma_20.get("trend", "unknown")
                rsi_value = rsi.get("rsi", 50)
                rsi_status = rsi.get("status", "neutral")
                crossover_type = crossover.get("crossover_type", "neutral")
                
                summary_query = f"""Provide a concise technical analysis summary for {ticker}:
                - Current price: ${current_price}
                - 20-period SMA trend: {sma_trend}
                - RSI: {rsi_value} ({rsi_status})
                - MA crossover: {crossover_type}
                
                Give a 2-3 sentence summary with actionable insights."""
                
                ai_summary = await self.analyze(summary_query)
                result["ai_summary"] = ai_summary
            
            return result
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "error": str(e),
                "message": f"Error analyzing ticker: {str(e)}"
            }
    
    async def compare_technical(
        self,
        tickers: List[str],
        metric: str = "rsi"
    ) -> Dict[str, Any]:
        """
        Compare technical indicators across multiple tickers
        
        Args:
            tickers: List of ticker symbols
            metric: Indicator to compare (rsi, sma, volatility)
        
        Returns:
            Dictionary with comparison results
        """
        try:
            results = {}
            
            # Calculate metric for each ticker
            for ticker in tickers:
                if metric == "rsi":
                    results[ticker] = await self.plugin.calculate_rsi(ticker)
                elif metric == "sma":
                    results[ticker] = await self.plugin.calculate_sma(ticker, period=20)
                elif metric == "volatility":
                    results[ticker] = await self.plugin.get_volatility(ticker)
                else:
                    return {"error": f"Unknown metric: {metric}"}
            
            # Sort by metric value
            if metric == "rsi":
                sorted_tickers = sorted(
                    [(t, r.get("rsi", 0)) for t, r in results.items() if r.get("success")],
                    key=lambda x: x[1],
                    reverse=True
                )
            elif metric == "volatility":
                sorted_tickers = sorted(
                    [(t, r.get("annualized_volatility", 0)) for t, r in results.items() if r.get("success")],
                    key=lambda x: x[1],
                    reverse=True
                )
            else:
                sorted_tickers = [(t, r.get("sma", 0)) for t, r in results.items() if r.get("success")]
            
            # Generate AI comparison summary
            comparison_text = ", ".join([f"{t}: {v:.1f}" for t, v in sorted_tickers])
            comparison_query = f"""Compare these {metric.upper()} readings across stocks:
            {comparison_text}
            
            Which stocks show the strongest/weakest signals? Give a brief comparison."""
            
            ai_comparison = await self.analyze(comparison_query)
            
            return {
                "metric": metric,
                "tickers": tickers,
                "results": results,
                "sorted": sorted_tickers,
                "highest": sorted_tickers[0] if sorted_tickers else None,
                "lowest": sorted_tickers[-1] if sorted_tickers else None,
                "comparison_summary": ai_comparison
            }
            
        except Exception as e:
            return {
                "metric": metric,
                "tickers": tickers,
                "error": str(e),
                "message": f"Error comparing technical indicators: {str(e)}"
            }
    
    async def detect_signals(
        self,
        ticker: str
    ) -> Dict[str, Any]:
        """
        Detect buy/sell signals based on multiple indicators
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with trading signals
        """
        try:
            # Get all relevant indicators
            rsi = await self.plugin.calculate_rsi(ticker)
            crossover = await self.plugin.detect_crossover(ticker, short_period=20, long_period=50)
            support_resistance = await self.plugin.get_support_resistance(ticker, days=30)
            
            signals = []
            
            # RSI signals
            if rsi.get("success"):
                rsi_value = rsi.get("rsi", 50)
                if rsi_value <= 30:
                    signals.append({
                        "type": "buy",
                        "indicator": "RSI",
                        "value": rsi_value,
                        "reason": "RSI oversold (below 30)"
                    })
                elif rsi_value >= 70:
                    signals.append({
                        "type": "sell",
                        "indicator": "RSI",
                        "value": rsi_value,
                        "reason": "RSI overbought (above 70)"
                    })
            
            # Crossover signals
            if crossover.get("success"):
                crossover_type = crossover.get("crossover_type")
                if crossover_type == "bullish":
                    signals.append({
                        "type": "buy",
                        "indicator": "MA Crossover",
                        "value": crossover_type,
                        "reason": "Golden cross - short MA above long MA"
                    })
                elif crossover_type == "bearish":
                    signals.append({
                        "type": "sell",
                        "indicator": "MA Crossover",
                        "value": crossover_type,
                        "reason": "Death cross - short MA below long MA"
                    })
            
            # Support/Resistance signals
            if support_resistance.get("success"):
                position = support_resistance.get("position", "")
                current_price = support_resistance.get("current_price", 0)
                support = support_resistance.get("support", 0)
                resistance = support_resistance.get("resistance", 0)
                
                if "near support" in position:
                    signals.append({
                        "type": "buy",
                        "indicator": "Support Level",
                        "value": support,
                        "reason": f"Price near support at ${support:.2f}"
                    })
                elif "near resistance" in position:
                    signals.append({
                        "type": "sell",
                        "indicator": "Resistance Level",
                        "value": resistance,
                        "reason": f"Price near resistance at ${resistance:.2f}"
                    })
            
            # Count signal types
            buy_signals = sum(1 for s in signals if s["type"] == "buy")
            sell_signals = sum(1 for s in signals if s["type"] == "sell")
            
            # Determine overall recommendation
            if buy_signals > sell_signals:
                overall = "buy"
                confidence = "high" if buy_signals >= 2 else "moderate"
            elif sell_signals > buy_signals:
                overall = "sell"
                confidence = "high" if sell_signals >= 2 else "moderate"
            else:
                overall = "neutral"
                confidence = "low"
            
            # Generate AI interpretation
            signals_text = "\n".join([f"- {s['indicator']}: {s['reason']}" for s in signals])
            interpretation_query = f"""Interpret these technical signals for {ticker}:
            {signals_text}
            
            Overall: {buy_signals} buy signals, {sell_signals} sell signals
            
            What's the best trading action? Give a 1-2 sentence recommendation."""
            
            ai_interpretation = await self.analyze(interpretation_query)
            
            return {
                "ticker": ticker.upper(),
                "signals": signals,
                "buy_signals": buy_signals,
                "sell_signals": sell_signals,
                "overall_recommendation": overall,
                "confidence": confidence,
                "ai_interpretation": ai_interpretation,
                "message": f"{ticker}: {buy_signals} buy / {sell_signals} sell signals - {overall} ({confidence} confidence)"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "error": str(e),
                "message": f"Error detecting signals: {str(e)}"
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
        """Test the Technical Analysis Agent"""
        print("Testing Technical Analysis Agent with Semantic Kernel...\n")
        
        # Create agent
        agent = TechnicalAnalysisAgentSK()
        
        # Test 1: Natural language query
        print("Test 1: Ask about RSI indicator")
        response = await agent.analyze("What is the RSI for AAPL and what does it tell us?")
        print(f"Response: {response}\n")
        
        # Test 2: Comprehensive ticker analysis
        print("Test 2: Analyze AAPL comprehensively")
        result = await agent.analyze_ticker("AAPL", include_volatility=True)
        print(f"SMA 20: {result.get('sma_20', {}).get('message')}")
        print(f"RSI: {result.get('rsi', {}).get('message')}")
        print(f"Crossover: {result.get('crossover', {}).get('message')}")
        print(f"Support/Resistance: {result.get('support_resistance', {}).get('message')}")
        if "ai_summary" in result:
            print(f"AI Summary: {result['ai_summary']}\n")
        
        # Test 3: Compare multiple tickers
        print("Test 3: Compare RSI across multiple stocks")
        comparison = await agent.compare_technical(["AAPL", "MSFT", "GOOGL"], metric="rsi")
        print(f"Results: {comparison.get('message', 'See results')}")
        if "comparison_summary" in comparison:
            print(f"AI Comparison: {comparison['comparison_summary']}\n")
        
        # Test 4: Detect trading signals
        print("Test 4: Detect trading signals for AAPL")
        signals = await agent.detect_signals("AAPL")
        print(f"Signals: {signals.get('message')}")
        if "ai_interpretation" in signals:
            print(f"AI Interpretation: {signals['ai_interpretation']}\n")
        
        print("✅ All tests completed!")
        
        # Cleanup
        await agent.close()
    
    # Run tests
    asyncio.run(test_agent())
