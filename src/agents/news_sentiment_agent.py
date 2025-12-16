"""Agent that surfaces financial news and sentiment signals."""

from typing import Any, Dict, Optional, Tuple

from src.agents.base_agent import BaseAgent
from src.agents.plugins.news_sentiment_plugin import NewsSentimentPlugin


class NewsSentimentAgent(BaseAgent):
    """Searches Redis-backed news corpus and summarizes sentiment."""

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
- get_news_sentiment: Summarize sentiment across articles
- get_ticker_news: Retrieve ticker-focused coverage
- analyze_news_impact: Gauge potential price reaction
- get_recent_news: Inspect freshest headlines

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
            tools=[],
        )
        self._plugin: Optional[NewsSentimentPlugin] = None

    @property
    def plugin(self) -> NewsSentimentPlugin:
        """Lazy-initialize the news sentiment plugin."""
        if self._plugin is None:
            self._plugin = NewsSentimentPlugin(self.redis)
        return self._plugin

    async def run(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Search for relevant headlines and synthesize sentiment for a topic."""
        context = context or {}
        query = context.get("query") or task
        ticker = context.get("ticker") or self._extract_ticker(task)
        days = int(context.get("days", 7))
        top_k = int(context.get("top_k", 5))

        if not query and not ticker:
            return {
                "status": "error",
                "message": "Provide a topic or ticker so I can search the news corpus.",
            }

        normalized_ticker = ticker.upper() if ticker else None
        cache_params = {
            "query": query,
            "ticker": normalized_ticker,
            "days": days,
            "top_k": top_k,
        }
        cached_payload = self.check_tool_cache("news_sentiment_summary", cache_params)
        if cached_payload:
            return {**cached_payload, "cache_hit": True}

        if normalized_ticker:
            articles_result, articles_cached = await self._get_ticker_news(normalized_ticker, top_k)
        else:
            articles_result, articles_cached = await self._search_news(query, top_k)

        sentiment_target = normalized_ticker or query
        sentiment_result, sentiment_cached = await self._get_sentiment_summary(sentiment_target, days)

        impact_result: Dict[str, Any] = {}
        impact_cached = False
        if normalized_ticker:
            impact_result, impact_cached = await self._analyze_impact(normalized_ticker, min(top_k, 10))

        summary = self._summarize(sentiment_target, articles_result, sentiment_result, impact_result)

        payload = {
            "status": "success",
            "query": query,
            "ticker": normalized_ticker,
            "days": days,
            "top_k": top_k,
            "articles": articles_result,
            "sentiment": sentiment_result,
            "impact": impact_result or None,
            "summary": summary,
            "cache_hit": articles_cached and sentiment_cached and (impact_cached if normalized_ticker else True),
        }

        self.cache_tool_output(
            "news_sentiment_summary",
            cache_params,
            payload,
            ttl=max(self.config.tool_cache_ttl, 1800),
        )
        return payload

    async def _search_news(self, query: str, limit: int) -> Tuple[Dict[str, Any], bool]:
        tool_name = "news_sentiment:search_news"
        params = {"query": query, "limit": limit}
        cached = self.check_tool_cache(tool_name, params)
        if cached:
            return cached, True

        result = await self.plugin.search_news(query, limit=limit)
        if result.get("success"):
            self.cache_tool_output(tool_name, params, result, ttl=1800)
        return result, False

    async def _get_ticker_news(self, ticker: str, limit: int) -> Tuple[Dict[str, Any], bool]:
        tool_name = "news_sentiment:get_ticker_news"
        params = {"ticker": ticker, "limit": limit}
        cached = self.check_tool_cache(tool_name, params)
        if cached:
            return cached, True

        result = await self.plugin.get_ticker_news(ticker, limit=limit)
        if result.get("success"):
            self.cache_tool_output(tool_name, params, result, ttl=1800)
        return result, False

    async def _get_sentiment_summary(self, topic: str, days: int) -> Tuple[Dict[str, Any], bool]:
        tool_name = "news_sentiment:get_news_sentiment"
        params = {"topic": topic, "days": days}
        cached = self.check_tool_cache(tool_name, params)
        if cached:
            return cached, True

        result = await self.plugin.get_news_sentiment(topic, days=days)
        if result.get("success"):
            self.cache_tool_output(tool_name, params, result, ttl=3600)
        return result, False

    async def _analyze_impact(self, ticker: str, limit: int) -> Tuple[Dict[str, Any], bool]:
        tool_name = "news_sentiment:analyze_news_impact"
        params = {"ticker": ticker, "limit": limit}
        cached = self.check_tool_cache(tool_name, params)
        if cached:
            return cached, True

        result = await self.plugin.analyze_news_impact(ticker, limit=limit)
        if result.get("success"):
            self.cache_tool_output(tool_name, params, result, ttl=3600)
        return result, False

    @staticmethod
    def _extract_ticker(query: str) -> Optional[str]:
        import re

        patterns = [
            r"\$([A-Z]{1,5})\b",
            r"(?:ticker|symbol)\s+([A-Z]{1,5})\b",
            r"\b([A-Z]{2,5})\b",
        ]

        upper_query = query.upper()
        for pattern in patterns:
            match = re.search(pattern, upper_query)
            if match:
                return match.group(1)

        return None

    @staticmethod
    def _summarize(
        target: str,
        articles: Dict[str, Any],
        sentiment: Dict[str, Any],
        impact: Optional[Dict[str, Any]],
    ) -> str:
        """Create brief digest of findings across news calls."""
        parts = []

        if articles.get("success"):
            count = articles.get("count", 0)
            parts.append(f"{count} articles located for {target}")
        else:
            error_msg = articles.get("message") or articles.get("error")
            if error_msg:
                parts.append(error_msg)

        if sentiment.get("success"):
            overall = sentiment.get("overall_sentiment", "neutral")
            distribution = sentiment.get("sentiment_percentages", {})
            pos = distribution.get("positive")
            neg = distribution.get("negative")
            if pos is not None and neg is not None:
                parts.append(f"Sentiment: {overall} ({pos}% positive vs {neg}% negative)")
            else:
                parts.append(f"Sentiment: {overall}")
        elif sentiment.get("message"):
            parts.append(sentiment.get("message"))

        if impact and impact.get("success"):
            parts.append(impact.get("message", "Impact analysis available."))
        elif impact and impact.get("message"):
            parts.append(impact.get("message"))

        return " | ".join(parts) if parts else f"No news data available for {target}."
