"""
Semantic Routing for intelligent workflow selection
Shortcuts orchestrator reasoning by caching query patterns → workflows
"""

import json
import time
import hashlib
from typing import Dict, Any, List, Optional

import numpy as np
from redis import Redis

from .client import RedisConfig, get_redis_client

try:
    from redis.commands.search.field import VectorField, TextField, NumericField
    from redis.commands.search.indexDefinition import IndexDefinition, IndexType
    from redis.commands.search.query import Query
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False
    print("⚠️  RediSearch not available. Semantic routing will use pattern fallback only.")


class SemanticRouter:
    """
    Semantic router for workflow selection
    
    Features:
    - Cache query patterns → workflow mappings
    - Skip expensive orchestrator LLM calls
    - Direct agent routing for known patterns
    - Sub-millisecond routing decisions
    """
    
    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        prefix: str = "route:",
        index_name: str = "idx:semantic_routes",
        example_prefix: str = "route_example:",
        similarity_threshold: float = 0.82,
        example_ttl_seconds: int = 3600 * 24 * 30,
    ):
        """
        Initialize semantic router
        
        Args:
            redis_client: Redis client instance
            prefix: Key prefix for route entries
        """
        if redis_client is not None:
            decode_flag = getattr(getattr(redis_client, "connection_pool", None), "connection_kwargs", {}).get("decode_responses")
            if decode_flag:
                config = RedisConfig()
                self.redis = Redis(
                    host=config.host,
                    port=config.port,
                    password=config.password,
                    ssl=config.ssl,
                    decode_responses=False,
                    max_connections=config.max_connections,
                )
            else:
                self.redis = redis_client
        else:
            config = RedisConfig()
            self.redis = Redis(
                host=config.host,
                port=config.port,
                password=config.password,
                ssl=config.ssl,
                decode_responses=False,
                max_connections=config.max_connections,
            )
        self.prefix = prefix
        self.index_name = index_name
        self.example_prefix = example_prefix
        self.vector_similarity_threshold = similarity_threshold
        self.example_ttl_seconds = example_ttl_seconds
        self.vector_enabled = False
        self._route_cache: Dict[str, Dict[str, Any]] = {}
        
        # Initialize default routes
        self._init_default_routes()
        # Prepare vector index for semantic routing examples
        self._create_vector_index()
    
    def _init_default_routes(self):
        """Initialize default workflow routes"""
        
        default_routes = {
            # Investment Analysis Workflow
            "investment_analysis": {
                "patterns": [
                    "should i buy",
                    "should i invest",
                    "is it a good time to buy",
                    "investment recommendation",
                    "stock recommendation",
                ],
                "workflow": "InvestmentAnalysisWorkflow",
                "agents": ["market_data", "technical_analysis", "risk_analysis", "news_sentiment"],
                "description": "Complete investment analysis with market data, technical indicators, risk assessment, and sentiment"
            },
            
            # Portfolio Review Workflow
            "portfolio_review": {
                "patterns": [
                    "review my portfolio",
                    "portfolio performance",
                    "how is my portfolio",
                    "portfolio analysis",
                    "diversification check",
                ],
                "workflow": "PortfolioReviewWorkflow",
                "agents": ["portfolio", "risk_analysis"],
                "description": "Portfolio review with performance metrics and risk assessment"
            },
            
            # Market Research Workflow
            "market_research": {
                "patterns": [
                    "market analysis",
                    "market trends",
                    "sector analysis",
                    "market overview",
                    "what's happening in the market",
                ],
                "workflow": "MarketResearchWorkflow",
                "agents": ["market_data", "news_sentiment", "technical_analysis"],
                "description": "Market research with news, sentiment, and technical analysis"
            },
            
            # Quick Quote Workflow
            "quick_quote": {
                "patterns": [
                    "what's the price",
                    "current price",
                    "stock price",
                    "quote for",
                    "how much is",
                ],
                "workflow": "QuickQuoteWorkflow",
                "agents": ["market_data"],
                "description": "Quick price quote with basic market data"
            },
            
            # Technical Analysis Workflow
            "technical_analysis": {
                "patterns": [
                    "technical analysis",
                    "chart patterns",
                    "support and resistance",
                    "moving averages",
                    "rsi",
                    "macd",
                ],
                "workflow": "TechnicalAnalysisWorkflow",
                "agents": ["market_data", "technical_analysis"],
                "description": "Technical analysis with indicators and chart patterns"
            },
            
            # Risk Assessment Workflow
            "risk_assessment": {
                "patterns": [
                    "risk analysis",
                    "how risky",
                    "volatility",
                    "risk assessment",
                    "value at risk",
                ],
                "workflow": "RiskAssessmentWorkflow",
                "agents": ["market_data", "risk_analysis"],
                "description": "Risk assessment with VaR, volatility, and risk metrics"
            },
        }
        
        # Store default routes
        for route_id, route_data in default_routes.items():
            self.add_route(route_id, route_data)

    def _create_vector_index(self):
        """Create Redis vector search index for routing examples if available"""
        if not SEARCH_AVAILABLE:
            return

        try:
            self.redis.ft(self.index_name).info()
            self.vector_enabled = True
        except Exception:
            try:
                schema = [
                    VectorField(
                        "query_embedding",
                        "HNSW",
                        {
                            "TYPE": "FLOAT32",
                            "DIM": 3072,
                            "DISTANCE_METRIC": "COSINE",
                        },
                    ),
                    TextField("route_id"),
                    TextField("workflow"),
                    TextField("agents"),
                    TextField("query_text"),
                    TextField("source"),
                    NumericField("timestamp"),
                ]
                definition = IndexDefinition(prefix=[self.example_prefix], index_type=IndexType.HASH)
                self.redis.ft(self.index_name).create_index(fields=schema, definition=definition)
                self.vector_enabled = True
                print(f"✅ Created semantic routing index '{self.index_name}'")
            except Exception as create_error:
                self.vector_enabled = False
                print(f"⚠️  Could not create semantic routing index: {create_error}")

    def _refresh_route_cache(self):
        """Populate in-memory cache of route definitions"""
        try:
            for route_key in self.redis.scan_iter(f"{self.prefix}*", count=100):
                key_str = route_key.decode() if isinstance(route_key, bytes) else route_key
                if ":pattern:" in key_str or ":usage:" in key_str:
                    continue

                route_json = self.redis.get(route_key)
                if not route_json:
                    continue

                try:
                    serialized = route_json.decode() if isinstance(route_json, bytes) else route_json
                    route_data = json.loads(serialized)
                except Exception:
                    continue

                route_id = route_data.get("route_id") or key_str.replace(self.prefix, "")
                route_data["route_id"] = route_id
                self._route_cache[route_id] = route_data
        except Exception as e:
            print(f"❌ Error refreshing route cache: {e}")
    
    def add_route(
        self,
        route_id: str,
        route_data: Dict[str, Any],
        ttl_seconds: int = 3600 * 24 * 30,  # 30 days
    ):
        """
        Add or update a route
        
        Args:
            route_id: Route identifier
            route_data: Route configuration
            ttl_seconds: Time to live
        """
        key = f"{self.prefix}{route_id}"
        
        try:
            payload = route_data.copy()
            payload.setdefault("route_id", route_id)
            self.redis.setex(
                key,
                ttl_seconds,
                json.dumps(payload)
            )
            
            # Index patterns for fast lookup
            for pattern in route_data.get("patterns", []):
                pattern_key = f"{self.prefix}pattern:{hashlib.md5(pattern.lower().encode()).hexdigest()[:8]}"
                self.redis.setex(pattern_key, ttl_seconds, route_id)

            # Update local cache for quick lookup
            cached_copy = payload.copy()
            self._route_cache[route_id] = cached_copy
            
        except Exception as e:
            print(f"❌ Error adding route: {e}")
    
    def find_route(
        self,
        query: str,
        query_embedding: Optional[List[float]] = None,
        top_k: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """Find matching route for query using semantic search with pattern fallback"""

        semantic_match = None
        if self.vector_enabled and query_embedding is not None:
            semantic_match = self._find_route_by_vector(query_embedding=query_embedding, top_k=top_k)
            if semantic_match:
                return semantic_match

        return self._find_route_by_pattern(query=query)
    
    def _find_route_by_vector(
        self,
        query_embedding: List[float],
        top_k: int,
    ) -> Optional[Dict[str, Any]]:
        if not self.vector_enabled:
            return None

        try:
            embedding_bytes = np.array(query_embedding, dtype=np.float32).tobytes()
            search_query = (
                Query(f"*=>[KNN {top_k} @query_embedding $vec AS score]")
                .sort_by("score")
                .return_fields("route_id", "workflow", "agents", "query_text", "source", "score")
                .dialect(2)
            )
            results = self.redis.ft(self.index_name).search(
                search_query,
                query_params={"vec": embedding_bytes},
            )

            for doc in getattr(results, "docs", []):
                similarity = 1 - float(doc.score)
                if similarity < self.vector_similarity_threshold:
                    continue

                route_id = getattr(doc, "route_id", None) or getattr(doc, "workflow", None)
                if not route_id:
                    continue

                base_route = self.get_route(route_id)
                workflow = base_route.get("workflow") if base_route else getattr(doc, "workflow", None)
                agents = None

                if base_route and base_route.get("agents"):
                    agents = base_route["agents"]
                elif getattr(doc, "agents", None):
                    try:
                        agents = json.loads(doc.agents)
                    except Exception:
                        agents = [doc.agents]
                else:
                    agents = []

                description = base_route.get("description") if base_route else None
                result = {
                    "route_id": route_id,
                    "workflow": workflow,
                    "agents": agents,
                    "description": description,
                    "matched_pattern": getattr(doc, "query_text", None),
                    "matched_via": "semantic",
                    "similarity": similarity,
                    "cache_hit": True,
                }

                self._increment_usage(route_id)
                return result

        except Exception as e:
            print(f"❌ Error during semantic routing search: {e}")

        return None

    def record_route(
        self,
        query: str,
        query_embedding: Optional[List[float]],
        route_id: str,
        workflow: str,
        agents: Optional[List[str]] = None,
        source: str = "inference",
    ) -> None:
        """Record a successful routing decision for future semantic matches"""

        if not (self.vector_enabled and query_embedding):
            return

        try:
            embedding_bytes = np.array(query_embedding, dtype=np.float32).tobytes()
            fingerprint = hashlib.md5(f"{route_id}:{query}".encode()).hexdigest()[:16]
            example_key = f"{self.example_prefix}{fingerprint}"

            self.redis.hset(
                example_key,
                mapping={
                    "route_id": route_id,
                    "workflow": workflow,
                    "agents": json.dumps(agents or []),
                    "query_text": query,
                    "query_embedding": embedding_bytes,
                    "timestamp": time.time(),
                    "source": source,
                },
            )
            self.redis.expire(example_key, self.example_ttl_seconds)
        except Exception as e:
            print(f"❌ Error recording semantic route example: {e}")

    def _find_route_by_pattern(self, query: str) -> Optional[Dict[str, Any]]:
        query_lower = query.lower()

        try:
            if not self._route_cache:
                self._refresh_route_cache()

            for route_id, route_data in self._route_cache.items():
                for pattern in route_data.get("patterns", []):
                    if pattern.lower() in query_lower:
                        self._increment_usage(route_id)
                        return {
                            "route_id": route_id,
                            "workflow": route_data["workflow"],
                            "agents": route_data["agents"],
                            "description": route_data.get("description"),
                            "matched_pattern": pattern,
                            "matched_via": "pattern",
                            "similarity": 1.0,
                            "cache_hit": True,
                        }

        except Exception as e:
            print(f"❌ Error finding route via pattern: {e}")

        return None

    def _increment_usage(self, route_id: str):
        """Increment usage counter for route"""
        usage_key = f"{self.prefix}usage:{route_id}"
        self.redis.incr(usage_key)
    
    def get_route(self, route_id: str) -> Optional[Dict[str, Any]]:
        """Get route by ID"""
        key = f"{self.prefix}{route_id}"
        
        try:
            if route_id in self._route_cache:
                return self._route_cache[route_id].copy()

            route_json = self.redis.get(key)
            if route_json:
                serialized = route_json.decode() if isinstance(route_json, bytes) else route_json
                data = json.loads(serialized)
                data.setdefault("route_id", route_id)
                self._route_cache[route_id] = data
                return data.copy()
            return None
            
        except Exception as e:
            print(f"❌ Error getting route: {e}")
            return None
    
    def get_all_routes(self) -> List[Dict[str, Any]]:
        """Get all available routes"""
        routes: List[Dict[str, Any]] = []

        try:
            if not self._route_cache:
                self._refresh_route_cache()

            for route_id, route_data in self._route_cache.items():
                entry = route_data.copy()
                usage_key = f"{self.prefix}usage:{route_id}"
                usage_value = self.redis.get(usage_key)
                if isinstance(usage_value, bytes):
                    usage_value = usage_value.decode()
                entry["usage_count"] = int(usage_value or 0)
                routes.append(entry)

            return routes

        except Exception as e:
            print(f"❌ Error getting all routes: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        routes = self.get_all_routes()
        
        total_routes = len(routes)
        total_usage = sum(r.get("usage_count", 0) for r in routes)
        
        top_routes = sorted(routes, key=lambda r: r.get("usage_count", 0), reverse=True)[:5]

        vector_entries = 0
        if self.vector_enabled:
            try:
                vector_entries = sum(1 for _ in self.redis.scan_iter(f"{self.example_prefix}*", count=200))
            except Exception as e:
                print(f"⚠️  Error counting semantic route examples: {e}")
        
        return {
            "total_routes": total_routes,
            "total_usage": total_usage,
            "top_routes": [
                {
                    "route_id": r["route_id"],
                    "workflow": r["workflow"],
                    "usage_count": r.get("usage_count", 0)
                }
                for r in top_routes
            ],
            "vector_enabled": self.vector_enabled,
            "vector_example_count": vector_entries,
            "similarity_threshold": self.vector_similarity_threshold,
        }


if __name__ == "__main__":
    # Test semantic router
    router = SemanticRouter()
    
    # Test queries
    test_queries = [
        "Should I buy AAPL?",
        "What's the current price of Tesla?",
        "Review my portfolio performance",
        "Technical analysis for MSFT",
        "How risky is this stock?",
    ]
    
    for query in test_queries:
        route = router.find_route(query)
        if route:
            print(f"✅ Query: '{query}'")
            print(f"   → Workflow: {route['workflow']}")
            print(f"   → Agents: {', '.join(route['agents'])}")
            print(f"   → Matched: '{route['matched_pattern']}'")
        else:
            print(f"❌ Query: '{query}' - No route found")
        print()
    
    # Show stats
    print("Router stats:")
    print(json.dumps(router.get_stats(), indent=2))
