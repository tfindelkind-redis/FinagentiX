"""Agent that retrieves market data and technical indicators."""

from typing import Any, Dict, Optional, Tuple

from src.agents.base_agent import BaseAgent
from src.agents.plugins.market_data_plugin import MarketDataPlugin


class MarketDataAgent(BaseAgent):
    """
    Specialized agent for stock market data and technical analysis.
    
    Uses Redis time series for efficient price data retrieval and
    caches computed technical indicators.
    """
    
    def __init__(self):
        instructions = """You are the Market Data Agent for FinagentiX.

Your responsibilities:
1. Fetch stock prices (current, historical, intraday)
2. Retrieve trading volume data
3. Calculate technical indicators:
   - Moving averages (SMA, EMA)
   - RSI (Relative Strength Index)
   - MACD (Moving Average Convergence Divergence)
   - Bollinger Bands
   - Support and resistance levels
4. Provide price change analysis (daily, weekly, monthly)

Available tools:
- get_stock_price: Fetch current or historical price
- get_trading_volume: Retrieve volume data
- get_technical_indicators: Calculate indicators from time series
- get_price_history: Get price series over time range

Always:
- Check tool cache before fetching data
- Return structured data with timestamps
- Include data source and freshness info
- Handle missing data gracefully
"""
        
        super().__init__(
            name="market_data",
            instructions=instructions,
            tools=[],
        )
        self._plugin: Optional[MarketDataPlugin] = None

    @property
    def plugin(self) -> MarketDataPlugin:
        """Lazy-initialize the market data plugin."""
        if self._plugin is None:
            self._plugin = MarketDataPlugin(self.redis)
        return self._plugin

    async def run(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Fetch market data (price, history, change, volume) for a ticker."""
        context = context or {}
        ticker = context.get("ticker") or self._extract_ticker(task)
        metric = context.get("metric", "close")
        history_days = int(context.get("days", 30))

        if not ticker:
            return {
                "status": "error",
                "message": "Please specify a stock ticker symbol (e.g., 'AAPL').",
            }

        cache_params = {
            "ticker": ticker.upper(),
            "metric": metric,
            "days": history_days,
        }
        cached_payload = self.check_tool_cache("market_data_summary", cache_params)
        if cached_payload:
            return {**cached_payload, "cache_hit": True}

        price_result, price_cached = await self._get_price(ticker, metric)
        history_result, history_cached = await self._get_history(ticker, metric, history_days)
        change_result, change_cached = await self._get_change(ticker, metric, history_days)
        volume_result, volume_cached = await self._get_volume(ticker, history_days)
        technical_result, technical_cached = await self._get_technical_indicators(ticker, metric)

        summary = self._summarize(
            ticker,
            price_result,
            change_result,
            volume_result,
            technical_result,
        )

        signals = self._build_signals(change_result, technical_result)

        metadata = {
            "as_of": price_result.get("date"),
            "metric": metric,
            "price_timestamp": price_result.get("timestamp"),
            "history_points": (history_result.get("stats") or {}).get("count"),
        }

        payload = {
            "status": "success",
            "ticker": ticker.upper(),
            "metric": metric,
            "history_days": history_days,
            "current_price": price_result,
            "history": history_result,
            "change": change_result,
            "volume": volume_result,
            "technical": technical_result,
            "signals": signals,
            "metadata": metadata,
            "summary": summary,
            "cache_hit": (
                price_cached
                and history_cached
                and change_cached
                and volume_cached
                and technical_cached
            ),
        }

        self.cache_tool_output("market_data_summary", cache_params, payload, ttl=self.config.tool_cache_ttl)
        return payload

    async def _get_price(self, ticker: str, metric: str) -> Tuple[Dict[str, Any], bool]:
        tool_name = "market_data:get_stock_price"
        params = {"ticker": ticker.upper(), "metric": metric}
        cached = self.check_tool_cache(tool_name, params)
        if cached:
            return cached, True

        result = await self.plugin.get_stock_price(ticker, metric)
        if result.get("success"):
            self.cache_tool_output(tool_name, params, result, ttl=60)
        return result, False

    async def _get_history(self, ticker: str, metric: str, days: int) -> Tuple[Dict[str, Any], bool]:
        tool_name = "market_data:get_price_history"
        params = {"ticker": ticker.upper(), "metric": metric, "days": days}
        cached = self.check_tool_cache(tool_name, params)
        if cached:
            return cached, True

        result = await self.plugin.get_price_history(ticker, days=days, metric=metric)
        if result.get("success"):
            self.cache_tool_output(tool_name, params, result, ttl=300)
        return result, False

    async def _get_change(self, ticker: str, metric: str, days: int) -> Tuple[Dict[str, Any], bool]:
        tool_name = "market_data:get_price_change"
        params = {"ticker": ticker.upper(), "metric": metric, "days": days}
        cached = self.check_tool_cache(tool_name, params)
        if cached:
            return cached, True

        result = await self.plugin.get_price_change(ticker, days=days, metric=metric)
        if result.get("success"):
            self.cache_tool_output(tool_name, params, result, ttl=300)
        return result, False

    async def _get_volume(self, ticker: str, days: int) -> Tuple[Dict[str, Any], bool]:
        tool_name = "market_data:get_volume_analysis"
        params = {"ticker": ticker.upper(), "days": days}
        cached = self.check_tool_cache(tool_name, params)
        if cached:
            return cached, True

        result = await self.plugin.get_volume_analysis(ticker, days=days)
        if result.get("success"):
            self.cache_tool_output(tool_name, params, result, ttl=600)
        return result, False

    async def _get_technical_indicators(self, ticker: str, metric: str) -> Tuple[Dict[str, Any], bool]:
        tool_name = "market_data:get_technical_indicators"
        params = {"ticker": ticker.upper(), "metric": metric}
        cached = self.check_tool_cache(tool_name, params)
        if cached:
            return cached, True

        result = await self.plugin.get_technical_indicators(ticker, metric=metric)
        if result.get("success"):
            self.cache_tool_output(tool_name, params, result, ttl=900)
        return result, False

    @staticmethod
    def _extract_ticker(query: str) -> Optional[str]:
        """Basic ticker extraction to support free-form questions."""
        import re

        patterns = [
            r"\b([A-Z]{1,5})\b(?:\s+stock|\s+shares?)",
            r"(?:ticker|symbol)\s+([A-Z]{1,5})\b",
            r"\$([A-Z]{1,5})\b",
        ]

        upper_query = query.upper()
        for pattern in patterns:
            match = re.search(pattern, upper_query)
            if match:
                return match.group(1)

        for word in upper_query.split():
            if 2 <= len(word) <= 5 and word.isalpha():
                return word

        return None

    @staticmethod
    def _summarize(
        ticker: str,
        price: Dict[str, Any],
        change: Dict[str, Any],
        volume: Dict[str, Any],
        technical: Dict[str, Any],
    ) -> str:
        """Create human-readable summary from component results."""
        price_msg = price.get("message") if isinstance(price, dict) else None
        change_msg = change.get("message") if isinstance(change, dict) else None
        volume_msg = volume.get("message") if isinstance(volume, dict) else None
        technical_msg = technical.get("message") if isinstance(technical, dict) and technical.get("success") else None

        parts = [msg for msg in [price_msg, change_msg, volume_msg, technical_msg] if msg]
        if parts:
            return " | ".join(parts)
        return f"No market data available for {ticker.upper()}"

    @staticmethod
    def _build_signals(change: Dict[str, Any], technical: Dict[str, Any]) -> Dict[str, Any]:
        """Extract concise signal metadata from change and technical payloads."""
        signals: Dict[str, Any] = {}

        if isinstance(change, dict) and change.get("success"):
            signals["trend"] = change.get("trend")
            signals["change_pct"] = change.get("change_pct")
        if isinstance(technical, dict) and technical.get("success"):
            signals["momentum"] = technical.get("momentum")
            signals["trend_signal"] = technical.get("trend")
            macd = technical.get("macd") or {}
            line = macd.get("line")
            signal_line = macd.get("signal")
            if line is not None and signal_line is not None:
                signals["macd_cross"] = "bullish" if line > signal_line else "bearish"
            signals["rsi"] = technical.get("rsi")
        return {k: v for k, v in signals.items() if v is not None}
