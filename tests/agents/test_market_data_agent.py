"""Unit tests for the MarketDataAgent orchestration logic."""

import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.agents.market_data_agent import MarketDataAgent
from src.agents.config import AgentConfig, AzureOpenAIConfig, RedisConfig


class StubMarketDataPlugin:
    """Stub implementation of MarketDataPlugin for agent tests."""

    def __init__(self):
        self.calls = []

    async def get_stock_price(self, ticker: str, metric: str = "close"):
        self.calls.append(("get_stock_price", ticker.upper(), metric))
        return {
            "success": True,
            "ticker": ticker.upper(),
            "metric": metric,
            "value": 150.25,
            "timestamp": 1_704_000_000_000,
            "date": "2024-01-02 16:00:00",
            "message": f"{ticker.upper()} price message",
        }

    async def get_price_history(self, ticker: str, days: int = 30, metric: str = "close"):
        self.calls.append(("get_price_history", ticker.upper(), days, metric))
        history = [
            {
                "timestamp": 1_704_000_000_000 - idx * 86_400_000,
                "date": "2024-01-01",
                "value": 140.0 + idx,
            }
            for idx in range(30)
        ]
        return {
            "success": True,
            "ticker": ticker.upper(),
            "metric": metric,
            "days": days,
            "data": list(reversed(history)),
            "stats": {
                "count": len(history),
                "first": history[-1]["value"],
                "last": history[0]["value"],
            },
            "message": "History ok",
        }

    async def get_price_change(self, ticker: str, days: int = 30, metric: str = "close"):
        self.calls.append(("get_price_change", ticker.upper(), days, metric))
        return {
            "success": True,
            "ticker": ticker.upper(),
            "metric": metric,
            "days": days,
            "trend": "uptrend",
            "change_pct": 3.2,
            "message": f"{ticker.upper()} change message",
        }

    async def get_volume_analysis(self, ticker: str, days: int = 30):
        self.calls.append(("get_volume_analysis", ticker.upper(), days))
        return {
            "success": True,
            "ticker": ticker.upper(),
            "days": days,
            "current_volume": 1_200_000,
            "avg_volume": 1_000_000,
            "message": f"{ticker.upper()} volume message",
        }

    async def get_technical_indicators(self, ticker: str, metric: str = "close"):
        self.calls.append(("get_technical_indicators", ticker.upper(), metric))
        return {
            "success": True,
            "ticker": ticker.upper(),
            "metric": metric,
            "momentum": "positive",
            "trend": "bullish",
            "rsi": 62.0,
            "macd": {
                "line": 1.5,
                "signal": 0.5,
                "histogram": 1.0,
            },
            "message": "Trend bullish, Momentum positive, MACD above signal",
        }


@pytest.fixture
def configured_agent(monkeypatch):
    """Create a MarketDataAgent with deterministic configuration and plugin stub."""

    config = AgentConfig(
        azure_openai=AzureOpenAIConfig(
            endpoint="https://example.openai.azure.com",
            api_key="test-key",
            api_version="2024-08-01-preview",
            embedding_deployment="text-embedding-3-large",
            chat_deployment="gpt-4o",
        ),
        redis=RedisConfig(
            host="localhost",
            port=6379,
            password="test",
            ssl=False,
            decode_responses=True,
        ),
        enable_semantic_cache=False,
        enable_tool_cache=False,
        enable_routing_cache=False,
        tool_cache_ttl=0,
    )

    monkeypatch.setattr("src.agents.config._config", config, raising=False)
    monkeypatch.setattr("src.agents.config.get_config", lambda: config)

    agent = MarketDataAgent()
    stub = StubMarketDataPlugin()
    agent._plugin = stub
    return agent, stub


@pytest.mark.asyncio
async def test_run_aggregates_market_data(configured_agent):
    """MarketDataAgent.run should collect and structure market data outputs."""

    agent, stub = configured_agent

    result = await agent.run("Please analyze AAPL", context={"ticker": "AAPL"})

    assert result["status"] == "success"
    assert result["ticker"] == "AAPL"
    assert result["cache_hit"] is False

    summary = result["summary"]
    assert "price message" in summary
    assert "change message" in summary
    assert "volume message" in summary
    assert "Trend bullish" in summary

    signals = result["signals"]
    assert signals["trend"] == "uptrend"
    assert signals["momentum"] == "positive"
    assert signals["macd_cross"] == "bullish"
    assert signals["rsi"] == 62.0

    metadata = result["metadata"]
    assert metadata["as_of"] == "2024-01-02 16:00:00"
    assert metadata["history_points"] == 30

    assert {call[0] for call in stub.calls} == {
        "get_stock_price",
        "get_price_history",
        "get_price_change",
        "get_volume_analysis",
        "get_technical_indicators",
    }
