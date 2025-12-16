"""Agent responsible for computing risk metrics using Redis data."""

from typing import Any, Dict, List, Optional, Tuple

from src.agents.base_agent import BaseAgent
from src.agents.plugins.risk_analysis_plugin import RiskAnalysisPlugin


class RiskAssessmentAgent(BaseAgent):
    """
    Specialized agent for risk analysis and portfolio assessment.
    
    Calculates various risk metrics using time series data from Redis
    and provides risk management recommendations.
    """
    
    def __init__(self):
        instructions = """You are the Risk Assessment Agent for FinagentiX.

Your responsibilities:
1. Calculate volatility metrics:
   - Historical volatility (standard deviation)
   - Implied volatility
   - Beta (relative to market)
   - Value at Risk (VaR)
   - Conditional VaR (CVaR)
2. Analyze portfolio risk:
   - Total portfolio volatility
   - Asset correlations
   - Concentration risk
   - Sector exposure
3. Compute risk-adjusted returns:
   - Sharpe ratio
   - Sortino ratio
   - Information ratio
4. Provide risk management recommendations

Available tools:
- calculate_volatility: Compute historical volatility
- calculate_var: Value at Risk calculation
- get_correlation_matrix: Asset correlations
- calculate_beta: Beta relative to benchmark
- get_risk_metrics: Comprehensive risk analysis

Always:
- Use appropriate time windows for calculations
- Consider market regime (bull/bear)
- Adjust for outliers and market events
- Provide risk scores with context
- Compare to benchmarks and peers
"""
        
        super().__init__(
            name="risk_assessment",
            instructions=instructions,
            tools=[],
        )
        self._plugin: Optional[RiskAnalysisPlugin] = None

    @property
    def plugin(self) -> RiskAnalysisPlugin:
        """Lazy initialize risk analysis plugin."""
        if self._plugin is None:
            self._plugin = RiskAnalysisPlugin(self.redis)
        return self._plugin

    async def run(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Compute risk metrics (VaR, beta, drawdown, stress scenarios)."""
        context = context or {}
        tickers: List[str] = context.get("tickers") or []
        ticker = (tickers[0] if tickers else None) or self._extract_ticker(task)
        confidence = float(context.get("confidence", 0.95))
        holding_period = int(context.get("holding_period", 1))
        benchmark = context.get("benchmark", "SPY")
        history_days = int(context.get("days", 252))
        stress_scenarios = context.get("scenarios")

        if not ticker:
            return {
                "status": "error",
                "message": "Provide at least one ticker symbol for risk assessment.",
            }

        cache_params = {
            "ticker": ticker.upper(),
            "confidence": confidence,
            "holding_period": holding_period,
            "benchmark": benchmark,
            "days": history_days,
            "scenarios": stress_scenarios or [],
        }
        cached_payload = self.check_tool_cache("risk_assessment_summary", cache_params)
        if cached_payload:
            return {**cached_payload, "cache_hit": True}

        var_result, var_cached = await self._get_var(ticker, confidence, history_days, holding_period)
        beta_result, beta_cached = await self._get_beta(ticker, benchmark, history_days)
        drawdown_result, drawdown_cached = await self._get_drawdown(ticker, history_days)
        stress_result, stress_cached = await self._get_stress_test(ticker, stress_scenarios)

        insights = self._summarize(var_result, beta_result, drawdown_result, stress_result)

        payload = {
            "status": "success",
            "ticker": ticker.upper(),
            "confidence": confidence,
            "holding_period": holding_period,
            "benchmark": benchmark,
            "days": history_days,
            "var": var_result,
            "beta": beta_result,
            "drawdown": drawdown_result,
            "stress_test": stress_result,
            "insights": insights,
            "cache_hit": var_cached and beta_cached and drawdown_cached and stress_cached,
        }

        self.cache_tool_output("risk_assessment_summary", cache_params, payload, ttl=self.config.tool_cache_ttl)
        return payload

    async def _get_var(
        self,
        ticker: str,
        confidence: float,
        days: int,
        holding_period: int,
    ) -> Tuple[Dict[str, Any], bool]:
        tool_name = "risk_assessment:calculate_var"
        params = {
            "ticker": ticker.upper(),
            "confidence": confidence,
            "days": days,
            "holding_period": holding_period,
        }
        cached = self.check_tool_cache(tool_name, params)
        if cached:
            return cached, True

        result = await self.plugin.calculate_var(
            ticker,
            confidence=confidence,
            days=days,
            holding_period=holding_period,
        )
        if result.get("success"):
            self.cache_tool_output(tool_name, params, result, ttl=86400)
        return result, False

    async def _get_beta(self, ticker: str, benchmark: str, days: int) -> Tuple[Dict[str, Any], bool]:
        tool_name = "risk_assessment:calculate_beta"
        params = {"ticker": ticker.upper(), "benchmark": benchmark.upper(), "days": days}
        cached = self.check_tool_cache(tool_name, params)
        if cached:
            return cached, True

        result = await self.plugin.calculate_beta(ticker, market_ticker=benchmark, days=days)
        if result.get("success"):
            self.cache_tool_output(tool_name, params, result, ttl=86400)
        return result, False

    async def _get_drawdown(self, ticker: str, days: int) -> Tuple[Dict[str, Any], bool]:
        tool_name = "risk_assessment:calculate_drawdown"
        params = {"ticker": ticker.upper(), "days": days}
        cached = self.check_tool_cache(tool_name, params)
        if cached:
            return cached, True

        result = await self.plugin.calculate_drawdown(ticker, days=days)
        if result.get("success"):
            self.cache_tool_output(tool_name, params, result, ttl=86400)
        return result, False

    async def _get_stress_test(
        self,
        ticker: str,
        scenarios: Optional[List[str]],
    ) -> Tuple[Dict[str, Any], bool]:
        normalized_scenarios = sorted(scenarios) if scenarios else []
        tool_name = "risk_assessment:stress_test"
        params = {"ticker": ticker.upper(), "scenarios": normalized_scenarios}
        cached = self.check_tool_cache(tool_name, params)
        if cached:
            return cached, True

        result = await self.plugin.stress_test(ticker, scenarios=normalized_scenarios or None)
        if result.get("success"):
            self.cache_tool_output(tool_name, params, result, ttl=43200)
        return result, False

    @staticmethod
    def _extract_ticker(query: str) -> Optional[str]:
        import re

        match = re.search(r"\b([A-Z]{2,5})\b", query.upper())
        return match.group(1) if match else None

    @staticmethod
    def _summarize(
        var: Dict[str, Any],
        beta: Dict[str, Any],
        drawdown: Dict[str, Any],
        stress: Dict[str, Any],
    ) -> List[str]:
        """Compile concise insights from component results."""
        insights: List[str] = []

        if var.get("success"):
            insights.append(var.get("message", ""))
        if beta.get("success"):
            insights.append(beta.get("message", ""))
        if drawdown.get("success"):
            drawdown_msg = drawdown.get("message") or (
                f"Max drawdown: {drawdown.get('max_drawdown_pct', 'N/A')}%"
            )
            insights.append(drawdown_msg)
        if stress.get("success"):
            insights.append(stress.get("message", ""))

        return [msg for msg in insights if msg]
