import pytest
from fastapi.testclient import TestClient

from src.api import dependencies as deps
from src.api import main as api_main


class StubSemanticCache:
    def __init__(self):
        self.get_return = None
        self.set_calls = []
        self.stats = {
            "total_entries": 3,
            "total_cache_hits": 2,
            "total_tokens_saved": 1500,
            "similarity_threshold": 0.9,
            "index_name": "idx:semantic_cache",
        }
        self.cleared_patterns = []
        self.auto_cache = False
        self.auto_cache_similarity = 0.99
        self.last_cached_entry = None

    def enable_auto_cache(self, similarity: float = 0.99):
        self.auto_cache = True
        self.auto_cache_similarity = similarity

    def get(self, query, query_embedding):
        if self.get_return is not None:
            return self.get_return
        if self.auto_cache and self.last_cached_entry:
            return {
                "cache_hit": True,
                "response": self.last_cached_entry["response"],
                "model": self.last_cached_entry["model"],
                "similarity": self.auto_cache_similarity,
                "cached_query": self.last_cached_entry["query"],
            }
        return self.get_return

    def set(self, *, query, query_embedding, response, model, tokens_saved):
        entry = {
            "query": query,
            "response": response,
            "model": model,
            "tokens_saved": tokens_saved,
        }
        self.set_calls.append(entry)
        self.last_cached_entry = entry

    def get_stats(self):
        return self.stats

    def clear(self, pattern=None):
        self.cleared_patterns.append(pattern)
        return 0


class StubContextualMemory:
    def __init__(self):
        self.messages = []
        self.context = {
            "session": {},
            "history": [],
        }

    def get_context(self, user_id, include_history=False):
        return self.context

    def add_message(self, user_id, role, content, metadata=None):
        self.messages.append((user_id, role, content, metadata or {}))


class StubSemanticRouter:
    def __init__(self):
        self.route = {
            "route_id": "investment_analysis",
            "workflow": "InvestmentAnalysisWorkflow",
            "agents": ["market_data", "risk_analysis"],
            "matched_via": "pattern",
            "similarity": 0.93,
        }
        self.routes = [
            {
                "workflow": "InvestmentAnalysisWorkflow",
                "description": "Default investment analysis",
            }
        ]
        self.record_calls = []
        self.last_query = None
        self.last_embedding = None

    def find_route(self, query, query_embedding=None, top_k=3):
        self.last_query = query
        self.last_embedding = query_embedding
        return self.route

    def record_route(self, **kwargs):
        self.record_calls.append(kwargs)

    def get_stats(self):
        return {"total_routes": len(self.routes)}

    def get_all_routes(self):
        return self.routes


class StubEmbeddingsClient:
    def __init__(self, embedding):
        self._embedding = embedding

    async def create(self, input, model):
        class Response:
            def __init__(self, vector):
                class Datum:
                    def __init__(self, value):
                        self.embedding = value

                self.data = [Datum(vector)]

        return Response(self._embedding)


class StubOpenAIClient:
    def __init__(self):
        self.embeddings = StubEmbeddingsClient([0.1, 0.2, 0.3])


class StubMarketDataAgent:
    def __init__(self):
        self.agent = object()


class StubSequentialOrchestration:
    def __init__(self, agents, metrics_collector):
        self.agents = agents
        self.metrics = metrics_collector

    async def execute(self, initial_query, context):
        return {"final_result": "Stub orchestrated result"}


class StubInvestmentWorkflow:
    last_call = None

    def __init__(self, *args, **kwargs):
        StubInvestmentWorkflow.last_call = None

    async def execute(self, *, ticker, **kwargs):
        StubInvestmentWorkflow.last_call = {"ticker": ticker}
        return {
            "workflow": "InvestmentAnalysisWorkflow",
            "ticker": ticker,
            "recommendation": {
                "action": "buy",
                "confidence": "high",
                "signals": ["momentum"],
                "summary": "Strong fundamentals",
            },
        }


class StubQuickQuoteWorkflow:
    async def execute(self, *, ticker, **kwargs):
        return {
            "workflow": "QuickQuoteWorkflow",
            "response": f"Quote for {ticker}",
        }


class StubPortfolioWorkflow:
    async def execute(self, *, portfolio_id, **kwargs):
        return {
            "workflow": "PortfolioReviewWorkflow",
            "positions": {
                "success": True,
                "total_value": 100000,
                "positions": ["AAPL", "MSFT"],
            },
        }


class StubMarketResearchWorkflow:
    async def execute(self, *, query, tickers=None, **kwargs):
        return {
            "workflow": "MarketResearchWorkflow",
            "response": f"Research on {tickers or 'market'}",
        }


class StubDocumentStore:
    def __init__(self):
        self.ingest_calls = []
        self.search_calls = []
        self.deleted_ticker = None

    async def ingest_document(self, **kwargs):
        self.ingest_calls.append(kwargs)
        return ["chunk-1", "chunk-2"]

    async def search(self, **kwargs):
        self.search_calls.append(kwargs)
        return [
            {
                "content": "Stub content",
                "score": 0.92,
                "metadata": {"ticker": "AAPL"},
            }
        ]

    async def get_stats(self):
        return {"total_documents": 1}

    async def delete_by_ticker(self, ticker):
        self.deleted_ticker = ticker
        return 2


class StubRAGResult:
    def __init__(self, question):
        self.query = question
        self.answer = "Stub answer"
        self.confidence = "high"
        self.sources = [
            {
                "title": "Stub source",
                "doc_type": "10-K",
                "filing_date": "2024-01-01",
            }
        ]


class StubRAGRetriever:
    def __init__(self):
        self.last_question = None

    async def ask(self, *, question, ticker=None, doc_type=None, source=None, top_k=5):
        self.last_question = {
            "question": question,
            "ticker": ticker,
            "doc_type": doc_type,
            "source": source,
            "top_k": top_k,
        }
        return StubRAGResult(question)


class StubRedisClient:
    def ping(self):
        return True


@pytest.fixture
def app_client(monkeypatch):
    stub_cache = StubSemanticCache()
    stub_memory = StubContextualMemory()
    stub_router = StubSemanticRouter()
    stub_openai = StubOpenAIClient()
    stub_document_store = StubDocumentStore()
    stub_rag = StubRAGRetriever()

    app_api = api_main.app

    app_api.dependency_overrides[deps.get_semantic_cache] = lambda: stub_cache
    app_api.dependency_overrides[deps.get_contextual_memory] = lambda: stub_memory
    app_api.dependency_overrides[deps.get_semantic_router] = lambda: stub_router
    app_api.dependency_overrides[deps.get_azure_openai_client] = lambda: stub_openai
    app_api.dependency_overrides[deps.get_document_store] = lambda: stub_document_store
    app_api.dependency_overrides[deps.get_rag_retriever] = lambda: stub_rag

    if hasattr(api_main, "MarketDataAgentSK"):
        monkeypatch.setattr(api_main, "MarketDataAgentSK", StubMarketDataAgent)
    if hasattr(api_main, "SequentialOrchestration"):
        monkeypatch.setattr(api_main, "SequentialOrchestration", StubSequentialOrchestration)
    monkeypatch.setattr(api_main, "InvestmentAnalysisWorkflow", StubInvestmentWorkflow)
    monkeypatch.setattr(api_main, "QuickQuoteWorkflow", StubQuickQuoteWorkflow)
    monkeypatch.setattr(api_main, "PortfolioReviewWorkflow", StubPortfolioWorkflow)
    monkeypatch.setattr(api_main, "MarketResearchWorkflow", StubMarketResearchWorkflow)
    monkeypatch.setattr("src.redis.client.get_redis_client", lambda: StubRedisClient())

    client = TestClient(app_api)

    yield {
        "client": client,
        "cache": stub_cache,
        "memory": stub_memory,
        "router": stub_router,
        "document_store": stub_document_store,
        "rag": stub_rag,
    }

    app_api.dependency_overrides.clear()


def test_health_endpoint(app_client):
    client = app_client["client"]

    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"healthy", "degraded"}
    assert "services" in payload
    assert "redis" in payload["services"]


def test_enhanced_query_cache_hit(app_client):
    client = app_client["client"]
    cache = app_client["cache"]

    cache.get_return = {
        "cache_hit": True,
        "response": "Cached response",
        "similarity": 0.98,
        "query_time_ms": 2.5,
    }

    response = client.post(
        "/api/query/enhanced",
        json={"query": "Price for AAPL", "user_id": "user-1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["response"] == "Cached response"
    assert payload["overall_cache_hit"] is True
    assert cache.set_calls == []


def test_enhanced_query_executes_workflow(app_client):
    client = app_client["client"]
    cache = app_client["cache"]
    router = app_client["router"]

    cache.get_return = None

    response = client.post(
        "/api/query/enhanced",
        json={"query": "Analyze TSLA", "user_id": "user-2", "ticker": "TSLA"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_cache_hit"] is True
    assert "Investment Analysis" in payload["response"]
    assert cache.set_calls, "Fresh results should be cached"
    assert router.last_embedding is not None
    assert router.record_calls, "Router should store semantic example"


def test_query_endpoint_routes_to_investment_workflow(app_client):
    client = app_client["client"]
    cache = app_client["cache"]
    router = app_client["router"]
    cache.get_return = None
    StubInvestmentWorkflow.last_call = None

    response = client.post(
        "/api/query",
        json={"query": "Should I buy AAPL stock?", "user_id": "user-3"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "Investment Analysis" in payload["response"]
    assert StubInvestmentWorkflow.last_call == {"ticker": "AAPL"}
    assert router.last_embedding is not None
    assert router.record_calls, "Router should persist semantic recordings"
    assert router.record_calls[-1]["workflow"] == "InvestmentAnalysisWorkflow"


def test_query_endpoint_uses_cache_when_available(app_client):
    client = app_client["client"]
    cache = app_client["cache"]

    cache.get_return = {
        "response": "Cached basic response",
        "workflow": "CachedWorkflow",
        "similarity": 0.95,
        "cached_query": "Should I buy AAPL?",
        "cache_hit": True,
    }

    response = client.post(
        "/api/query",
        json={"query": "Should I buy AAPL stock?", "user_id": "user-4"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["cache_hit"] is True
    assert payload["response"] == "Cached basic response"


def test_query_endpoint_caches_then_hits_on_repeat(app_client):
    client = app_client["client"]
    cache = app_client["cache"]

    cache.get_return = None
    cache.enable_auto_cache(similarity=0.995)

    first_response = client.post(
        "/api/query",
        json={"query": "Test auto cache", "user_id": "user-repeat"},
    )

    assert first_response.status_code == 200
    first_payload = first_response.json()
    assert first_payload["cache_hit"] is False
    assert len(cache.set_calls) == 1

    cache.get_return = None

    second_response = client.post(
        "/api/query",
        json={"query": "Test auto cache", "user_id": "user-repeat"},
    )

    assert second_response.status_code == 200
    second_payload = second_response.json()
    assert second_payload["cache_hit"] is True
    assert second_payload["response"] == first_payload["response"]
    assert len(cache.set_calls) == 1, "Cache hit should not trigger re-cache"


def test_metrics_cache_endpoint(app_client):
    client = app_client["client"]

    response = client.get("/api/metrics/cache")
    assert response.status_code == 200
    payload = response.json()
    assert payload["cache_stats"]["total_entries"] == 3
    assert payload["cache_stats"]["total_hits"] == 2


def test_routes_listing(app_client):
    client = app_client["client"]

    response = client.get("/api/routes")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_routes"] == 1
    assert payload["routes"][0]["workflow"] == "InvestmentAnalysisWorkflow"


def test_document_ingest_endpoint(app_client):
    client = app_client["client"]

    response = client.post(
        "/api/documents/ingest",
        json={
            "content": "Some filing text",
            "title": "AAPL 10-K",
            "source": "SEC",
            "doc_type": "10-K",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["chunk_ids"] == ["chunk-1", "chunk-2"]


def test_document_search_endpoint(app_client):
    client = app_client["client"]

    response = client.post(
        "/api/documents/search",
        json={"query": "revenue guidance", "ticker": "AAPL"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_results"] == 1
    assert payload["results"][0]["score"] == 0.92


def test_document_rag_endpoint(app_client):
    client = app_client["client"]
    rag = app_client["rag"]

    response = client.post(
        "/api/documents/ask",
        json={"question": "What did AAPL report?", "ticker": "AAPL"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Stub answer"
    assert rag.last_question["question"] == "What did AAPL report?"


def test_document_delete_endpoint(app_client):
    client = app_client["client"]
    document_store = app_client["document_store"]

    response = client.delete("/api/documents/AAPL")
    assert response.status_code == 200
    payload = response.json()
    assert payload["deleted_count"] == 2
    assert document_store.deleted_ticker == "AAPL"


def test_document_stats_endpoint(app_client):
    client = app_client["client"]

    response = client.get("/api/documents/stats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_documents"] == 1


def test_root_endpoint(app_client):
    client = app_client["client"]

    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "FinagentiX API"
