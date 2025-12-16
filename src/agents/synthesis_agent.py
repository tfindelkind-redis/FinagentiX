"""Agent that combines multi-agent results into a cohesive answer."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent


class SynthesisAgent(BaseAgent):
    """Summarizes findings, reconciles conflicts, and produces recommendations."""

    def __init__(self):
        instructions = """You are the Synthesis Agent for FinagentiX.

Your responsibilities:
1. Aggregate results from multiple specialized agents:
   - Market Data Agent: Stock prices, technical indicators
   - News Sentiment Agent: News articles, sentiment scores
   - Risk Assessment Agent: Risk metrics, volatility
   - Fundamental Analysis Agent: Financial data, SEC filings
2. Resolve conflicts and inconsistencies:
   - Different time ranges
   - Conflicting signals (e.g., positive news but high risk)
   - Data quality issues
3. Generate natural language summary:
   - Answer the original user question directly
   - Integrate insights from all agents
   - Highlight key findings
   - Provide actionable recommendations
4. Format data for presentation:
   - Structure bullet points for key insights
   - Include citations and sources
   - Add confidence indicators when possible

Always:
- Maintain factual accuracy
- Cite data sources
- Note when data is cached or stale
- Highlight high-confidence vs low-confidence insights
- Use clear, professional language
"""

        super().__init__(
            name="synthesis",
            instructions=instructions,
            tools=[],
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    async def run(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Combine agent outputs into a structured response."""
        context = context or {}
        agent_results: Dict[str, Any] = context.get("agent_results") or {}

        if not agent_results:
            return {
                "status": "error",
                "message": "No agent results provided for synthesis.",
            }

        ticker = context.get("ticker") or self._infer_ticker(agent_results)

        findings = self._collect_findings(agent_results, ticker)
        recommendations = self._generate_recommendations(agent_results, ticker)
        sources = self._collect_sources(agent_results)

        structured_answer = self._compose_answer(task, ticker, findings, recommendations)
        llm_answer = await self._llm_synthesize(
            task=task,
            ticker=ticker,
            findings=findings,
            recommendations=recommendations,
            sources=sources,
        )

        final_answer = llm_answer or structured_answer

        return {
            "status": "success",
            "answer": final_answer,
            "structured_answer": structured_answer,
            "llm_used": bool(llm_answer),
            "key_findings": findings,
            "recommendations": recommendations,
            "sources": sources,
        }

    @staticmethod
    def _infer_ticker(agent_results: Dict[str, Any]) -> Optional[str]:
        for key in ("market_data", "fundamental_analysis", "risk_assessment", "news_sentiment"):
            result = agent_results.get(key)
            if isinstance(result, dict) and result.get("ticker"):
                return result.get("ticker")
        return None

    def _collect_findings(self, agent_results: Dict[str, Any], ticker: Optional[str]) -> List[str]:
        findings: List[str] = []

        market = agent_results.get("market_data")
        if isinstance(market, dict) and market.get("status") == "success":
            summary = market.get("summary") or market.get("current_price", {}).get("message")
            if summary:
                findings.append(f"Market data: {summary}")

        news = agent_results.get("news_sentiment")
        if isinstance(news, dict) and news.get("status") == "success":
            news_summary = news.get("summary")
            if news_summary:
                findings.append(f"News sentiment: {news_summary}")
            elif news.get("sentiment", {}).get("message"):
                findings.append(f"News sentiment: {news['sentiment']['message']}")

        risk = agent_results.get("risk_assessment")
        if isinstance(risk, dict) and risk.get("status") == "success":
            insights: List[str] = risk.get("insights") or []
            for insight in insights[:2]:
                findings.append(f"Risk: {insight}")

        fundamentals = agent_results.get("fundamental_analysis")
        if isinstance(fundamentals, dict) and fundamentals.get("status") == "success":
            fund_summary = fundamentals.get("summary")
            if fund_summary:
                findings.append(f"Fundamentals: {fund_summary}")
            elif fundamentals.get("message"):
                findings.append(f"Fundamentals: {fundamentals['message']}")

        portfolio = agent_results.get("portfolio_review")
        if isinstance(portfolio, dict):
            portfolio_summary = portfolio.get("summary")
            if portfolio_summary:
                findings.append(f"Portfolio: {portfolio_summary}")
            elif portfolio.get("status") == "error":
                findings.append("Portfolio: Unable to retrieve portfolio analytics.")

        if not findings and ticker:
            findings.append(f"No structured findings were produced for {ticker}.")
        elif not findings:
            findings.append("No structured findings were produced.")

        return findings

    def _generate_recommendations(
        self,
        agent_results: Dict[str, Any],
        ticker: Optional[str],
    ) -> List[str]:
        recommendations: List[str] = []

        risk = agent_results.get("risk_assessment")
        if isinstance(risk, dict) and risk.get("status") == "success":
            insights = risk.get("insights") or []
            if insights:
                recommendations.append(insights[0])

        news = agent_results.get("news_sentiment")
        if isinstance(news, dict) and news.get("status") == "success":
            impact = news.get("impact")
            if isinstance(impact, dict) and impact.get("success"):
                recommendations.append(impact.get("recommendation") or impact.get("message", "Monitor news developments."))

        portfolio = agent_results.get("portfolio_review")
        if isinstance(portfolio, dict) and portfolio.get("status") == "success":
            allocation = portfolio.get("allocation")
            if isinstance(allocation, dict) and allocation.get("rebalance_suggestion"):
                recommendations.append(allocation.get("rebalance_suggestion"))
            elif portfolio.get("summary"):
                recommendations.append(f"Portfolio insight: {portfolio['summary']}")

        if not recommendations:
            if ticker:
                recommendations.append(f"Gather additional signals before acting on {ticker}.")
            else:
                recommendations.append("Gather additional signals before acting.")

        return recommendations

    def _collect_sources(self, agent_results: Dict[str, Any]) -> Dict[str, Any]:
        sources: Dict[str, Any] = {}

        market = agent_results.get("market_data")
        if isinstance(market, dict) and market.get("current_price"):
            price = market["current_price"]
            sources["market_data"] = {
                "as_of": price.get("date"),
                "metric": price.get("metric"),
                "cache_hit": market.get("cache_hit"),
            }

        news = agent_results.get("news_sentiment")
        if isinstance(news, dict) and news.get("articles"):
            sources["news_sentiment"] = {
                "articles": news.get("articles", {}).get("count"),
                "cache_hit": news.get("cache_hit"),
            }

        risk = agent_results.get("risk_assessment")
        if isinstance(risk, dict):
            sources["risk_assessment"] = {
                "cache_hit": risk.get("cache_hit"),
                "confidence": risk.get("confidence"),
                "benchmark": risk.get("benchmark"),
            }

        fundamentals = agent_results.get("fundamental_analysis")
        if isinstance(fundamentals, dict):
            filing_count = 0
            filings = fundamentals.get("filings")
            if isinstance(filings, dict):
                filing_count = filings.get("count", 0)
            sources["fundamental_analysis"] = {
                "filings": filing_count,
                "cache_hit": fundamentals.get("cache_hit"),
            }

        portfolio = agent_results.get("portfolio_review")
        if isinstance(portfolio, dict):
            positions = portfolio.get("positions")
            holding_count = 0
            if isinstance(positions, dict):
                holdings = positions.get("positions") or positions.get("holdings")
                if isinstance(holdings, list):
                    holding_count = len(holdings)
            sources["portfolio_review"] = {
                "holdings": holding_count,
                "status": portfolio.get("status"),
            }

        return sources

    @staticmethod
    def _compose_answer(
        task: str,
        ticker: Optional[str],
        findings: List[str],
        recommendations: List[str],
    ) -> str:
        direct = findings[0] if findings else "No findings available."

        header = f"Answer: {direct}"

        key_lines = "\n".join(f"- {finding}" for finding in findings)
        rec_lines = "\n".join(f"- {rec}" for rec in recommendations)

        ticker_line = f"Combined view for {ticker}." if ticker else "Combined view across available agents."

        sections = [
            header,
            "",
            ticker_line,
            "",
            "Key Findings:",
            key_lines,
            "",
            "Recommendations:",
            rec_lines,
        ]

        return "\n".join(line for line in sections if line is not None)

    async def _llm_synthesize(
        self,
        task: str,
        ticker: Optional[str],
        findings: List[str],
        recommendations: List[str],
        sources: Dict[str, Any],
    ) -> Optional[str]:
        """Use Azure OpenAI to craft a polished summary when possible."""
        if not findings and not recommendations:
            return None

        try:
            payload = {
                "query": task,
                "ticker": ticker,
                "findings": findings,
                "recommendations": recommendations,
                "sources": sources,
            }
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are FinagentiX's synthesis assistant. Produce concise, factual investment responses. "
                        "Always ground statements in supplied findings and flag uncertainties."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "User query: {query}\n"
                        "Ticker: {ticker}\n\n"
                        "Key findings:\n{findings}\n\n"
                        "Recommendations:\n{recommendations}\n\n"
                        "Sources:\n{sources}\n".format(
                            query=task,
                            ticker=ticker or "N/A",
                            findings="\n".join(f"- {item}" for item in findings) or "- None",
                            recommendations="\n".join(f"- {item}" for item in recommendations) or "- None",
                            sources=json.dumps(sources, default=str) if sources else "{}",
                        )
                    ),
                },
            ]

            response = await asyncio.to_thread(
                self.openai.chat.completions.create,
                model=self.config.azure_openai.chat_deployment,
                temperature=0.2,
                max_tokens=600,
                messages=messages,
            )
            if response and response.choices:
                return response.choices[0].message.content.strip()
        except Exception as error:  # pragma: no cover - defensive log
            self.logger.warning("LLM synthesis failed: %s", error)
        return None
