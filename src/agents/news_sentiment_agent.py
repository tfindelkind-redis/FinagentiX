"""
News Sentiment Agent - Searches news and analyzes sentiment.

This agent:
- Searches news articles using Redis vector search
- Analyzes sentiment using Azure OpenAI
- Tracks sentiment trends over time
- Identifies key topics and entities
"""

from typing import Dict, List, Optional, Any
from src.agents.base_agent import BaseAgent


class NewsSentimentAgent(BaseAgent):
    """
    Specialized agent for news search and sentiment analysis.
    
    Uses Redis vector search to find relevant news articles and
    Azure OpenAI for sentiment classification.
    """
    
    def __init__(self):
        instructions = """You are the News Sentiment Agent for FinagentiX.

Your responsibilities:
1. Search news articles about specific stocks or topics using vector search
2. Analyze sentiment (positive, negative, neutral) of news content
3. Extract key topics, entities, and events from articles
4. Identify sentiment trends over time periods
5. Correlate news sentiment with price movements

Available tools:
- search_news: Vector search for relevant news articles
- analyze_sentiment: Classify sentiment of text
- extract_entities: Extract companies, people, events from text
- get_sentiment_trend: Calculate sentiment over time

Search criteria:
- Ticker symbols
- Company names
- Industry sectors
- Time ranges
- Sentiment polarity

Always:
- Return top K most relevant articles
- Include publication dates
- Provide sentiment scores with confidence
- Cite sources properly
"""
        
        super().__init__(
            name="news_sentiment",
            instructions=instructions,
            tools=[]  # Will be populated with vector and sentiment tools in Phase 5.3
        )
    
    async def run(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute news search and sentiment analysis.
        
        Args:
            task: Query about news or sentiment
            context: Optional ticker, date range, sentiment filter
            
        Returns:
            Dict with news articles and sentiment analysis
        """
        ticker = context.get("ticker") if context else None
        top_k = context.get("top_k", 5) if context else 5
        
        # TODO Phase 5.3: Implement with vector search and sentiment tools
        
        return {
            "status": "success",
            "articles": [],
            "sentiment": {},
            "message": "News sentiment tools will be implemented in Phase 5.3"
        }
