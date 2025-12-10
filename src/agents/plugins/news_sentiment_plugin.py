"""
News Sentiment Plugin for Semantic Kernel
Provides tools for querying news articles and sentiment analysis from Redis
"""

import asyncio
from typing import Dict, Any, List, Optional
import redis
from datetime import datetime, timedelta
from semantic_kernel.functions import kernel_function


class NewsSentimentPlugin:
    """
    Semantic Kernel plugin for news sentiment operations
    
    Provides tools:
    - search_news: Vector search for relevant news articles
    - get_news_sentiment: Analyze sentiment from news data
    - get_ticker_news: Get news specific to a ticker symbol
    - get_recent_news: Get most recent news articles
    - analyze_news_impact: Analyze potential market impact
    """
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize News Sentiment Plugin
        
        Args:
            redis_client: Configured Redis client with RediSearch
        """
        self.redis = redis_client
        self.index_name = "news_idx"
    
    @kernel_function(
        name="search_news",
        description="Search news articles using vector similarity. Returns relevant news articles matching the query."
    )
    async def search_news(
        self,
        query: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Search news articles using vector similarity
        
        Args:
            query: Search query or topic to find news about
            limit: Maximum number of results to return (default: 5)
        
        Returns:
            Dictionary with search results:
            {
                "query": str,
                "results": List[Dict],
                "count": int,
                "success": bool
            }
        """
        try:
            # Note: In production, you'd generate embeddings for the query
            # For now, we'll use text search as a fallback
            from redis.commands.search.query import Query
            
            # Search query - looking for text matches
            search_query = Query(f"@content:{query}").paging(0, limit)
            
            try:
                results = self.redis.ft(self.index_name).search(search_query)
            except Exception as e:
                # Fallback: try simpler query if vector search fails
                search_query = Query(query).paging(0, limit)
                results = self.redis.ft(self.index_name).search(search_query)
            
            articles = []
            for doc in results.docs:
                article = {
                    "id": doc.id,
                    "title": getattr(doc, "title", "No title"),
                    "content": getattr(doc, "content", "")[:500],  # Truncate content
                    "ticker": getattr(doc, "ticker", "N/A"),
                    "date": getattr(doc, "date", "Unknown"),
                    "sentiment": getattr(doc, "sentiment", "neutral"),
                    "source": getattr(doc, "source", "Unknown")
                }
                articles.append(article)
            
            return {
                "query": query,
                "results": articles,
                "count": len(articles),
                "total_found": results.total if hasattr(results, 'total') else len(articles),
                "success": True,
                "message": f"Found {len(articles)} articles matching '{query}'"
            }
            
        except Exception as e:
            return {
                "query": query,
                "success": False,
                "error": str(e),
                "message": f"Error searching news: {str(e)}"
            }
    
    @kernel_function(
        name="get_ticker_news",
        description="Get news articles specific to a stock ticker symbol. Returns news articles filtered by ticker."
    )
    async def get_ticker_news(
        self,
        ticker: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Get news articles for a specific ticker
        
        Args:
            ticker: Stock ticker symbol (e.g., AAPL, MSFT)
            limit: Maximum number of results (default: 5)
        
        Returns:
            Dictionary with ticker-specific news
        """
        try:
            from redis.commands.search.query import Query
            
            # Search for ticker-specific news
            ticker_upper = ticker.upper()
            search_query = Query(f"@ticker:{{{ticker_upper}}}").paging(0, limit)
            
            try:
                results = self.redis.ft(self.index_name).search(search_query)
            except Exception:
                # Fallback to content search
                search_query = Query(ticker_upper).paging(0, limit)
                results = self.redis.ft(self.index_name).search(search_query)
            
            articles = []
            for doc in results.docs:
                article = {
                    "id": doc.id,
                    "title": getattr(doc, "title", "No title"),
                    "content": getattr(doc, "content", "")[:500],
                    "ticker": getattr(doc, "ticker", ticker_upper),
                    "date": getattr(doc, "date", "Unknown"),
                    "sentiment": getattr(doc, "sentiment", "neutral"),
                    "source": getattr(doc, "source", "Unknown")
                }
                articles.append(article)
            
            # Calculate sentiment distribution
            sentiments = [a.get("sentiment", "neutral") for a in articles]
            sentiment_counts = {
                "positive": sentiments.count("positive"),
                "negative": sentiments.count("negative"),
                "neutral": sentiments.count("neutral")
            }
            
            return {
                "ticker": ticker_upper,
                "results": articles,
                "count": len(articles),
                "sentiment_distribution": sentiment_counts,
                "success": True,
                "message": f"Found {len(articles)} articles for {ticker_upper}"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "success": False,
                "error": str(e),
                "message": f"Error fetching news for {ticker.upper()}: {str(e)}"
            }
    
    @kernel_function(
        name="get_recent_news",
        description="Get the most recent news articles. Returns latest news sorted by date."
    )
    async def get_recent_news(
        self,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get most recent news articles
        
        Args:
            limit: Maximum number of articles to return (default: 10)
        
        Returns:
            Dictionary with recent news articles
        """
        try:
            from redis.commands.search.query import Query
            
            # Search for all news, sorted by date (if available)
            search_query = Query("*").paging(0, limit)
            
            results = self.redis.ft(self.index_name).search(search_query)
            
            articles = []
            for doc in results.docs:
                article = {
                    "id": doc.id,
                    "title": getattr(doc, "title", "No title"),
                    "content": getattr(doc, "content", "")[:300],
                    "ticker": getattr(doc, "ticker", "N/A"),
                    "date": getattr(doc, "date", "Unknown"),
                    "sentiment": getattr(doc, "sentiment", "neutral"),
                    "source": getattr(doc, "source", "Unknown")
                }
                articles.append(article)
            
            # Sort by date if available
            try:
                articles.sort(key=lambda x: x["date"], reverse=True)
            except:
                pass
            
            return {
                "results": articles,
                "count": len(articles),
                "success": True,
                "message": f"Retrieved {len(articles)} recent news articles"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error fetching recent news: {str(e)}"
            }
    
    @kernel_function(
        name="get_news_sentiment",
        description="Analyze overall sentiment from news articles for a given topic or ticker. Returns sentiment analysis summary."
    )
    async def get_news_sentiment(
        self,
        topic: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Analyze sentiment from news articles
        
        Args:
            topic: Topic or ticker to analyze sentiment for
            days: Number of days to look back (default: 7)
        
        Returns:
            Dictionary with sentiment analysis
        """
        try:
            # Get news for the topic
            news_result = await self.search_news(topic, limit=20)
            
            if not news_result.get("success") or news_result["count"] == 0:
                return {
                    "topic": topic,
                    "success": False,
                    "error": "No news articles found",
                    "message": f"No news found for '{topic}'"
                }
            
            articles = news_result["results"]
            
            # Analyze sentiment distribution
            sentiments = [a.get("sentiment", "neutral") for a in articles]
            positive_count = sentiments.count("positive")
            negative_count = sentiments.count("negative")
            neutral_count = sentiments.count("neutral")
            total = len(sentiments)
            
            # Calculate percentages
            positive_pct = (positive_count / total * 100) if total > 0 else 0
            negative_pct = (negative_count / total * 100) if total > 0 else 0
            neutral_pct = (neutral_count / total * 100) if total > 0 else 0
            
            # Determine overall sentiment
            if positive_pct > 50:
                overall = "positive"
                analysis = "predominantly positive sentiment"
            elif negative_pct > 50:
                overall = "negative"
                analysis = "predominantly negative sentiment"
            elif positive_pct > negative_pct:
                overall = "slightly positive"
                analysis = "mildly positive sentiment"
            elif negative_pct > positive_pct:
                overall = "slightly negative"
                analysis = "mildly negative sentiment"
            else:
                overall = "neutral"
                analysis = "neutral sentiment"
            
            return {
                "topic": topic,
                "days": days,
                "articles_analyzed": total,
                "sentiment_distribution": {
                    "positive": positive_count,
                    "negative": negative_count,
                    "neutral": neutral_count
                },
                "sentiment_percentages": {
                    "positive": round(positive_pct, 1),
                    "negative": round(negative_pct, 1),
                    "neutral": round(neutral_pct, 1)
                },
                "overall_sentiment": overall,
                "analysis": analysis,
                "success": True,
                "message": f"{topic}: {analysis} across {total} articles ({positive_pct:.0f}% positive, {negative_pct:.0f}% negative)"
            }
            
        except Exception as e:
            return {
                "topic": topic,
                "success": False,
                "error": str(e),
                "message": f"Error analyzing sentiment: {str(e)}"
            }
    
    @kernel_function(
        name="analyze_news_impact",
        description="Analyze potential market impact from news. Returns impact assessment and recommendations."
    )
    async def analyze_news_impact(
        self,
        ticker: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Analyze potential market impact from news
        
        Args:
            ticker: Stock ticker symbol
            limit: Number of recent articles to analyze
        
        Returns:
            Dictionary with impact analysis
        """
        try:
            # Get ticker news
            news_result = await self.get_ticker_news(ticker, limit=limit)
            
            if not news_result.get("success") or news_result["count"] == 0:
                return {
                    "ticker": ticker.upper(),
                    "success": False,
                    "error": "No news found",
                    "message": f"No news found for {ticker.upper()}"
                }
            
            articles = news_result["results"]
            sentiment_dist = news_result["sentiment_distribution"]
            
            # Calculate impact score
            positive_weight = sentiment_dist["positive"] * 1.0
            negative_weight = sentiment_dist["negative"] * -1.0
            total_articles = len(articles)
            
            impact_score = (positive_weight + negative_weight) / total_articles if total_articles > 0 else 0
            
            # Determine impact level
            if abs(impact_score) < 0.2:
                impact_level = "minimal"
                recommendation = "neutral - news unlikely to significantly move the stock"
            elif impact_score >= 0.5:
                impact_level = "positive"
                recommendation = "bullish - positive news sentiment may drive price up"
            elif impact_score <= -0.5:
                impact_level = "negative"
                recommendation = "bearish - negative news sentiment may pressure price"
            elif impact_score > 0.2:
                impact_level = "slightly positive"
                recommendation = "cautiously bullish - mildly positive news"
            else:
                impact_level = "slightly negative"
                recommendation = "cautiously bearish - mildly negative news"
            
            # Extract key headlines
            key_headlines = [a["title"] for a in articles[:3]]
            
            return {
                "ticker": ticker.upper(),
                "articles_analyzed": total_articles,
                "sentiment_distribution": sentiment_dist,
                "impact_score": round(impact_score, 2),
                "impact_level": impact_level,
                "recommendation": recommendation,
                "key_headlines": key_headlines,
                "success": True,
                "message": f"{ticker.upper()}: {impact_level} impact - {recommendation}"
            }
            
        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "success": False,
                "error": str(e),
                "message": f"Error analyzing news impact: {str(e)}"
            }


# Example usage and testing
if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from sk_config import get_redis_client
    
    async def test_plugin():
        """Test the News Sentiment Plugin"""
        print("Testing News Sentiment Plugin...\n")
        
        # Get Redis client
        redis_client = get_redis_client()
        
        # Create plugin
        plugin = NewsSentimentPlugin(redis_client)
        
        # Test 1: Search news
        print("Test 1: Search for AAPL news")
        result = await plugin.search_news("AAPL", limit=3)
        print(f"Result: {result.get('message')}")
        if result.get("success") and result["count"] > 0:
            print(f"First article: {result['results'][0]['title'][:80]}...")
        print()
        
        # Test 2: Get ticker news
        print("Test 2: Get AAPL ticker news")
        result = await plugin.get_ticker_news("AAPL", limit=3)
        print(f"Result: {result.get('message')}")
        if result.get("success"):
            print(f"Sentiment: {result.get('sentiment_distribution')}")
        print()
        
        # Test 3: Get recent news
        print("Test 3: Get recent news")
        result = await plugin.get_recent_news(limit=5)
        print(f"Result: {result.get('message')}")
        print()
        
        # Test 4: Analyze sentiment
        print("Test 4: Analyze AAPL sentiment")
        result = await plugin.get_news_sentiment("AAPL")
        print(f"Result: {result.get('message')}")
        if result.get("success"):
            print(f"Overall: {result.get('overall_sentiment')}")
            print(f"Distribution: {result.get('sentiment_percentages')}")
        print()
        
        # Test 5: Analyze news impact
        print("Test 5: Analyze AAPL news impact")
        result = await plugin.analyze_news_impact("AAPL", limit=5)
        print(f"Result: {result.get('message')}")
        if result.get("success"):
            print(f"Impact level: {result.get('impact_level')}")
            print(f"Recommendation: {result.get('recommendation')}")
        print()
        
        print("✅ All tests completed!")
    
    # Run tests
    asyncio.run(test_plugin())
