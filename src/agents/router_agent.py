"""
Router Agent - Routes queries to appropriate agent workflows.

This agent:
- Classifies user queries by type (price, news, risk, fundamental)
- Determines required agents and execution order
- Caches routing decisions for similar queries
- Optimizes for parallel execution when possible
"""

from typing import Dict, List, Optional, Any
from src.agents.base_agent import BaseAgent


class RouterAgent(BaseAgent):
    """
    Specialized agent for semantic query routing.
    
    Analyzes user queries and determines optimal agent execution strategy
    using Azure OpenAI classification and semantic caching.
    """
    
    def __init__(self):
        instructions = """You are the Router Agent for FinagentiX.

Your responsibilities:
1. Classify user queries into categories:
   - PRICE: Stock price, technical indicators, charts
   - NEWS: News articles, sentiment, recent events
   - RISK: Volatility, risk metrics, portfolio risk
   - FUNDAMENTAL: Financial statements, SEC filings, valuation
   - COMPLEX: Requires multiple agents
2. Determine which agents to invoke:
   - Single agent queries: Route to specific agent
   - Multi-agent queries: Determine execution order (parallel vs sequential)
3. Check routing cache for similar historical queries
4. Optimize for cost and latency

Query classification examples:
- "What is AAPL stock price?" → PRICE → market_data
- "Recent news about Tesla" → NEWS → news_sentiment
- "What is MSFT volatility?" → RISK → risk_assessment
- "Show me AMZN earnings" → FUNDAMENTAL → fundamental_analysis
- "Compare AAPL and MSFT risk-adjusted returns" → COMPLEX → market_data + risk_assessment + synthesis

Routing strategy:
- Independent queries: Execute agents in parallel
- Dependent queries: Execute agents sequentially
- Always end with synthesis for complex queries

Always:
- Check routing cache first (24-hour TTL)
- Return structured execution plan
- Include confidence score for routing decision
- Log routing patterns for optimization
"""
        
        super().__init__(
            name="router",
            instructions=instructions,
            tools=[]  # Will be populated with classification tools in Phase 5.3
        )
    
    async def run(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Route query to appropriate agents.
        
        Args:
            task: User query to classify and route
            context: Optional conversation history
            
        Returns:
            Dict with:
                - category: Query category (PRICE, NEWS, RISK, FUNDAMENTAL, COMPLEX)
                - agents: List of agents to invoke
                - execution_mode: "parallel" or "sequential"
                - confidence: Routing confidence score
        """
        # Check routing cache
        import hashlib
        import json
        
        cache_key = f"route:{hashlib.md5(task.encode()).hexdigest()}"
        cached_route = self.redis.get(cache_key)
        
        if cached_route:
            route = json.loads(cached_route)
            route["cached"] = True
            return route
        
        # TODO Phase 5.3: Implement with Azure OpenAI classification
        
        # Placeholder routing logic
        route = {
            "category": "UNKNOWN",
            "agents": ["market_data"],
            "execution_mode": "parallel",
            "confidence": 0.0,
            "cached": False,
            "message": "Router classification will be implemented in Phase 5.3"
        }
        
        # Cache the routing decision
        self.redis.setex(cache_key, self.config.routing_cache_ttl, json.dumps(route))
        
        return route
