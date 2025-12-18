"""
FinagentiX Agent Framework - Phase 5.2 Complete

This module contains all 7 specialized agents for the FinagentiX multi-agent system:

1. OrchestratorAgent: Coordinates workflow across agents
2. MarketDataAgent: Stock prices and technical indicators
3. NewsSentimentAgent: News search and sentiment analysis
4. RiskAssessmentAgent: Volatility and risk metrics
5. FundamentalAnalysisAgent: SEC filings and financial analysis
6. RouterAgent: Semantic query routing
7. SynthesisAgent: Multi-agent result combination

Usage:
    from src.agents import OrchestratorAgent, MarketDataAgent
    
    orchestrator = OrchestratorAgent()
    result = await orchestrator.run("What is AAPL stock price?")
"""

# Import most agents directly - but NOT OrchestratorAgent (causes circular import)
from src.agents.market_data_agent import MarketDataAgent
from src.agents.news_sentiment_agent import NewsSentimentAgent
from src.agents.risk_assessment_agent import RiskAssessmentAgent
from src.agents.fundamental_analysis_agent import FundamentalAnalysisAgent
from src.agents.router_agent import RouterAgent
from src.agents.synthesis_agent import SynthesisAgent

# Lazy import for OrchestratorAgent to avoid circular imports
# (orchestrator_agent imports workflows which imports agents.plugins which imports this module)
_OrchestratorAgent = None

def _get_orchestrator_agent():
    """Lazy load OrchestratorAgent to avoid circular imports."""
    global _OrchestratorAgent
    if _OrchestratorAgent is None:
        from src.agents.orchestrator_agent import OrchestratorAgent
        _OrchestratorAgent = OrchestratorAgent
    return _OrchestratorAgent

# Support "from src.agents import OrchestratorAgent"
def __getattr__(name):
    if name == "OrchestratorAgent":
        return _get_orchestrator_agent()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "OrchestratorAgent",
    "MarketDataAgent",
    "NewsSentimentAgent",
    "RiskAssessmentAgent",
    "FundamentalAnalysisAgent",
    "RouterAgent",
    "SynthesisAgent",
]

# Agent registry for dynamic instantiation - lazy for orchestrator
def _get_agent_registry():
    return {
        "orchestrator": _get_orchestrator_agent(),
        "market_data": MarketDataAgent,
        "news_sentiment": NewsSentimentAgent,
        "risk_assessment": RiskAssessmentAgent,
        "fundamental_analysis": FundamentalAnalysisAgent,
        "router": RouterAgent,
        "synthesis": SynthesisAgent,
    }


def get_agent(agent_name: str):
    """
    Factory function to instantiate agents by name.
    
    Args:
        agent_name: Name of agent (e.g., "orchestrator", "market_data")
        
    Returns:
        Instantiated agent object
        
    Raises:
        ValueError: If agent name not found in registry
    """
    registry = _get_agent_registry()
    if agent_name not in registry:
        available = ", ".join(registry.keys())
        raise ValueError(
            f"Agent '{agent_name}' not found. Available agents: {available}"
        )
    
    return registry[agent_name]()
