"""
Unit tests for News Sentiment Plugin
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Add parent directory to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.agents.plugins.news_sentiment_plugin import NewsSentimentPlugin


@pytest.fixture
def mock_redis():
    """Create a mock Redis client"""
    mock = Mock()
    return mock


@pytest.fixture
def plugin(mock_redis):
    """Create a NewsSentimentPlugin with mocked dependencies"""
    return NewsSentimentPlugin(mock_redis)


class TestSearchNews:
    """Tests for search_news function"""
    
    @pytest.mark.asyncio
    async def test_search_news_success(self, plugin, mock_redis):
        """Test successful news search"""
        # Mock RediSearch response
        mock_redis.ft.return_value.search.return_value.docs = [
            Mock(
                ticker="AAPL",
                title="Apple announces new product",
                summary="Apple reveals innovative technology",
                date="2024-12-10",
                url="https://news.example.com/apple1",
                score=0.95
            ),
            Mock(
                ticker="AAPL",
                title="AAPL stock rises",
                summary="Apple stock sees gains",
                date="2024-12-09",
                url="https://news.example.com/apple2",
                score=0.88
            )
        ]
        
        result = await plugin.search_news("AAPL", limit=2)
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["ticker"] == "AAPL"
        assert result_dict["count"] == 2
        assert len(result_dict["articles"]) == 2
        assert result_dict["articles"][0]["title"] == "Apple announces new product"
        assert result_dict["articles"][0]["relevance_score"] == 0.95
    
    @pytest.mark.asyncio
    async def test_search_news_no_results(self, plugin, mock_redis):
        """Test news search with no results"""
        mock_redis.ft.return_value.search.return_value.docs = []
        
        result = await plugin.search_news("INVALID")
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["count"] == 0
        assert len(result_dict["articles"]) == 0
        assert "No news articles found" in result_dict["message"]
    
    @pytest.mark.asyncio
    async def test_search_news_max_results_limit(self, plugin, mock_redis):
        """Test max_results parameter"""
        # Create 10 mock articles
        mock_docs = [
            Mock(
                ticker="AAPL",
                title=f"Article {i}",
                summary=f"Summary {i}",
                date="2024-12-10",
                url=f"https://news.example.com/{i}",
                score=0.9 - (i * 0.05)
            )
            for i in range(10)
        ]
        mock_redis.ft.return_value.search.return_value.docs = mock_docs
        
        result = await plugin.search_news("AAPL", limit=5)
        result_dict = result
        
        assert result_dict["count"] == 5
        assert len(result_dict["articles"]) == 5
    
    @pytest.mark.asyncio
    async def test_search_news_uppercase_ticker(self, plugin, mock_redis):
        """Test ticker is converted to uppercase"""
        mock_redis.ft.return_value.search.return_value.docs = []
        
        await plugin.search_news("aapl")
        
        # Verify search was called with uppercase ticker
        call_args = mock_redis.ft.return_value.search.call_args
        assert "AAPL" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_search_news_error_handling(self, plugin, mock_redis):
        """Test error handling in news search"""
        mock_redis.ft.return_value.search.side_effect = Exception("Redis connection error")
        
        result = await plugin.search_news("AAPL")
        result_dict = result
        
        assert result_dict["success"] is False
        assert "error" in result_dict
        assert "Redis connection error" in result_dict["error"]


# TODO: Fix - plugin has get_news_sentiment, not analyze_sentiment
# TODO: Fix - plugin has get_news_sentiment, not analyze_sentiment
class TestAnalyzeSentiment:
    """Tests for analyze_sentiment function"""
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_positive(self, plugin):
        """Test positive sentiment analysis"""
        # Mock GPT-4o response
        mock_result = Mock()
        mock_result.value = json.dumps({
            "sentiment": "positive",
            "score": 0.85,
            "confidence": "high",
            "reasoning": "Article contains optimistic language and positive outlook"
        })        
        text = "Apple stock soars on strong earnings report"
        result = await plugin.analyze_sentiment(text)
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["sentiment"] == "positive"
        assert result_dict["score"] == 0.85
        assert result_dict["confidence"] == "high"
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_negative(self, plugin):
        """Test negative sentiment analysis"""
        mock_result = Mock()
        mock_result.value = json.dumps({
            "sentiment": "negative",
            "score": -0.75,
            "confidence": "high",
            "reasoning": "Article discusses concerns and challenges"
        })        
        text = "Apple faces supply chain disruptions and delays"
        result = await plugin.analyze_sentiment(text)
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["sentiment"] == "negative"
        assert result_dict["score"] == -0.75
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_neutral(self, plugin):
        """Test neutral sentiment analysis"""
        mock_result = Mock()
        mock_result.value = json.dumps({
            "sentiment": "neutral",
            "score": 0.05,
            "confidence": "moderate",
            "reasoning": "Article is factual without strong positive or negative tone"
        })        
        text = "Apple releases quarterly financial statements"
        result = await plugin.analyze_sentiment(text)
        result_dict = result
        
        assert result_dict["sentiment"] == "neutral"
        assert abs(result_dict["score"]) < 0.3
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_empty_text(self, plugin):
        """Test sentiment analysis with empty text"""
        result = await plugin.analyze_sentiment("")
        result_dict = result
        
        assert result_dict["success"] is False
        assert "error" in result_dict
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_error_handling(self, plugin):
        """Test error handling in sentiment analysis"""        
        result = await plugin.analyze_sentiment("Some text")
        result_dict = result
        
        assert result_dict["success"] is False
        assert "error" in result_dict


class TestGetSentimentSummary:
    """Tests for get_sentiment_summary function"""
    
    @pytest.mark.asyncio
    async def test_sentiment_summary_positive_majority(self, plugin, mock_redis):
        """Test sentiment summary with mostly positive articles"""
        mock_docs = [
            Mock(ticker="AAPL", title=f"Article {i}", summary=f"Summary {i}", 
                 date="2024-12-10", url=f"url{i}", score=0.9)
            for i in range(5)
        ]
        mock_redis.ft.return_value.search.return_value.docs = mock_docs
        
        # Mock sentiment analysis results (4 positive, 1 neutral)
        with patch.object(plugin, 'analyze_sentiment') as mock_analyze:
            mock_analyze.side_effect = [
                json.dumps({"success": True, "sentiment": "positive", "score": 0.8}),
                json.dumps({"success": True, "sentiment": "positive", "score": 0.7}),
                json.dumps({"success": True, "sentiment": "positive", "score": 0.9}),
                json.dumps({"success": True, "sentiment": "positive", "score": 0.6}),
                json.dumps({"success": True, "sentiment": "neutral", "score": 0.1})
            ]
            
            result = await plugin.get_sentiment_summary("AAPL", days=7)
            result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["ticker"] == "AAPL"
        assert result_dict["total_articles"] == 5
        assert result_dict["positive_count"] == 4
        assert result_dict["neutral_count"] == 1
        assert result_dict["negative_count"] == 0
        assert result_dict["overall_sentiment"] == "positive"
        assert result_dict["sentiment_percentage"] == 80.0  # 4/5 = 80%
    
    @pytest.mark.asyncio
    async def test_sentiment_summary_mixed(self, plugin, mock_redis):
        """Test sentiment summary with mixed sentiments"""
        mock_docs = [Mock(ticker="AAPL", title=f"Article {i}", summary=f"Summary {i}", 
                         date="2024-12-10", url=f"url{i}", score=0.9) for i in range(6)]
        mock_redis.ft.return_value.search.return_value.docs = mock_docs
        
        with patch.object(plugin, 'analyze_sentiment') as mock_analyze:
            mock_analyze.side_effect = [
                json.dumps({"success": True, "sentiment": "positive", "score": 0.7}),
                json.dumps({"success": True, "sentiment": "positive", "score": 0.6}),
                json.dumps({"success": True, "sentiment": "negative", "score": -0.8}),
                json.dumps({"success": True, "sentiment": "negative", "score": -0.7}),
                json.dumps({"success": True, "sentiment": "neutral", "score": 0.1}),
                json.dumps({"success": True, "sentiment": "neutral", "score": -0.05})
            ]
            
            result = await plugin.get_sentiment_summary("AAPL", days=7)
            result_dict = result
        
        assert result_dict["positive_count"] == 2
        assert result_dict["negative_count"] == 2
        assert result_dict["neutral_count"] == 2
        assert result_dict["overall_sentiment"] == "neutral"  # Mixed, no clear majority
    
    @pytest.mark.asyncio
    async def test_sentiment_summary_no_articles(self, plugin, mock_redis):
        """Test sentiment summary with no articles"""
        mock_redis.ft.return_value.search.return_value.docs = []
        
        result = await plugin.get_sentiment_summary("INVALID")
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["total_articles"] == 0
        assert result_dict["overall_sentiment"] == "neutral"


class TestGetTrendingTopics:
    """Tests for get_trending_topics function"""
    
    @pytest.mark.asyncio
    async def test_trending_topics_success(self, plugin, mock_redis):
        """Test successful trending topics extraction"""
        mock_docs = [
            Mock(ticker="AAPL", title="Apple iPhone 15 release", 
                 summary="New iPhone features AI technology", 
                 date="2024-12-10", url="url1", score=0.9),
            Mock(ticker="AAPL", title="Apple AI advancements", 
                 summary="Apple integrates AI into products", 
                 date="2024-12-10", url="url2", score=0.85),
            Mock(ticker="AAPL", title="iPhone sales surge", 
                 summary="Strong iPhone demand continues", 
                 date="2024-12-09", url="url3", score=0.8)
        ]
        mock_redis.ft.return_value.search.return_value.docs = mock_docs
        
        result = await plugin.get_trending_topics("AAPL", max_topics=5)
        result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["ticker"] == "AAPL"
        assert len(result_dict["topics"]) > 0
        
        # Check that common words like "iPhone" and "AI" appear
        topics = [t["topic"].lower() for t in result_dict["topics"]]
        assert any("iphone" in t or "ai" in t for t in topics)
    
    @pytest.mark.asyncio
    async def test_trending_topics_frequency_ranking(self, plugin, mock_redis):
        """Test topics are ranked by frequency"""
        mock_docs = [
            Mock(ticker="AAPL", title=f"earnings report quarter {i}", 
                 summary=f"earnings analysis {i}", 
                 date="2024-12-10", url=f"url{i}", score=0.9)
            for i in range(5)
        ]
        mock_redis.ft.return_value.search.return_value.docs = mock_docs
        
        result = await plugin.get_trending_topics("AAPL")
        result_dict = result
        
        # "earnings" should appear frequently and be highly ranked
        topics = result_dict["topics"]
        assert any("earnings" in t["topic"].lower() for t in topics)
        
        # Topics should be sorted by frequency
        if len(topics) > 1:
            assert topics[0]["count"] >= topics[1]["count"]
    
    @pytest.mark.asyncio
    async def test_trending_topics_max_topics_limit(self, plugin, mock_redis):
        """Test max_topics parameter limits results"""
        mock_docs = [
            Mock(ticker="AAPL", title=f"Different topic {i} news", 
                 summary=f"Topic {i} analysis", 
                 date="2024-12-10", url=f"url{i}", score=0.9)
            for i in range(10)
        ]
        mock_redis.ft.return_value.search.return_value.docs = mock_docs
        
        result = await plugin.get_trending_topics("AAPL", max_topics=3)
        result_dict = result
        
        assert len(result_dict["topics"]) <= 3


class TestGetSentimentTimeline:
    """Tests for get_sentiment_timeline function"""
    
    @pytest.mark.asyncio
    async def test_sentiment_timeline_success(self, plugin, mock_redis):
        """Test sentiment timeline generation"""
        # Create mock articles across different dates
        mock_docs = [
            Mock(ticker="AAPL", title="Article 1", summary="Positive news 1", 
                 date="2024-12-10", url="url1", score=0.9),
            Mock(ticker="AAPL", title="Article 2", summary="Positive news 2", 
                 date="2024-12-10", url="url2", score=0.88),
            Mock(ticker="AAPL", title="Article 3", summary="Negative news", 
                 date="2024-12-09", url="url3", score=0.85),
            Mock(ticker="AAPL", title="Article 4", summary="Neutral news", 
                 date="2024-12-08", url="url4", score=0.82)
        ]
        mock_redis.ft.return_value.search.return_value.docs = mock_docs
        
        with patch.object(plugin, 'analyze_sentiment') as mock_analyze:
            mock_analyze.side_effect = [
                json.dumps({"success": True, "sentiment": "positive", "score": 0.8}),
                json.dumps({"success": True, "sentiment": "positive", "score": 0.7}),
                json.dumps({"success": True, "sentiment": "negative", "score": -0.6}),
                json.dumps({"success": True, "sentiment": "neutral", "score": 0.1})
            ]
            
            result = await plugin.get_sentiment_timeline("AAPL", days=7)
            result_dict = result
        
        assert result_dict["success"] is True
        assert result_dict["ticker"] == "AAPL"
        assert len(result_dict["timeline"]) > 0
        
        # Verify timeline structure
        for day_data in result_dict["timeline"]:
            assert "date" in day_data
            assert "articles_count" in day_data
            assert "average_sentiment" in day_data
            assert "sentiment_label" in day_data
    
    @pytest.mark.asyncio
    async def test_sentiment_timeline_trend_detection(self, plugin, mock_redis):
        """Test trend detection in sentiment timeline"""
        # Create articles showing improving sentiment over time
        mock_docs = [
            Mock(ticker="AAPL", title=f"Article {i}", summary=f"News {i}", 
                 date=f"2024-12-{10-i:02d}", url=f"url{i}", score=0.9)
            for i in range(5)
        ]
        mock_redis.ft.return_value.search.return_value.docs = mock_docs
        
        with patch.object(plugin, 'analyze_sentiment') as mock_analyze:
            # Sentiment improves: -0.5, -0.2, 0.1, 0.4, 0.7
            mock_analyze.side_effect = [
                json.dumps({"success": True, "sentiment": "negative", "score": -0.5}),
                json.dumps({"success": True, "sentiment": "negative", "score": -0.2}),
                json.dumps({"success": True, "sentiment": "neutral", "score": 0.1}),
                json.dumps({"success": True, "sentiment": "positive", "score": 0.4}),
                json.dumps({"success": True, "sentiment": "positive", "score": 0.7})
            ]
            
            result = await plugin.get_sentiment_timeline("AAPL", days=7)
            result_dict = result
        
        assert "trend" in result_dict
        assert result_dict["trend"] in ["improving", "declining", "stable"]
    
    @pytest.mark.asyncio
    async def test_sentiment_timeline_no_data(self, plugin, mock_redis):
        """Test sentiment timeline with no articles"""
        mock_redis.ft.return_value.search.return_value.docs = []
        
        result = await plugin.get_sentiment_timeline("INVALID")
        result_dict = result
        
        assert result_dict["success"] is True
        assert len(result_dict["timeline"]) == 0
        assert result_dict["trend"] == "no_data"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
