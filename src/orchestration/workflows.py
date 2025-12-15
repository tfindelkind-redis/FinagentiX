"""
Orchestration workflows for FinagentiX
Coordinates multiple agents to accomplish complex tasks
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional
import redis
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import ChatHistory

from ..agents.plugins.market_data_plugin import MarketDataPlugin
from ..agents.plugins.technical_analysis_plugin import TechnicalAnalysisPlugin
from ..agents.plugins.risk_analysis_plugin import RiskAnalysisPlugin
from ..agents.plugins.news_sentiment_plugin import NewsSentimentPlugin
from ..agents.plugins.portfolio_plugin import PortfolioPlugin
from ..redis import ToolCache, get_redis_client
from ..utils.logger import WorkflowDebugger
from ..utils.metrics_collector import MetricsCollector


class BaseWorkflow:
    """Base class for orchestration workflows"""
    
    def __init__(
        self,
        kernel: Optional[Kernel] = None,
        tool_cache: Optional[ToolCache] = None,
        redis_client: Optional[redis.Redis] = None,
        metrics_collector: Optional[MetricsCollector] = None,
    ):
        """
        Initialize workflow
        
        Args:
            kernel: Semantic Kernel instance
            tool_cache: Tool cache for caching plugin outputs
        """
        self.kernel = kernel
        self.tool_cache = tool_cache or ToolCache()
        self.metrics = metrics_collector
        self.debugger = WorkflowDebugger(self.__class__.__name__)
        self.redis = redis_client or get_redis_client()
        
        # Initialize plugins
        self.market_data = MarketDataPlugin(self.redis)
        self.technical_analysis = TechnicalAnalysisPlugin(self.redis)
        self.risk_analysis = RiskAnalysisPlugin(self.redis)
        self.news_sentiment = NewsSentimentPlugin(self.redis)
        self.portfolio = PortfolioPlugin(self.redis)

        self.debugger.log_config({
            "kernel_provided": kernel is not None,
            "tool_cache_provided": tool_cache is not None
        })
    
    async def execute(self, **params) -> Dict[str, Any]:
        """Execute workflow - to be implemented by subclasses"""
        raise NotImplementedError

    def _record_tool_metrics(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Optional[Dict[str, Any]],
        start_time: float,
        cache_hit: bool,
        cache_checked: bool = False,
        cache_layer: str = "tool_cache",
        status: str = "success",
        error: Optional[str] = None,
    ) -> None:
        """Record tool invocation and cache metrics when collector available."""
        if not self.metrics:
            return

        duration_ms = (time.perf_counter() - start_time) * 1000
        result_payload = result or {}
        try:
            result_size = len(json.dumps(result_payload))
        except (TypeError, ValueError):
            result_size = len(str(result_payload))

        self.metrics.record_tool_invocation(
            tool_name=tool_name,
            parameters=parameters,
            duration_ms=duration_ms,
            cache_hit=cache_hit,
            cache_similarity=1.0 if cache_hit else None,
            result_size=result_size,
            status=status,
            error=error,
        )

        if cache_checked or cache_hit:
            self.metrics.record_cache_check(
                layer_name=cache_layer,
                hit=cache_hit,
                similarity=1.0 if cache_hit else None,
                query_time_ms=duration_ms,
                matched_query=f"{tool_name}:{parameters}",
                cost_saved=0.0,
            )


class InvestmentAnalysisWorkflow(BaseWorkflow):
    """
    Complete investment analysis workflow
    
    Agents: Market Data + Technical Analysis + Risk Analysis + News Sentiment
    Use case: "Should I invest in AAPL?"
    """
    
    async def execute(self, ticker: str, **params) -> Dict[str, Any]:
        """
        Execute investment analysis
        
        Args:
            ticker: Stock ticker symbol
            **params: Additional parameters
        
        Returns:
            Complete investment analysis
        """
        self.debugger.log_step("start_investment_analysis", f"ticker={ticker}")
        rag_context = params.get("rag_context")
        
        # Run agents in parallel for speed while handling partial failures
        tasks = (
            ("market_data", self._get_market_data(ticker)),
            ("technical_analysis", self._get_technical_analysis(ticker)),
            ("risk_analysis", self._get_risk_analysis(ticker)),
            ("news_sentiment", self._get_news_sentiment(ticker)),
        )
        raw_results = await asyncio.gather(
            *(task for _, task in tasks),
            return_exceptions=True
        )

        errors: List[Dict[str, Any]] = []

        def _fallback_payload(tool_name: str, error: Exception) -> Dict[str, Any]:
            """Create structured fallback payload for failed tool."""
            message = str(error)
            if self.metrics:
                self.metrics.add_warning(f"{tool_name}_error:{message}")
            self.debugger.log_error(error)
            fallback_common = {"success": False, "error": message}
            if tool_name == "market_data":
                fallback = {
                    **fallback_common,
                    "current_price": {"success": False, "error": message},
                    "historical": {"success": False, "error": message},
                }
            elif tool_name == "technical_analysis":
                fallback = {
                    **fallback_common,
                    "sma_50": {"success": False, "error": message},
                    "sma_200": {"success": False, "error": message},
                    "rsi": {"success": False, "error": message},
                    "volatility": {"success": False, "error": message},
                }
            elif tool_name == "risk_analysis":
                fallback = {
                    **fallback_common,
                    "var": {"success": False, "error": message},
                    "beta": {"success": False, "error": message},
                    "drawdown": {"success": False, "error": message},
                }
            else:  # news_sentiment
                fallback = {
                    **fallback_common,
                    "news": {"success": False, "error": message},
                    "sentiment": {"success": False, "error": message},
                }
            errors.append({"tool": tool_name, "error": message})
            return fallback

        processed = []
        for (name, _), result in zip(tasks, raw_results):
            if isinstance(result, Exception):
                processed.append(_fallback_payload(name, result))
            else:
                processed.append(result)

        market_data, technical, risk, sentiment = processed
        
        # Synthesize recommendation
        recommendation = self._synthesize_recommendation(
            ticker=ticker,
            market_data=market_data,
            technical=technical,
            risk=risk,
            sentiment=sentiment
        )
        
        result_payload = {
            "workflow": "InvestmentAnalysisWorkflow",
            "ticker": ticker,
            "market_data": market_data,
            "technical_analysis": technical,
            "risk_analysis": risk,
            "sentiment_analysis": sentiment,
            "recommendation": recommendation,
            "timestamp": "now",
            "rag": rag_context,
        }
        if errors:
            result_payload["errors"] = errors
        return result_payload
    
    async def _get_market_data(self, ticker: str) -> Dict[str, Any]:
        """Get market data"""
        start_time = time.perf_counter()
        try:
            cached = self.tool_cache.get("market_data", ticker=ticker)
            if cached:
                self.debugger.log_cache_hit(f"market_data:{ticker}")
                self._record_tool_metrics(
                    tool_name="market_data",
                    parameters={"ticker": ticker},
                    result=cached,
                    start_time=start_time,
                    cache_hit=True,
                    cache_checked=True,
                )
                return cached

            self.debugger.log_cache_miss(f"market_data:{ticker}")

            price_data = await self.market_data.get_stock_price(ticker)
            historical = await self.market_data.get_price_history(ticker, days=30)

            result = {
                "current_price": price_data,
                "historical": historical,
            }

            self.tool_cache.set("market_data", result, ticker=ticker, ttl_seconds=60)
            self.debugger.log_step("market_data_fetched", f"ticker={ticker}")
            self._record_tool_metrics(
                tool_name="market_data",
                parameters={"ticker": ticker},
                result=result,
                start_time=start_time,
                cache_hit=False,
                cache_checked=True,
            )
            return result

        except Exception as exc:
            self.debugger.log_error(exc)
            self._record_tool_metrics(
                tool_name="market_data",
                parameters={"ticker": ticker},
                result=None,
                start_time=start_time,
                cache_hit=False,
                cache_checked=True,
                status="error",
                error=str(exc),
            )
            raise
    
    async def _get_technical_analysis(self, ticker: str) -> Dict[str, Any]:
        """Get technical analysis"""
        start_time = time.perf_counter()
        try:
            cached = self.tool_cache.get("technical_analysis", ticker=ticker)
            if cached:
                self.debugger.log_cache_hit(f"technical_analysis:{ticker}")
                self._record_tool_metrics(
                    tool_name="technical_analysis",
                    parameters={"ticker": ticker},
                    result=cached,
                    start_time=start_time,
                    cache_hit=True,
                    cache_checked=True,
                )
                return cached

            self.debugger.log_cache_miss(f"technical_analysis:{ticker}")

            sma_50 = await self.technical_analysis.calculate_sma(ticker, period=50)
            sma_200 = await self.technical_analysis.calculate_sma(ticker, period=200)
            rsi = await self.technical_analysis.calculate_rsi(ticker, period=14)
            volatility = await self.technical_analysis.get_volatility(ticker, days=30)

            result = {
                "sma_50": sma_50,
                "sma_200": sma_200,
                "rsi": rsi,
                "volatility": volatility,
            }

            self.tool_cache.set("technical_analysis", result, ticker=ticker, ttl_seconds=300)
            self.debugger.log_step("technical_analysis_fetched", f"ticker={ticker}")
            self._record_tool_metrics(
                tool_name="technical_analysis",
                parameters={"ticker": ticker},
                result=result,
                start_time=start_time,
                cache_hit=False,
                cache_checked=True,
            )
            return result

        except Exception as exc:
            self.debugger.log_error(exc)
            self._record_tool_metrics(
                tool_name="technical_analysis",
                parameters={"ticker": ticker},
                result=None,
                start_time=start_time,
                cache_hit=False,
                cache_checked=True,
                status="error",
                error=str(exc),
            )
            raise
    
    async def _get_risk_analysis(self, ticker: str) -> Dict[str, Any]:
        """Get risk analysis"""
        start_time = time.perf_counter()
        try:
            cached = self.tool_cache.get("risk_analysis", ticker=ticker)
            if cached:
                self.debugger.log_cache_hit(f"risk_analysis:{ticker}")
                self._record_tool_metrics(
                    tool_name="risk_analysis",
                    parameters={"ticker": ticker},
                    result=cached,
                    start_time=start_time,
                    cache_hit=True,
                    cache_checked=True,
                )
                return cached

            self.debugger.log_cache_miss(f"risk_analysis:{ticker}")

            var = await self.risk_analysis.calculate_var(ticker, confidence=0.95, holding_period=1)
            beta = await self.risk_analysis.calculate_beta(ticker)
            drawdown = await self.risk_analysis.calculate_drawdown(ticker, days=252)

            result = {
                "var": var,
                "beta": beta,
                "drawdown": drawdown,
            }

            self.tool_cache.set("risk_analysis", result, ticker=ticker, ttl_seconds=600)
            self.debugger.log_step("risk_analysis_fetched", f"ticker={ticker}")
            self._record_tool_metrics(
                tool_name="risk_analysis",
                parameters={"ticker": ticker},
                result=result,
                start_time=start_time,
                cache_hit=False,
                cache_checked=True,
            )
            return result

        except Exception as exc:
            self.debugger.log_error(exc)
            self._record_tool_metrics(
                tool_name="risk_analysis",
                parameters={"ticker": ticker},
                result=None,
                start_time=start_time,
                cache_hit=False,
                cache_checked=True,
                status="error",
                error=str(exc),
            )
            raise
    
    async def _get_news_sentiment(self, ticker: str) -> Dict[str, Any]:
        """Get news sentiment"""
        start_time = time.perf_counter()
        try:
            cached = self.tool_cache.get("news_sentiment", ticker=ticker)
            if cached:
                self.debugger.log_cache_hit(f"news_sentiment:{ticker}")
                self._record_tool_metrics(
                    tool_name="news_sentiment",
                    parameters={"ticker": ticker},
                    result=cached,
                    start_time=start_time,
                    cache_hit=True,
                    cache_checked=True,
                )
                return cached

            self.debugger.log_cache_miss(f"news_sentiment:{ticker}")

            news = await self.news_sentiment.get_ticker_news(ticker, limit=5)
            sentiment = await self.news_sentiment.get_news_sentiment(ticker)

            result = {
                "news": news,
                "sentiment": sentiment,
            }

            self.tool_cache.set("news_sentiment", result, ticker=ticker, ttl_seconds=1800)
            self.debugger.log_step("news_sentiment_fetched", f"ticker={ticker}")
            self._record_tool_metrics(
                tool_name="news_sentiment",
                parameters={"ticker": ticker},
                result=result,
                start_time=start_time,
                cache_hit=False,
                cache_checked=True,
            )
            return result

        except Exception as exc:
            self.debugger.log_error(exc)
            self._record_tool_metrics(
                tool_name="news_sentiment",
                parameters={"ticker": ticker},
                result=None,
                start_time=start_time,
                cache_hit=False,
                cache_checked=True,
                status="error",
                error=str(exc),
            )
            raise
    
    def _synthesize_recommendation(
        self,
        ticker: str,
        market_data: Dict,
        technical: Dict,
        risk: Dict,
        sentiment: Dict
    ) -> Dict[str, Any]:
        """Synthesize investment recommendation"""
        
        # Simple rule-based recommendation (can be enhanced with LLM)
        signals = []
        
        # Technical signals
        if technical.get("sma_50", {}).get("success"):
            sma_50_val = technical["sma_50"].get("sma", 0)
            sma_200_val = technical["sma_200"].get("sma", 0)
            
            if sma_50_val > sma_200_val:
                signals.append("bullish_trend")
            else:
                signals.append("bearish_trend")
        
        # RSI signals
        if technical.get("rsi", {}).get("success"):
            rsi_val = technical["rsi"].get("rsi", 50)
            if rsi_val < 30:
                signals.append("oversold")
            elif rsi_val > 70:
                signals.append("overbought")
        
        # Sentiment signals
        if sentiment.get("sentiment", {}).get("success"):
            sent_score = sentiment["sentiment"].get("overall_sentiment", "neutral")
            if "positive" in sent_score.lower():
                signals.append("positive_sentiment")
            elif "negative" in sent_score.lower():
                signals.append("negative_sentiment")
        
        # Determine overall recommendation
        bullish_count = sum(1 for s in signals if s in ["bullish_trend", "oversold", "positive_sentiment"])
        bearish_count = sum(1 for s in signals if s in ["bearish_trend", "overbought", "negative_sentiment"])
        
        if bullish_count > bearish_count:
            action = "BUY"
            confidence = "moderate"
        elif bearish_count > bullish_count:
            action = "SELL"
            confidence = "moderate"
        else:
            action = "HOLD"
            confidence = "low"
        
        self.debugger.log_decision(
            "investment_recommendation",
            f"ticker={ticker}; action={action}; signals={signals}"
        )

        return {
            "action": action,
            "confidence": confidence,
            "signals": signals,
            "summary": f"Based on technical analysis, risk metrics, and sentiment, recommend {action} for {ticker}",
        }


class PortfolioReviewWorkflow(BaseWorkflow):
    """
    Portfolio review workflow
    
    Agents: Portfolio + Risk Analysis
    Use case: "Review my portfolio performance"
    """
    
    async def execute(self, portfolio_id: str = "default", **params) -> Dict[str, Any]:
        """Execute portfolio review"""
        self.debugger.log_step("start_portfolio_review", f"portfolio={portfolio_id}")
        
        # Get portfolio data
        positions_start = time.perf_counter()
        positions = await self.portfolio.get_positions(portfolio_id)
        self._record_tool_metrics(
            tool_name="portfolio_positions",
            parameters={"portfolio_id": portfolio_id},
            result={"positions": positions},
            start_time=positions_start,
            cache_hit=False,
        )

        metrics_start = time.perf_counter()
        metrics = await self.portfolio.calculate_metrics(portfolio_id)
        self._record_tool_metrics(
            tool_name="portfolio_metrics",
            parameters={"portfolio_id": portfolio_id},
            result={"metrics": metrics},
            start_time=metrics_start,
            cache_hit=False,
        )

        allocation_start = time.perf_counter()
        allocation = await self.portfolio.analyze_allocation(portfolio_id)
        self._record_tool_metrics(
            tool_name="portfolio_allocation",
            parameters={"portfolio_id": portfolio_id},
            result={"allocation": allocation},
            start_time=allocation_start,
            cache_hit=False,
        )
        
        # Get risk analysis for portfolio
        # (This would normally analyze the entire portfolio)
        
        return {
            "workflow": "PortfolioReviewWorkflow",
            "portfolio_id": portfolio_id,
            "positions": positions,
            "metrics": metrics,
            "allocation": allocation,
            "timestamp": "now",
        }


class MarketResearchWorkflow(BaseWorkflow):
    """
    Market research workflow
    
    Agents: Market Data + News Sentiment + Technical Analysis
    Use case: "What's happening in the tech sector?"
    """
    
    async def execute(self, query: str, tickers: Optional[List[str]] = None, **params) -> Dict[str, Any]:
        """Execute market research"""
        self.debugger.log_step("start_market_research", f"query={query}")
        rag_context = params.get("rag_context")
        
        # Default tickers if none provided
        if not tickers:
            tickers = ["AAPL", "MSFT", "GOOGL", "NVDA", "META"]
        
        # Get market overview for each ticker
        results = []
        for ticker in tickers[:5]:  # Limit to 5
            data = await self._get_ticker_overview(ticker)
            results.append(data)
        
        # Get general market news
        news_start = time.perf_counter()
        market_news = await self.news_sentiment.get_recent_news(limit=10)
        self._record_tool_metrics(
            tool_name="market_research_news",
            parameters={"limit": 10},
            result={"market_news": market_news},
            start_time=news_start,
            cache_hit=False,
        )
        
        return {
            "workflow": "MarketResearchWorkflow",
            "query": query,
            "tickers": results,
            "market_news": market_news,
            "timestamp": "now",
            "rag": rag_context,
        }
    
    async def _get_ticker_overview(self, ticker: str) -> Dict[str, Any]:
        """Get overview for single ticker"""
        try:
            self.debugger.log_step("ticker_overview_fetch", f"ticker={ticker}")
            price_start = time.perf_counter()
            price = await self.market_data.get_stock_price(ticker)
            self._record_tool_metrics(
                tool_name="ticker_overview_price",
                parameters={"ticker": ticker},
                result={"price": price},
                start_time=price_start,
                cache_hit=False,
            )
            news_start = time.perf_counter()
            news = await self.news_sentiment.get_ticker_news(ticker, limit=3)
            self._record_tool_metrics(
                tool_name="ticker_overview_news",
                parameters={"ticker": ticker, "limit": 3},
                result={"news": news},
                start_time=news_start,
                cache_hit=False,
            )

            return {
                "ticker": ticker,
                "price": price,
                "news": news,
            }

        except Exception as exc:
            self.debugger.log_error(exc)
            self._record_tool_metrics(
                tool_name="ticker_overview",
                parameters={"ticker": ticker},
                result=None,
                start_time=time.perf_counter(),
                cache_hit=False,
                status="error",
                error=str(exc),
            )
            raise


class QuickQuoteWorkflow(BaseWorkflow):
    """
    Quick quote workflow
    
    Agents: Market Data only
    Use case: "What's AAPL's price?"
    """
    
    async def execute(self, ticker: str, **params) -> Dict[str, Any]:
        """Execute quick quote"""
        self.debugger.log_step("start_quick_quote", f"ticker={ticker}")
        
        # Get current price only
        price_start = time.perf_counter()
        price_data = await self.market_data.get_stock_price(ticker)
        self._record_tool_metrics(
            tool_name="quick_quote_price",
            parameters={"ticker": ticker},
            result={"price_data": price_data},
            start_time=price_start,
            cache_hit=False,
        )
        
        return {
            "workflow": "QuickQuoteWorkflow",
            "ticker": ticker,
            "price_data": price_data,
            "timestamp": "now",
        }


if __name__ == "__main__":
    # Test workflows
    async def test_workflows():
        # Test Investment Analysis
        workflow = InvestmentAnalysisWorkflow()
        result = await workflow.execute(ticker="AAPL")
        print(f"\n✅ Investment Analysis Result:")
        print(f"   Action: {result['recommendation']['action']}")
        print(f"   Signals: {result['recommendation']['signals']}")
        
        # Test Quick Quote
        quick = QuickQuoteWorkflow()
        result2 = await quick.execute(ticker="MSFT")
        print(f"\n✅ Quick Quote Result:")
        print(f"   Price: {result2['price_data']}")
    
    asyncio.run(test_workflows())
