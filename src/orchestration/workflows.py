"""
Orchestration workflows for FinagentiX
Coordinates multiple agents to accomplish complex tasks
"""

import asyncio
import functools
import json
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
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


@dataclass
class AgentTaskSpec:
    """Specification describing an agent task for workflow execution."""

    name: str
    coroutine_factory: Callable[[], Awaitable[Dict[str, Any]]]
    fallback_factory: Optional[Callable[[Exception], Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


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

    async def _run_agent_tasks(
        self,
        tasks: List[AgentTaskSpec],
        pattern: str = "concurrent",
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        """Run agent tasks with optional parallelism and structured error handling."""

        if not tasks:
            return [], []

        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, str]] = []

        async def _execute_task(spec: AgentTaskSpec) -> Dict[str, Any]:
            return await spec.coroutine_factory()

        async def _run_single(spec: AgentTaskSpec) -> Dict[str, Any]:
            try:
                return await _execute_task(spec)
            except Exception as exc:  # pragma: no cover - defensive
                return self._handle_task_failure(spec, exc, errors)

        if pattern == "concurrent":
            coroutines = [_run_single(spec) for spec in tasks]
            gathered = await asyncio.gather(*coroutines, return_exceptions=False)
            results.extend(gathered)
        else:
            for spec in tasks:
                result = await _run_single(spec)
                results.append(result)

        return results, errors

    def _handle_task_failure(
        self,
        spec: AgentTaskSpec,
        error: Exception,
        errors_accumulator: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Handle agent execution failures and build fallback payloads."""

        message = str(error)
        errors_accumulator.append({"tool": spec.name, "error": message})
        self.debugger.log_error(error)
        if self.metrics:
            try:
                self.metrics.add_warning(f"{spec.name}_error:{message}")
            except AttributeError:
                pass

        if spec.fallback_factory:
            try:
                return spec.fallback_factory(error)
            except Exception as fallback_error:  # pragma: no cover - defensive
                self.debugger.log_error(fallback_error)

        return {
            "status": "error",
            "message": message,
            "error": message,
            "success": False,
        }

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

    def _structure_market_result(self, ticker: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize market data payload for downstream synthesis."""
        payload = payload or {}
        ticker_upper = ticker.upper()

        if payload.get("status") and payload.get("summary"):
            payload.setdefault("ticker", ticker_upper)
            if "history" in payload and "historical" not in payload:
                payload["historical"] = payload["history"]
            return payload

        current_price = payload.get("current_price") or payload.get("price_data") or {}
        history = payload.get("historical") or payload.get("history") or {}
        summary = payload.get("summary")

        if not summary:
            messages: List[str] = []
            if isinstance(current_price, dict) and current_price.get("message"):
                messages.append(current_price["message"])
            if isinstance(history, dict) and history.get("message"):
                messages.append(history["message"])
            summary = " | ".join(messages[:2])

        success_price = bool(current_price.get("success")) if isinstance(current_price, dict) else False
        success_history = bool(history.get("success")) if isinstance(history, dict) else False
        status = payload.get("status") or ("success" if success_price or success_history else "error")

        structured = {
            "status": status,
            "ticker": ticker_upper,
            "summary": summary or f"No market data available for {ticker_upper}",
            "current_price": current_price,
            "historical": history,
        }
        if "cache_hit" in payload:
            structured["cache_hit"] = payload["cache_hit"]
        return structured

    def _structure_technical_result(self, ticker: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize technical analysis payload."""
        payload = payload or {}
        ticker_upper = ticker.upper()
        if payload.get("status") and payload.get("summary"):
            payload.setdefault("ticker", ticker_upper)
            return payload

        sma_50 = payload.get("sma_50") or {}
        sma_200 = payload.get("sma_200") or {}
        rsi = payload.get("rsi") or {}
        volatility = payload.get("volatility") or {}

        summary_parts: List[str] = []
        for indicator in (sma_50, rsi, volatility):
            if isinstance(indicator, dict) and indicator.get("message"):
                summary_parts.append(indicator["message"])

        summary = payload.get("summary") or " | ".join(summary_parts[:2])

        signals: List[str] = payload.get("signals", [])
        if not signals:
            sma_50_val = sma_50.get("sma")
            sma_200_val = sma_200.get("sma")
            if isinstance(sma_50_val, (int, float)) and isinstance(sma_200_val, (int, float)):
                signals.append("bullish_trend" if sma_50_val > sma_200_val else "bearish_trend")
            rsi_status = rsi.get("status")
            if rsi_status == "oversold":
                signals.append("oversold")
            elif rsi_status == "overbought":
                signals.append("overbought")

        success_flags = [item.get("success") for item in (sma_50, sma_200, rsi, volatility) if isinstance(item, dict)]
        status = payload.get("status") or ("success" if any(success_flags) else "error")

        structured = {
            "status": status,
            "ticker": ticker_upper,
            "summary": summary or f"No technical indicators available for {ticker_upper}",
            "signals": signals,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "rsi": rsi,
            "volatility": volatility,
        }
        if "cache_hit" in payload:
            structured["cache_hit"] = payload["cache_hit"]
        return structured

    def _structure_risk_result(self, ticker: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize risk analysis payload."""
        payload = payload or {}
        ticker_upper = ticker.upper()
        if payload.get("status") and payload.get("summary"):
            payload.setdefault("ticker", ticker_upper)
            return payload

        var = payload.get("var") or {}
        beta = payload.get("beta") or {}
        drawdown = payload.get("drawdown") or {}

        insights: List[str] = payload.get("insights") or []
        if not insights:
            for metric in (var, beta, drawdown):
                if isinstance(metric, dict) and metric.get("success") and metric.get("message"):
                    insights.append(metric["message"])

        summary = payload.get("summary") or (insights[0] if insights else None)
        success_flags = [metric.get("success") for metric in (var, beta, drawdown) if isinstance(metric, dict)]
        status = payload.get("status") or ("success" if any(success_flags) else "error")

        structured = {
            "status": status,
            "ticker": ticker_upper,
            "summary": summary or f"No risk metrics available for {ticker_upper}",
            "var": var,
            "beta": beta,
            "drawdown": drawdown,
            "insights": insights,
        }
        if "cache_hit" in payload:
            structured["cache_hit"] = payload["cache_hit"]
        return structured

    def _structure_news_result(self, ticker: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize news sentiment payload."""
        payload = payload or {}
        ticker_upper = ticker.upper()
        if payload.get("status") and payload.get("summary"):
            payload.setdefault("ticker", ticker_upper)
            return payload

        news = payload.get("news") or {}
        sentiment = payload.get("sentiment") or {}

        structured_articles = payload.get("articles") or {
            "count": news.get("count", 0),
            "results": news.get("results", []),
            "success": news.get("success"),
            "message": news.get("message"),
        }

        summary = payload.get("summary") or sentiment.get("message") or news.get("message")
        status = payload.get("status") or (
            "success" if sentiment.get("success") or news.get("success") else "error"
        )

        structured = {
            "status": status,
            "ticker": ticker_upper,
            "summary": summary or f"No recent news available for {ticker_upper}",
            "articles": structured_articles,
            "sentiment": sentiment,
        }
        if "cache_hit" in payload:
            structured["cache_hit"] = payload["cache_hit"]
        if "impact" in payload:
            structured["impact"] = payload["impact"]
        return structured

    def _structure_portfolio_result(
        self,
        portfolio_id: str,
        positions: Optional[Dict[str, Any]],
        metrics: Optional[Dict[str, Any]],
        allocation: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Normalize portfolio workflow payload."""

        positions = positions or {}
        metrics = metrics or {}
        allocation = allocation or {}

        def _payload_success(payload: Dict[str, Any]) -> bool:
            if payload.get("success") is not None:
                return bool(payload.get("success"))
            status = payload.get("status")
            if isinstance(status, str):
                return status.lower() == "success"
            return bool(payload)

        success_flags = [
            _payload_success(positions) if isinstance(positions, dict) else False,
            _payload_success(metrics) if isinstance(metrics, dict) else False,
            _payload_success(allocation) if isinstance(allocation, dict) else False,
        ]

        summary_parts: List[str] = []

        if isinstance(metrics, dict):
            if metrics.get("summary"):
                summary_parts.append(str(metrics["summary"]))
            elif metrics.get("total_return") is not None:
                summary_parts.append(
                    f"Portfolio return {metrics['total_return']}"
                )

        if isinstance(positions, dict):
            holdings = positions.get("positions") or positions.get("holdings") or []
            if isinstance(holdings, list) and holdings:
                summary_parts.append(f"Holding count {len(holdings)}")
            total_value = positions.get("total_value")
            if isinstance(total_value, (int, float)):
                summary_parts.append(f"Value ${total_value:,.2f}")

        if isinstance(allocation, dict):
            dominant = allocation.get("top_sector") or allocation.get("top_asset")
            if dominant:
                summary_parts.append(f"Top allocation {dominant}")

        summary = " | ".join(summary_parts[:3])

        structured = {
            "status": "success" if any(success_flags) else "error",
            "portfolio_id": portfolio_id,
            "summary": summary or f"No portfolio analytics available for {portfolio_id}",
            "positions": positions,
            "metrics": metrics,
            "allocation": allocation,
        }

        return structured


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
        
        def _fallback_payload(tool_name: str, error: Exception) -> Dict[str, Any]:
            """Create structured fallback payload for failed tool."""
            message = str(error)
            fallback_common = {"success": False, "error": message, "message": message}
            if tool_name == "market_data":
                return self._structure_market_result(
                    ticker,
                    {
                        **fallback_common,
                        "current_price": {"success": False, "error": message, "message": message},
                        "historical": {"success": False, "error": message, "message": message},
                    },
                )
            if tool_name == "technical_analysis":
                return self._structure_technical_result(
                    ticker,
                    {
                        **fallback_common,
                        "sma_50": {"success": False, "error": message},
                        "sma_200": {"success": False, "error": message},
                        "rsi": {"success": False, "error": message},
                        "volatility": {"success": False, "error": message},
                    },
                )
            if tool_name == "risk_analysis":
                return self._structure_risk_result(
                    ticker,
                    {
                        **fallback_common,
                        "var": {"success": False, "error": message},
                        "beta": {"success": False, "error": message},
                        "drawdown": {"success": False, "error": message},
                    },
                )
            return self._structure_news_result(
                ticker,
                {
                    **fallback_common,
                    "news": {"success": False, "error": message},
                    "sentiment": {"success": False, "error": message, "message": message},
                },
            )

        task_specs: List[AgentTaskSpec] = [
            AgentTaskSpec(
                name="market_data",
                coroutine_factory=functools.partial(self._get_market_data, ticker),
                fallback_factory=functools.partial(_fallback_payload, "market_data"),
            ),
            AgentTaskSpec(
                name="technical_analysis",
                coroutine_factory=functools.partial(self._get_technical_analysis, ticker),
                fallback_factory=functools.partial(_fallback_payload, "technical_analysis"),
            ),
            AgentTaskSpec(
                name="risk_analysis",
                coroutine_factory=functools.partial(self._get_risk_analysis, ticker),
                fallback_factory=functools.partial(_fallback_payload, "risk_analysis"),
            ),
            AgentTaskSpec(
                name="news_sentiment",
                coroutine_factory=functools.partial(self._get_news_sentiment, ticker),
                fallback_factory=functools.partial(_fallback_payload, "news_sentiment"),
            ),
        ]

        processed, errors = await self._run_agent_tasks(task_specs, pattern="concurrent")
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
        result_payload["agent_results"] = {
            "market_data": market_data,
            "technical_analysis": technical,
            "risk_assessment": risk,
            "news_sentiment": sentiment,
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
                normalized = self._structure_market_result(ticker, dict(cached))
                normalized["cache_hit"] = True
                if "status" not in cached or "summary" not in cached or "cache_hit" in cached:
                    stored_payload = {k: v for k, v in normalized.items() if k != "cache_hit"}
                    self.tool_cache.set("market_data", stored_payload, ticker=ticker, ttl_seconds=60)
                self._record_tool_metrics(
                    tool_name="market_data",
                    parameters={"ticker": ticker},
                    result=normalized,
                    start_time=start_time,
                    cache_hit=True,
                    cache_checked=True,
                )
                return normalized

            self.debugger.log_cache_miss(f"market_data:{ticker}")

            price_data = await self.market_data.get_stock_price(ticker)
            historical = await self.market_data.get_price_history(ticker, days=30)
            raw_payload = {
                "current_price": price_data,
                "historical": historical,
            }
            result = self._structure_market_result(ticker, raw_payload)
            result["cache_hit"] = False

            stored_payload = {k: v for k, v in result.items() if k != "cache_hit"}
            self.tool_cache.set("market_data", stored_payload, ticker=ticker, ttl_seconds=60)
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
                normalized = self._structure_technical_result(ticker, dict(cached))
                normalized["cache_hit"] = True
                if "status" not in cached or "summary" not in cached or "cache_hit" in cached:
                    stored_payload = {k: v for k, v in normalized.items() if k != "cache_hit"}
                    self.tool_cache.set("technical_analysis", stored_payload, ticker=ticker, ttl_seconds=300)
                self._record_tool_metrics(
                    tool_name="technical_analysis",
                    parameters={"ticker": ticker},
                    result=normalized,
                    start_time=start_time,
                    cache_hit=True,
                    cache_checked=True,
                )
                return normalized

            self.debugger.log_cache_miss(f"technical_analysis:{ticker}")

            sma_50 = await self.technical_analysis.calculate_sma(ticker, period=50)
            sma_200 = await self.technical_analysis.calculate_sma(ticker, period=200)
            rsi = await self.technical_analysis.calculate_rsi(ticker, period=14)
            volatility = await self.technical_analysis.get_volatility(ticker, days=30)

            raw_payload = {
                "sma_50": sma_50,
                "sma_200": sma_200,
                "rsi": rsi,
                "volatility": volatility,
            }
            result = self._structure_technical_result(ticker, raw_payload)
            result["cache_hit"] = False

            stored_payload = {k: v for k, v in result.items() if k != "cache_hit"}
            self.tool_cache.set("technical_analysis", stored_payload, ticker=ticker, ttl_seconds=300)
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
                normalized = self._structure_risk_result(ticker, dict(cached))
                normalized["cache_hit"] = True
                if "status" not in cached or "summary" not in cached or "cache_hit" in cached:
                    stored_payload = {k: v for k, v in normalized.items() if k != "cache_hit"}
                    self.tool_cache.set("risk_analysis", stored_payload, ticker=ticker, ttl_seconds=600)
                self._record_tool_metrics(
                    tool_name="risk_analysis",
                    parameters={"ticker": ticker},
                    result=normalized,
                    start_time=start_time,
                    cache_hit=True,
                    cache_checked=True,
                )
                return normalized

            self.debugger.log_cache_miss(f"risk_analysis:{ticker}")

            var = await self.risk_analysis.calculate_var(ticker, confidence=0.95, holding_period=1)
            beta = await self.risk_analysis.calculate_beta(ticker)
            drawdown = await self.risk_analysis.calculate_drawdown(ticker, days=252)

            raw_payload = {
                "var": var,
                "beta": beta,
                "drawdown": drawdown,
            }
            result = self._structure_risk_result(ticker, raw_payload)
            result["cache_hit"] = False

            stored_payload = {k: v for k, v in result.items() if k != "cache_hit"}
            self.tool_cache.set("risk_analysis", stored_payload, ticker=ticker, ttl_seconds=600)
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
                normalized = self._structure_news_result(ticker, dict(cached))
                normalized["cache_hit"] = True
                if "status" not in cached or "summary" not in cached or "cache_hit" in cached:
                    stored_payload = {k: v for k, v in normalized.items() if k != "cache_hit"}
                    self.tool_cache.set("news_sentiment", stored_payload, ticker=ticker, ttl_seconds=1800)
                self._record_tool_metrics(
                    tool_name="news_sentiment",
                    parameters={"ticker": ticker},
                    result=normalized,
                    start_time=start_time,
                    cache_hit=True,
                    cache_checked=True,
                )
                return normalized

            self.debugger.log_cache_miss(f"news_sentiment:{ticker}")

            news = await self.news_sentiment.get_ticker_news(ticker, limit=5)
            sentiment = await self.news_sentiment.get_news_sentiment(ticker)

            raw_payload = {
                "news": news,
                "sentiment": sentiment,
            }
            result = self._structure_news_result(ticker, raw_payload)
            result["cache_hit"] = False

            stored_payload = {k: v for k, v in result.items() if k != "cache_hit"}
            self.tool_cache.set("news_sentiment", stored_payload, ticker=ticker, ttl_seconds=1800)
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

        def _fallback_payload(tool_name: str, error: Exception) -> Dict[str, Any]:
            message = str(error)
            base = {
                "portfolio_id": portfolio_id,
                "success": False,
                "error": message,
                "message": message,
            }
            if tool_name == "portfolio_positions":
                return {
                    **base,
                    "positions": [],
                    "total_value": 0,
                    "num_positions": 0,
                }
            if tool_name == "portfolio_metrics":
                return {
                    **base,
                    "total_value": 0,
                    "total_cost": 0,
                    "total_gain_loss": 0,
                    "total_return_pct": 0,
                }
            if tool_name == "portfolio_allocation":
                return {
                    **base,
                    "total_positions": 0,
                    "top_5_concentration": 0,
                    "large_positions": 0,
                    "medium_positions": 0,
                    "small_positions": 0,
                    "diversification": "unknown",
                    "concentration_risk": "unknown",
                    "risk_note": message,
                }
            return base

        task_specs: List[AgentTaskSpec] = [
            AgentTaskSpec(
                name="portfolio_positions",
                coroutine_factory=functools.partial(
                    self._get_portfolio_positions,
                    portfolio_id,
                ),
                fallback_factory=functools.partial(_fallback_payload, "portfolio_positions"),
            ),
            AgentTaskSpec(
                name="portfolio_metrics",
                coroutine_factory=functools.partial(
                    self._get_portfolio_metrics,
                    portfolio_id,
                ),
                fallback_factory=functools.partial(_fallback_payload, "portfolio_metrics"),
            ),
            AgentTaskSpec(
                name="portfolio_allocation",
                coroutine_factory=functools.partial(
                    self._get_portfolio_allocation,
                    portfolio_id,
                ),
                fallback_factory=functools.partial(_fallback_payload, "portfolio_allocation"),
            ),
        ]

        processed, errors = await self._run_agent_tasks(task_specs, pattern="sequential")
        positions, metrics, allocation = processed

        structured_portfolio = self._structure_portfolio_result(
            portfolio_id=portfolio_id,
            positions=positions,
            metrics=metrics,
            allocation=allocation,
        )

        result_payload = {
            "workflow": "PortfolioReviewWorkflow",
            "portfolio_id": portfolio_id,
            "positions": positions,
            "metrics": metrics,
            "allocation": allocation,
            "timestamp": "now",
            "portfolio_summary": structured_portfolio,
        }
        result_payload["agent_results"] = {
            "portfolio_review": structured_portfolio,
        }
        if errors:
            result_payload["errors"] = errors
        return result_payload

    async def _get_portfolio_positions(self, portfolio_id: str) -> Dict[str, Any]:
        start_time = time.perf_counter()
        try:
            positions = await self.portfolio.get_positions(portfolio_id)
            self.debugger.log_step("portfolio_positions_fetched", f"portfolio={portfolio_id}")
            self._record_tool_metrics(
                tool_name="portfolio_positions",
                parameters={"portfolio_id": portfolio_id},
                result={"positions": positions},
                start_time=start_time,
                cache_hit=False,
            )
            return positions
        except Exception as exc:
            self.debugger.log_error(exc)
            self._record_tool_metrics(
                tool_name="portfolio_positions",
                parameters={"portfolio_id": portfolio_id},
                result=None,
                start_time=start_time,
                cache_hit=False,
                status="error",
                error=str(exc),
            )
            raise

    async def _get_portfolio_metrics(self, portfolio_id: str) -> Dict[str, Any]:
        start_time = time.perf_counter()
        try:
            metrics = await self.portfolio.calculate_metrics(portfolio_id)
            self.debugger.log_step("portfolio_metrics_calculated", f"portfolio={portfolio_id}")
            self._record_tool_metrics(
                tool_name="portfolio_metrics",
                parameters={"portfolio_id": portfolio_id},
                result={"metrics": metrics},
                start_time=start_time,
                cache_hit=False,
            )
            return metrics
        except Exception as exc:
            self.debugger.log_error(exc)
            self._record_tool_metrics(
                tool_name="portfolio_metrics",
                parameters={"portfolio_id": portfolio_id},
                result=None,
                start_time=start_time,
                cache_hit=False,
                status="error",
                error=str(exc),
            )
            raise

    async def _get_portfolio_allocation(self, portfolio_id: str) -> Dict[str, Any]:
        start_time = time.perf_counter()
        try:
            allocation = await self.portfolio.analyze_allocation(portfolio_id)
            self.debugger.log_step("portfolio_allocation_analyzed", f"portfolio={portfolio_id}")
            self._record_tool_metrics(
                tool_name="portfolio_allocation",
                parameters={"portfolio_id": portfolio_id},
                result={"allocation": allocation},
                start_time=start_time,
                cache_hit=False,
            )
            return allocation
        except Exception as exc:
            self.debugger.log_error(exc)
            self._record_tool_metrics(
                tool_name="portfolio_allocation",
                parameters={"portfolio_id": portfolio_id},
                result=None,
                start_time=start_time,
                cache_hit=False,
                status="error",
                error=str(exc),
            )
            raise


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
        
        ticker_symbols = [entry.get("ticker", "") for entry in results if isinstance(entry, dict)]
        if ticker_symbols:
            lead = ticker_symbols[:3]
            tickers_summary = ", ".join(lead)
            if len(ticker_symbols) > len(lead):
                tickers_summary += ", ..."
            market_summary_text = f"Snapshots collected for {len(ticker_symbols)} tickers ({tickers_summary})"
        else:
            market_summary_text = "No ticker snapshots collected."

        market_summary = {
            "status": "success" if results else "error",
            "summary": market_summary_text,
            "tickers": results,
        }

        news_success = isinstance(market_news, dict) and market_news.get("success")
        news_results = market_news.get("results") if isinstance(market_news, dict) else None
        headline = None
        if isinstance(news_results, list) and news_results:
            first_article = news_results[0]
            if isinstance(first_article, dict):
                headline = first_article.get("title") or first_article.get("headline")
        news_summary_text = (
            headline
            or (market_news.get("message") if isinstance(market_news, dict) else None)
            or "No recent market headlines available."
        )

        articles_payload = {
            "count": len(news_results) if isinstance(news_results, list) else market_news.get("count") if isinstance(market_news, dict) else 0,
            "results": news_results if isinstance(news_results, list) else [],
            "success": bool(news_success),
        }
        if isinstance(market_news, dict) and market_news.get("message"):
            articles_payload["message"] = market_news.get("message")

        news_summary = {
            "status": "success" if news_success else "error",
            "summary": news_summary_text,
            "articles": articles_payload,
            "sentiment": {
                "success": bool(news_success),
                "message": news_summary_text,
            },
        }

        result_payload = {
            "workflow": "MarketResearchWorkflow",
            "query": query,
            "tickers": results,
            "market_news": market_news,
            "timestamp": "now",
            "rag": rag_context,
        }
        result_payload["agent_results"] = {
            "market_data": market_summary,
            "news_sentiment": news_summary,
        }
        return result_payload
    
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

        market_result = self._structure_market_result(
            ticker,
            {
                "current_price": price_data,
                "historical": {},
                "cache_hit": False,
            },
        )
        
        return {
            "workflow": "QuickQuoteWorkflow",
            "ticker": ticker,
            "price_data": price_data,
            "agent_results": {
                "market_data": market_result,
            },
            "market_overview": market_result,
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
