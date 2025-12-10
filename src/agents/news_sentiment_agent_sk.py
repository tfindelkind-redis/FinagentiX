"""
News Sentiment Agent using Semantic Kernel
Migrated from BaseAgent to ChatCompletionAgent
"""

import asyncio
from typing import Dict, Any, Optional, List
from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.contents import ChatMessageContent, AuthorRole
import redis

from sk_config import get_global_config
from plugins.news_sentiment_plugin import NewsSentimentPlugin


class NewsSentimentAgentSK:
    """
    News Sentiment Agent powered by Semantic Kernel
    
    Analyzes news sentiment, market impact, and provides insights based on
    news articles from Redis with RediSearch and Azure OpenAI GPT-4.
    
    Capabilities:
    - Search and retrieve relevant news articles
    - Analyze sentiment from news data
    - Assess potential market impact
    - Track sentiment trends over time
    - Provide actionable insights
    """
    
    def __init__(
        self,
        kernel: Optional[Kernel] = None,
        redis_client: Optional[redis.Redis] = None
    ):
        """
        Initialize News Sentiment Agent
        
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
        
        # Create News Sentiment Plugin
        self.plugin = NewsSentimentPlugin(self.redis_client)
        
        # Agent instructions
        instructions = """You are a News Sentiment Agent specializing in financial news analysis and market sentiment.

Your capabilities:
1. Search and retrieve relevant news articles from multiple sources
2. Analyze sentiment (positive, negative, neutral) from news content
3. Assess potential market impact from news events
4. Identify sentiment trends and shifts
5. Provide actionable insights for investment decisions

When responding:
- Always cite specific news sources and headlines
- Quantify sentiment with percentages and distributions
- Explain potential market impact clearly
- Consider both short-term reactions and long-term implications
- Highlight any significant sentiment shifts or unusual patterns
- Provide balanced analysis considering multiple viewpoints

Available tools:
- search_news: Find relevant news articles by query
- get_ticker_news: Get news specific to a stock ticker
- get_recent_news: Retrieve most recent news articles
- get_news_sentiment: Analyze overall sentiment for a topic
- analyze_news_impact: Assess potential market impact

Always use the appropriate tool to get real news data before responding. Never fabricate news or sentiment data."""
        
        # Create agent with kernel and plugins
        self.agent = ChatCompletionAgent(
            kernel=self.kernel,
            name="NewsSentimentAgent",
            instructions=instructions,
            plugins=[self.plugin]
        )
    
    async def analyze(self, query: str) -> str:
        """
        Analyze a news/sentiment query
        
        Args:
            query: Natural language query about news or sentiment
        
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
    
    async def analyze_ticker_sentiment(
        self,
        ticker: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Comprehensive sentiment analysis for a ticker
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to analyze (default: 7)
        
        Returns:
            Dictionary with comprehensive sentiment analysis
        """
        try:
            # Get ticker news
            news_result = await self.plugin.get_ticker_news(ticker, limit=10)
            
            # Get sentiment analysis
            sentiment_result = await self.plugin.get_news_sentiment(ticker, days=days)
            
            # Get impact analysis
            impact_result = await self.plugin.analyze_news_impact(ticker, limit=5)
            
            # Compile analysis
            analysis = {
                "ticker": ticker.upper(),
                "days": days,
                "news": news_result,
                "sentiment": sentiment_result,
                "impact": impact_result,
                "success": all([
                    news_result.get("success"),
                    sentiment_result.get("success"),
                    impact_result.get("success")
                ])
            }
            
            # Generate AI summary if data available
            if analysis["success"]:
                summary_query = f"""Provide a comprehensive sentiment analysis for {ticker.upper()} based on this data:

News Articles: {news_result['count']} articles found
Sentiment Distribution: {sentiment_result.get('sentiment_percentages')}
Overall Sentiment: {sentiment_result.get('overall_sentiment')}
Impact Level: {impact_result.get('impact_level')}
Recommendation: {impact_result.get('recommendation')}

Key Headlines:
{chr(10).join(['- ' + h for h in impact_result.get('key_headlines', [])[:3]])}

Provide 3-4 sentences summarizing the sentiment analysis and potential investment implications."""
                
                analysis["ai_summary"] = await self.analyze(summary_query)
            
            return analysis
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "success": False,
                "error": str(e)
            }
    
    async def compare_sentiment(
        self,
        tickers: List[str],
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Compare sentiment across multiple tickers
        
        Args:
            tickers: List of ticker symbols to compare
            days: Number of days for analysis
        
        Returns:
            Dictionary with comparative sentiment analysis
        """
        try:
            # Get sentiment for each ticker
            ticker_sentiments = []
            for ticker in tickers:
                sentiment = await self.plugin.get_news_sentiment(ticker, days=days)
                if sentiment.get("success"):
                    ticker_sentiments.append({
                        "ticker": ticker.upper(),
                        "overall_sentiment": sentiment.get("overall_sentiment"),
                        "positive_pct": sentiment.get("sentiment_percentages", {}).get("positive", 0),
                        "negative_pct": sentiment.get("sentiment_percentages", {}).get("negative", 0),
                        "articles": sentiment.get("articles_analyzed", 0)
                    })
            
            if not ticker_sentiments:
                return {
                    "tickers": tickers,
                    "success": False,
                    "error": "No sentiment data available for any tickers"
                }
            
            # Sort by positive sentiment
            ticker_sentiments.sort(key=lambda x: x["positive_pct"], reverse=True)
            
            # Generate comparison using agent
            comparison_query = f"""Compare sentiment across these {len(ticker_sentiments)} stocks:

""" + "\n".join([
                f"{s['ticker']}: {s['overall_sentiment']} ({s['positive_pct']:.0f}% positive, {s['negative_pct']:.0f}% negative) - {s['articles']} articles"
                for s in ticker_sentiments
            ]) + """

Provide a brief 2-3 sentence comparison highlighting which stocks have the most positive/negative sentiment and any notable differences."""
            
            summary = await self.analyze(comparison_query)
            
            return {
                "tickers": tickers,
                "days": days,
                "sentiments": ticker_sentiments,
                "most_positive": ticker_sentiments[0],
                "most_negative": ticker_sentiments[-1],
                "comparison_summary": summary,
                "success": True
            }
            
        except Exception as e:
            return {
                "tickers": tickers,
                "success": False,
                "error": str(e)
            }
    
    async def monitor_sentiment_shift(
        self,
        ticker: str,
        threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        Monitor for significant sentiment shifts
        
        Args:
            ticker: Stock ticker symbol
            threshold: Threshold for significant shift (default: 0.3 = 30%)
        
        Returns:
            Dictionary with shift analysis
        """
        try:
            # Get recent sentiment
            recent_sentiment = await self.plugin.get_news_sentiment(ticker, days=3)
            
            # Get longer-term sentiment
            historical_sentiment = await self.plugin.get_news_sentiment(ticker, days=14)
            
            if not recent_sentiment.get("success") or not historical_sentiment.get("success"):
                return {
                    "ticker": ticker.upper(),
                    "success": False,
                    "error": "Insufficient data to detect shifts"
                }
            
            # Calculate shift
            recent_pos = recent_sentiment["sentiment_percentages"]["positive"]
            hist_pos = historical_sentiment["sentiment_percentages"]["positive"]
            shift = recent_pos - hist_pos
            
            # Determine if significant
            is_significant = abs(shift) >= (threshold * 100)
            
            if is_significant:
                if shift > 0:
                    direction = "positive"
                    interpretation = "improving sentiment"
                else:
                    direction = "negative"
                    interpretation = "deteriorating sentiment"
            else:
                direction = "stable"
                interpretation = "relatively stable sentiment"
            
            return {
                "ticker": ticker.upper(),
                "recent_positive": round(recent_pos, 1),
                "historical_positive": round(hist_pos, 1),
                "shift_percentage": round(shift, 1),
                "is_significant": is_significant,
                "direction": direction,
                "interpretation": interpretation,
                "success": True,
                "message": f"{ticker.upper()}: {interpretation} (shift of {shift:+.1f}%)"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "success": False,
                "error": str(e)
            }
    
    def close(self):
        """Clean up resources"""
        if self.redis_client:
            self.redis_client.close()


# Example usage and testing
async def test_agent():
    """Test the News Sentiment Agent"""
    print("Testing News Sentiment Agent with Semantic Kernel\n")
    print("=" * 60)
    
    # Create agent
    agent = NewsSentimentAgentSK()
    
    # Test 1: Natural language query
    print("\nTest 1: Natural language query")
    print("-" * 60)
    query = "What is the current sentiment around technology stocks?"
    print(f"Query: {query}\n")
    result = await agent.analyze(query)
    print(f"Response: {result[:300]}...\n")
    
    # Test 2: Comprehensive ticker sentiment
    print("\nTest 2: Comprehensive ticker sentiment analysis")
    print("-" * 60)
    analysis = await agent.analyze_ticker_sentiment("AAPL", days=7)
    if analysis.get("success"):
        print(f"Ticker: {analysis['ticker']}")
        print(f"News: {analysis['news']['count']} articles")
        sentiment = analysis.get("sentiment", {})
        if sentiment.get("success"):
            print(f"Sentiment: {sentiment.get('overall_sentiment')}")
            print(f"Distribution: {sentiment.get('sentiment_percentages')}")
        impact = analysis.get("impact", {})
        if impact.get("success"):
            print(f"Impact: {impact.get('impact_level')}")
        if "ai_summary" in analysis:
            print(f"\nAI Summary: {analysis['ai_summary'][:200]}...")
    else:
        print(f"Limited data: {analysis.get('error', 'No AAPL news available')}")
    print()
    
    # Test 3: Compare sentiment
    print("\nTest 3: Compare sentiment across tickers")
    print("-" * 60)
    comparison = await agent.compare_sentiment(["AAPL", "MSFT", "GOOGL"], days=7)
    if comparison.get("success"):
        print(f"Tickers analyzed: {len(comparison['sentiments'])}")
        if comparison['sentiments']:
            print(f"Most positive: {comparison['most_positive']['ticker']}")
            print(f"Most negative: {comparison['most_negative']['ticker']}")
            print(f"\nComparison: {comparison['comparison_summary'][:200]}...")
    else:
        print(f"Limited data: {comparison.get('error')}")
    print()
    
    # Test 4: Monitor sentiment shift
    print("\nTest 4: Monitor sentiment shift")
    print("-" * 60)
    shift = await agent.monitor_sentiment_shift("AAPL", threshold=0.2)
    if shift.get("success"):
        print(f"Message: {shift['message']}")
        print(f"Recent: {shift['recent_positive']}% positive")
        print(f"Historical: {shift['historical_positive']}% positive")
        print(f"Shift: {shift['shift_percentage']:+.1f}%")
        print(f"Significant: {shift['is_significant']}")
    else:
        print(f"Unable to detect shift: {shift.get('error')}")
    
    # Cleanup
    agent.close()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_agent())
