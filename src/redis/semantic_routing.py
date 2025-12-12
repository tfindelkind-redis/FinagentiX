"""
Semantic Routing for intelligent workflow selection
Shortcuts orchestrator reasoning by caching query patterns → workflows
"""

import json
import time
import hashlib
from typing import Dict, Any, List, Optional
from redis import Redis

from .client import get_redis_client


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
    ):
        """
        Initialize semantic router
        
        Args:
            redis_client: Redis client instance
            prefix: Key prefix for route entries
        """
        self.redis = redis_client or get_redis_client()
        self.prefix = prefix
        
        # Initialize default routes
        self._init_default_routes()
    
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
            self.redis.setex(
                key,
                ttl_seconds,
                json.dumps(route_data)
            )
            
            # Index patterns for fast lookup
            for pattern in route_data.get("patterns", []):
                pattern_key = f"{self.prefix}pattern:{hashlib.md5(pattern.lower().encode()).hexdigest()[:8]}"
                self.redis.setex(pattern_key, ttl_seconds, route_id)
            
        except Exception as e:
            print(f"❌ Error adding route: {e}")
    
    def find_route(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Find matching route for query
        
        Args:
            query: User query
        
        Returns:
            Route data if found, None otherwise
        """
        query_lower = query.lower()
        
        try:
            # Check all routes for pattern matches
            route_keys = list(self.redis.scan_iter(f"{self.prefix}*", count=100))
            
            for route_key in route_keys:
                if ":pattern:" in route_key:
                    continue  # Skip pattern index keys
                
                route_json = self.redis.get(route_key)
                if not route_json:
                    continue
                
                route_data = json.loads(route_json)
                
                # Check if any pattern matches query
                for pattern in route_data.get("patterns", []):
                    if pattern.lower() in query_lower:
                        # Increment usage count
                        route_id = route_key.replace(self.prefix, "")
                        self._increment_usage(route_id)
                        
                        return {
                            "route_id": route_id,
                            "workflow": route_data["workflow"],
                            "agents": route_data["agents"],
                            "description": route_data["description"],
                            "matched_pattern": pattern,
                            "cache_hit": True,
                        }
            
            return None
            
        except Exception as e:
            print(f"❌ Error finding route: {e}")
            return None
    
    def _increment_usage(self, route_id: str):
        """Increment usage counter for route"""
        usage_key = f"{self.prefix}usage:{route_id}"
        self.redis.incr(usage_key)
    
    def get_route(self, route_id: str) -> Optional[Dict[str, Any]]:
        """Get route by ID"""
        key = f"{self.prefix}{route_id}"
        
        try:
            route_json = self.redis.get(key)
            if route_json:
                return json.loads(route_json)
            return None
            
        except Exception as e:
            print(f"❌ Error getting route: {e}")
            return None
    
    def get_all_routes(self) -> List[Dict[str, Any]]:
        """Get all available routes"""
        routes = []
        
        try:
            route_keys = list(self.redis.scan_iter(f"{self.prefix}*", count=100))
            
            for route_key in route_keys:
                if ":pattern:" in route_key or ":usage:" in route_key:
                    continue
                
                route_json = self.redis.get(route_key)
                if route_json:
                    route_data = json.loads(route_json)
                    route_id = route_key.replace(self.prefix, "")
                    route_data["route_id"] = route_id
                    
                    # Add usage count
                    usage_key = f"{self.prefix}usage:{route_id}"
                    route_data["usage_count"] = int(self.redis.get(usage_key) or 0)
                    
                    routes.append(route_data)
            
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
            ]
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
