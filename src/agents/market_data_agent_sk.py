"""
Market Data Agent using Semantic Kernel
Migrated from BaseAgent to ChatCompletionAgent
"""

import asyncio
from typing import Dict, Any, Optional
from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.contents import ChatMessageContent, AuthorRole
import redis

from sk_config import get_global_config
from plugins.market_data_plugin import MarketDataPlugin


class MarketDataAgentSK:
    """
    Market Data Agent powered by Semantic Kernel
    
    Analyzes stock prices, technical indicators, and market trends using
    Redis TimeSeries data and Azure OpenAI GPT-4.
    
    Capabilities:
    - Current stock prices
    - Historical price analysis
    - Price change calculations
    - Multiple ticker comparison
    - Volume analysis
    """
    
    def __init__(
        self,
        kernel: Optional[Kernel] = None,
        redis_client: Optional[redis.Redis] = None
    ):
        """
        Initialize Market Data Agent
        
        Args:
            kernel: Semantic Kernel instance (created if None)
            redis_client: Redis client (created if None)
        """
        # Get configuration
        config = get_global_config()
        
        # Use provided or create kernel
        self.kernel = kernel or config.get_kernel()
        
        # Use provided or create Redis client
        self.redis_client = redis_client or config.get_redis_client()
        
        # Create Market Data Plugin
        self.plugin = MarketDataPlugin(self.redis_client)
        
        # Agent instructions
        instructions = """You are a Market Data Agent specializing in financial market analysis.

Your capabilities:
1. Retrieve current and historical stock prices
2. Calculate price changes and trends
3. Analyze trading volume patterns
4. Compare multiple securities
5. Provide technical market insights

When responding:
- Always include specific numbers and percentages
- Explain trends in context (e.g., "strong uptrend" vs "slight decline")
- Compare current values to historical averages when relevant
- Highlight significant volume changes
- Use clear, concise language for financial data

Available tools:
- get_stock_price: Get current price for a ticker
- get_price_history: Get historical price data with statistics
- get_price_change: Calculate price change over time period
- get_multiple_tickers: Get prices for multiple tickers at once
- get_volume_analysis: Analyze trading volume patterns

Always use the appropriate tool to get real data before responding. Never make up numbers."""
        
        # Create agent - use kernel and plugins approach
        self.agent = ChatCompletionAgent(
            kernel=self.kernel,
            name="MarketDataAgent",
            instructions=instructions,
            plugins=[self.plugin]
        )
    
    async def analyze(self, query: str) -> str:
        """
        Analyze a market data query
        
        Args:
            query: Natural language query about market data
        
        Returns:
            Analysis result as string
        """
        try:
            # Create chat history
            history = []
            
            # Add user query
            history.append(
                ChatMessageContent(
                    role=AuthorRole.USER,
                    content=query
                )
            )
            
            # Invoke agent
            async for message in self.agent.invoke(history):
                if message.role == AuthorRole.ASSISTANT:
                    return message.content
            
            return "No response generated"
            
        except Exception as e:
            return f"Error analyzing query: {str(e)}"
    
    async def analyze_ticker(self, ticker: str, days: int = 30) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a ticker
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to analyze (default: 30)
        
        Returns:
            Dictionary with comprehensive analysis
        """
        try:
            # Get current price
            current = await self.plugin.get_stock_price(ticker, "close")
            
            # Get price history and change
            history = await self.plugin.get_price_history(ticker, days=days)
            change = await self.plugin.get_price_change(ticker, days=days)
            
            # Get volume analysis
            volume = await self.plugin.get_volume_analysis(ticker, days=days)
            
            # Compile analysis
            analysis = {
                "ticker": ticker.upper(),
                "current_price": current,
                "history": history,
                "change": change,
                "volume": volume,
                "success": all([
                    current.get("success"),
                    history.get("success"),
                    change.get("success"),
                    volume.get("success")
                ])
            }
            
            # Generate summary using agent
            if analysis["success"]:
                summary_query = f"""Provide a brief market analysis summary for {ticker.upper()} based on this data:
                
Current Price: ${current.get('value'):.2f} as of {current.get('date')}
{days}-Day Change: {change.get('change_pct'):+.2f}% ({change.get('trend')})
Volume Trend: {volume.get('volume_trend_pct'):+.1f}% vs average ({volume.get('analysis')})

Provide 2-3 sentences summarizing the current market position and trend."""
                
                analysis["summary"] = await self.analyze(summary_query)
            
            return analysis
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "success": False,
                "error": str(e)
            }
    
    async def compare_tickers(self, tickers: list[str], days: int = 7) -> Dict[str, Any]:
        """
        Compare multiple tickers
        
        Args:
            tickers: List of ticker symbols
            days: Number of days for comparison (default: 7)
        
        Returns:
            Dictionary with comparison analysis
        """
        try:
            # Get data for all tickers
            ticker_data = []
            for ticker in tickers:
                change = await self.plugin.get_price_change(ticker, days=days)
                if change.get("success"):
                    ticker_data.append({
                        "ticker": ticker.upper(),
                        "start_price": change["start_price"],
                        "end_price": change["end_price"],
                        "change_pct": change["change_pct"],
                        "trend": change["trend"]
                    })
            
            if not ticker_data:
                return {
                    "tickers": tickers,
                    "success": False,
                    "error": "No data available for any tickers"
                }
            
            # Sort by performance
            ticker_data.sort(key=lambda x: x["change_pct"], reverse=True)
            
            # Generate comparison using agent
            comparison_query = f"""Compare these tickers based on their {days}-day performance:

""" + "\n".join([
                f"{data['ticker']}: {data['change_pct']:+.2f}% ({data['trend']}) - ${data['start_price']:.2f} → ${data['end_price']:.2f}"
                for data in ticker_data
            ]) + """

Provide a brief 2-3 sentence comparison highlighting the best and worst performers."""
            
            summary = await self.analyze(comparison_query)
            
            return {
                "tickers": tickers,
                "days": days,
                "data": ticker_data,
                "summary": summary,
                "best_performer": ticker_data[0],
                "worst_performer": ticker_data[-1],
                "success": True
            }
            
        except Exception as e:
            return {
                "tickers": tickers,
                "success": False,
                "error": str(e)
            }
    
    def close(self):
        """Clean up resources"""
        if self.redis_client:
            self.redis_client.close()


# Example usage and testing
async def test_agent():
    """Test the Market Data Agent"""
    print("Testing Market Data Agent with Semantic Kernel\n")
    print("=" * 60)
    
    # Create agent
    agent = MarketDataAgentSK()
    
    # Test 1: Natural language query
    print("\nTest 1: Natural language query")
    print("-" * 60)
    query = "What is the current price of AAPL and how has it changed over the last 7 days?"
    print(f"Query: {query}\n")
    result = await agent.analyze(query)
    print(f"Response: {result}\n")
    
    # Test 2: Comprehensive ticker analysis
    print("\nTest 2: Comprehensive ticker analysis")
    print("-" * 60)
    analysis = await agent.analyze_ticker("MSFT", days=30)
    if analysis.get("success"):
        print(f"Ticker: {analysis['ticker']}")
        print(f"Current: {analysis['current_price']['message']}")
        print(f"Change: {analysis['change']['message']}")
        print(f"Volume: {analysis['volume']['message']}")
        print(f"\nSummary: {analysis['summary']}\n")
    
    # Test 3: Compare multiple tickers
    print("\nTest 3: Compare multiple tickers")
    print("-" * 60)
    comparison = await agent.compare_tickers(["AAPL", "MSFT", "GOOGL"], days=7)
    if comparison.get("success"):
        print(f"Comparison ({comparison['days']} days):")
        for data in comparison["data"]:
            print(f"  {data['ticker']}: {data['change_pct']:+.2f}% ({data['trend']})")
        print(f"\nAnalysis: {comparison['summary']}\n")
    
    # Test 4: Volume analysis query
    print("\nTest 4: Volume analysis query")
    print("-" * 60)
    query = "Analyze the trading volume for AAPL over the past 30 days. Is it above or below average?"
    print(f"Query: {query}\n")
    result = await agent.analyze(query)
    print(f"Response: {result}\n")
    
    # Cleanup
    agent.close()
    
    print("=" * 60)
    print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_agent())
