"""Agent that analyzes SEC filings and fundamentals."""

from typing import Any, Dict, List, Optional, Tuple

from src.agents.base_agent import BaseAgent
from src.tools.vector_tools import search_sec_filings
from src.tools.feature_tools import extract_financial_data, calculate_valuation_ratios


class FundamentalAnalysisAgent(BaseAgent):
    """Runs filing search, metric extraction, and valuation checks."""

    DEFAULT_METRICS: List[str] = [
        "revenue",
        "net_income",
        "eps",
        "cash_flow",
        "gross_margin",
        "operating_margin",
        "net_margin",
        "total_assets",
        "total_liabilities",
        "shareholders_equity",
        "roe",
        "roa",
    ]

    def __init__(self):
        instructions = """You are the Fundamental Analysis Agent for FinagentiX.

Your responsibilities:
1. Search SEC filings (10-K, 10-Q, 8-K) using vector search
2. Extract financial metrics:
   - Revenue, earnings, cash flow
   - Assets, liabilities, equity
   - Operating margins
3. Calculate valuation ratios:
   - P/E ratio (Price-to-Earnings)
   - P/B ratio (Price-to-Book)
   - EV/EBITDA proxies via pre-computed features when available
   - Dividend yield or PEG if provided
4. Analyze financial trends:
   - Revenue growth
   - Margin expansion/contraction
   - Return on equity (ROE)
5. Surface notable filing excerpts with citations

Available tools:
- search_sec_filings: Vector search for filing sections
- extract_financial_data: Retrieve structured metrics from Redis
- calculate_valuation_ratios: Compute valuation ratios
- Feature store metrics (if present) for trend calculations

When searching filings:
- Use semantic queries (e.g., "operating margin guidance")
- Focus on relevant sections (MD&A, financials, risk factors)
- Return excerpts with filing date and form type

Always:
- Cite specific SEC filings (form, date)
- Provide context for metrics
- Flag material changes or anomalies
- Mention data freshness assumptions
"""

        super().__init__(
            name="fundamental_analysis",
            instructions=instructions,
            tools=[],
        )

    async def run(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Retrieve filings, metrics, and valuation ratios for a ticker."""
        context = context or {}
        ticker = context.get("ticker") or self._extract_ticker(task)
        query = context.get("query") or task
        filing_type = context.get("filing_type")
        top_k = int(context.get("top_k", 5))
        metrics: List[str] = context.get("metrics") or self.DEFAULT_METRICS

        if not ticker:
            return {
                "status": "error",
                "message": "Provide a stock ticker (e.g., 'AAPL') for fundamental analysis.",
            }

        normalized_ticker = ticker.upper()
        cache_params = {
            "ticker": normalized_ticker,
            "query": query,
            "filing_type": filing_type,
            "top_k": top_k,
            "metrics": sorted(metrics),
        }
        cached_payload = self.check_tool_cache("fundamental_analysis_summary", cache_params)
        if cached_payload:
            return {**cached_payload, "cache_hit": True}

        filings_result, filings_cached = await self._search_filings(
            query=query,
            ticker=normalized_ticker,
            filing_type=filing_type,
            limit=top_k,
        )

        financials_result, financials_cached = await self._get_financials(
            ticker=normalized_ticker,
            metrics=metrics,
        )

        ratios_result, ratios_cached = await self._get_valuation(
            ticker=normalized_ticker,
        )

        summary = self._summarize(
            ticker=normalized_ticker,
            filings=filings_result,
            financials=financials_result,
            ratios=ratios_result,
        )

        payload = {
            "status": "success",
            "ticker": normalized_ticker,
            "query": query,
            "filing_type": filing_type,
            "filings": filings_result,
            "financials": financials_result,
            "valuation": ratios_result,
            "summary": summary,
            "cache_hit": filings_cached and financials_cached and ratios_cached,
        }

        self.cache_tool_output(
            "fundamental_analysis_summary",
            cache_params,
            payload,
            ttl=max(self.config.tool_cache_ttl, 86400),
        )
        return payload

    async def _search_filings(
        self,
        query: str,
        ticker: str,
        filing_type: Optional[str],
        limit: int,
    ) -> Tuple[Dict[str, Any], bool]:
        tool_name = "fundamental:search_sec_filings"
        params = {
            "query": query,
            "ticker": ticker,
            "filing_type": filing_type,
            "limit": limit,
        }
        cached = self.check_tool_cache(tool_name, params)
        if cached:
            return cached, True

        results = search_sec_filings(
            query=query,
            ticker=ticker,
            filing_type=filing_type,
            top_k=limit,
        )

        payload = {
            "success": True,
            "count": len(results),
            "results": results,
            "message": f"Found {len(results)} filing excerpts for {ticker}.",
        }

        if results:
            self.cache_tool_output(tool_name, params, payload, ttl=86400)
        return payload, False

    async def _get_financials(self, ticker: str, metrics: List[str]) -> Tuple[Dict[str, Any], bool]:
        tool_name = "fundamental:extract_financials"
        params = {"ticker": ticker, "metrics": sorted(metrics)}
        cached = self.check_tool_cache(tool_name, params)
        if cached:
            return cached, True

        data = extract_financial_data(ticker, metrics)
        success = bool(data)
        payload = {
            "success": success,
            "metrics": data,
            "message": "Financial metrics retrieved." if success else "No financial metrics available in cache.",
        }

        if success:
            self.cache_tool_output(tool_name, params, payload, ttl=86400)
        return payload, False

    async def _get_valuation(self, ticker: str) -> Tuple[Dict[str, Any], bool]:
        tool_name = "fundamental:calculate_valuation"
        params = {"ticker": ticker}
        cached = self.check_tool_cache(tool_name, params)
        if cached:
            return cached, True

        ratios = calculate_valuation_ratios(ticker)
        success = bool(ratios)
        payload = {
            "success": success,
            "ratios": ratios,
            "message": "Valuation ratios calculated." if success else "Valuation ratios unavailable.",
        }

        if success:
            self.cache_tool_output(tool_name, params, payload, ttl=86400)
        return payload, False

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
        ticker: str,
        filings: Dict[str, Any],
        financials: Dict[str, Any],
        ratios: Dict[str, Any],
    ) -> str:
        """Assemble human-readable summary from fundamentals."""
        parts: List[str] = []

        if filings.get("success"):
            count = filings.get("count", 0)
            if count:
                latest = filings["results"][0]
                parts.append(
                    f"Reviewing {count} filing excerpts; latest is {latest.get('filing_type', 'filing')} dated {latest.get('filing_date', 'N/A')}"
                )
            else:
                parts.append(f"No matching filings found for {ticker}.")
        elif filings.get("message"):
            parts.append(filings.get("message"))

        if financials.get("success"):
            metrics = financials.get("metrics", {})
            highlights = []
            for key in ["revenue", "net_income", "gross_margin", "roe"]:
                if key in metrics and metrics[key] is not None:
                    highlights.append(f"{key.replace('_', ' ').title()}: {metrics[key]}")
            if highlights:
                parts.append("Financial metrics: " + ", ".join(highlights))
        elif financials.get("message"):
            parts.append(financials.get("message"))

        if ratios.get("success"):
            ratio_vals = ratios.get("ratios", {})
            ratio_parts = []
            if ratio_vals.get("pe_ratio") is not None:
                ratio_parts.append(f"P/E {ratio_vals['pe_ratio']}")
            if ratio_vals.get("pb_ratio") is not None:
                ratio_parts.append(f"P/B {ratio_vals['pb_ratio']}")
            if ratio_vals.get("ps_ratio") is not None:
                ratio_parts.append(f"P/S {ratio_vals['ps_ratio']}")
            if ratio_parts:
                parts.append("Valuation: " + ", ".join(ratio_parts))
        elif ratios.get("message"):
            parts.append(ratios.get("message"))

        return " | ".join(parts) if parts else f"No fundamental data available for {ticker}."
