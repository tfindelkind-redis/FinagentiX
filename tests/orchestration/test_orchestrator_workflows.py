import pytest
from types import SimpleNamespace

from src.agents.orchestrator_agent import OrchestratorAgent
from src.agents.plugins.portfolio_plugin import PortfolioPlugin
from src.agents.plugins.news_sentiment_plugin import NewsSentimentPlugin
from src.agents.synthesis_agent import SynthesisAgent
from src.orchestration.workflows import InvestmentAnalysisWorkflow


class FakeToolCache:
    """Minimal in-memory cache used to avoid Redis in tests."""

    def __init__(self):
        self._store = {}

    def get(self, tool_name: str, **params):
        return self._store.get((tool_name, tuple(sorted(params.items()))))

    def set(self, tool_name: str, output, ttl_seconds=None, **params):
        self._store[(tool_name, tuple(sorted(params.items())))] = output


class FakeRedis:
    """Stub Redis client with minimal in-memory behaviour."""

    def __init__(self):
        self._kv = {}

    def get(self, key):
        return self._kv.get(key)

    def setex(self, key, _ttl, value):
        self._kv[key] = value
        return True

    def hincrby(self, key, field, amount):
        stats = self._kv.setdefault(key, {})
        if not isinstance(stats, dict):
            stats = {}
            self._kv[key] = stats
        stats[field] = stats.get(field, 0) + amount
        return stats[field]

    def delete(self, *keys):
        removed = 0
        for key in keys:
            if key in self._kv:
                del self._kv[key]
                removed += 1
        return removed

    def scan_iter(self, pattern, count=10):
        from fnmatch import fnmatch

        for key in list(self._kv.keys()):
            if fnmatch(str(key), pattern):
                yield key


@pytest.fixture(autouse=True)
def patch_agent_config(monkeypatch):
    dummy_config = SimpleNamespace(
        azure_openai=SimpleNamespace(
            endpoint="https://example.azure.com",
            api_key="test-key",
            api_version="2024-08-01-preview",
            embedding_deployment="text-embedding-3-large",
            chat_deployment="gpt-4o",
        ),
        redis=SimpleNamespace(
            host="localhost",
            port=6379,
            password="pass",
            ssl=False,
            decode_responses=False,
        ),
        max_iterations=3,
        timeout_seconds=30,
        enable_semantic_cache=False,
        enable_tool_cache=False,
        enable_routing_cache=False,
        semantic_cache_ttl=0,
        tool_cache_ttl=0,
        routing_cache_ttl=0,
        vector_top_k=3,
        similarity_threshold=0.7,
    )
    monkeypatch.setattr("src.agents.config._config", dummy_config, raising=False)
    monkeypatch.setattr("src.agents.config.get_config", lambda: dummy_config)
    monkeypatch.setattr("src.agents.orchestrator_agent.ToolCache", FakeToolCache)
    monkeypatch.setattr("src.orchestration.workflows.ToolCache", FakeToolCache)
    monkeypatch.setattr("src.orchestration.workflows.get_redis_client", lambda: FakeRedis())
    return dummy_config


@pytest.fixture
def orchestrator_agent(monkeypatch):
    async def fake_embedding(self, _query):
        return [0.1, 0.2, 0.3]

    async def fake_llm(self, **_kwargs):
        return None

    monkeypatch.setattr(OrchestratorAgent, "_create_embedding", fake_embedding)
    monkeypatch.setattr(SynthesisAgent, "_llm_synthesize", fake_llm)

    agent = OrchestratorAgent()
    agent.tool_cache = FakeToolCache()
    agent._redis_client = FakeRedis()
    return agent


@pytest.mark.asyncio
async def test_portfolio_workflow_synthesis(monkeypatch, orchestrator_agent):
    def select_portfolio(self, _route, _derived):
        return "PortfolioReviewWorkflow", "forced"

    async def fake_positions(self, portfolio_id="default"):
        return {
            "portfolio_id": portfolio_id,
            "success": True,
            "positions": [
                {"ticker": "AAPL", "allocation_pct": 55},
                {"ticker": "MSFT", "allocation_pct": 45},
            ],
            "total_value": 120000,
        }

    async def fake_metrics(self, portfolio_id="default"):
        return {
            "portfolio_id": portfolio_id,
            "success": True,
            "summary": "Year-to-date return 8%.",
        }

    async def fake_allocation(self, portfolio_id="default"):
        return {
            "portfolio_id": portfolio_id,
            "success": True,
            "top_sector": "Technology",
            "rebalance_suggestion": "Trim overweight tech.",
        }

    monkeypatch.setattr(OrchestratorAgent, "_select_workflow", select_portfolio)
    monkeypatch.setattr(PortfolioPlugin, "get_positions", fake_positions)
    monkeypatch.setattr(PortfolioPlugin, "calculate_metrics", fake_metrics)
    monkeypatch.setattr(PortfolioPlugin, "analyze_allocation", fake_allocation)

    response = await orchestrator_agent.run("Review my portfolio", context={"portfolio_id": "alpha"})

    assert response["workflow"] == "PortfolioReviewWorkflow"
    assert response["synthesis"]["status"] == "success"
    assert any(f.startswith("Portfolio:") for f in response["synthesis"]["key_findings"])
    assert response["synthesis"]["sources"]["portfolio_review"]["holdings"] == 2
    assert "Trim overweight tech." in " ".join(response["synthesis"]["recommendations"])


@pytest.mark.asyncio
async def test_market_research_workflow_synthesis(monkeypatch, orchestrator_agent):
    def select_market_research(self, _route, _derived):
        return "MarketResearchWorkflow", "forced"

    async def fake_ticker_overview(self, ticker: str):
        return {
            "ticker": ticker,
            "price": {"success": True, "message": f"{ticker} price stable"},
            "news": {"success": True, "results": []},
        }

    async def fake_recent_news(self, limit=10):
        return {
            "success": True,
            "count": 1,
            "results": [
                {"title": "Markets rally as tech leads", "sentiment": "positive"}
            ],
            "message": "Markets rallied today.",
        }

    monkeypatch.setattr(OrchestratorAgent, "_select_workflow", select_market_research)
    monkeypatch.setattr(
        "src.orchestration.workflows.MarketResearchWorkflow._get_ticker_overview",
        fake_ticker_overview,
    )
    monkeypatch.setattr(NewsSentimentPlugin, "get_recent_news", fake_recent_news)

    response = await orchestrator_agent.run("What is happening in tech?")

    assert response["workflow"] == "MarketResearchWorkflow"
    assert response["synthesis"]["status"] == "success"
    assert any(f.startswith("Market data:") for f in response["synthesis"]["key_findings"])
    assert any(f.startswith("News sentiment:") for f in response["synthesis"]["key_findings"])
    assert response["synthesis"]["sources"]["news_sentiment"]["articles"] == 1


@pytest.mark.asyncio
async def test_reuses_cached_workflow_outcome(monkeypatch, orchestrator_agent):
    def select_investment(self, _route, _derived):
        return "InvestmentAnalysisWorkflow", "forced"

    call_counter = {"count": 0}

    async def fake_execute(self, ticker: str, **_params):
        call_counter["count"] += 1
        return {
            "workflow": "InvestmentAnalysisWorkflow",
            "ticker": ticker,
            "response": f"Cached analysis for {ticker}",
        }

    monkeypatch.setattr(OrchestratorAgent, "_select_workflow", select_investment)
    monkeypatch.setattr(InvestmentAnalysisWorkflow, "execute", fake_execute)

    response_first = await orchestrator_agent.run("Analyze AAPL", context={"ticker": "AAPL"})
    assert response_first["cached"] is False
    assert call_counter["count"] == 1

    response_second = await orchestrator_agent.run("Analyze AAPL", context={"ticker": "AAPL"})
    assert response_second["cached"] is True
    assert response_second["cache_hits"] == 1
    assert response_second["answer"].startswith("Cached analysis")
    assert call_counter["count"] == 1
