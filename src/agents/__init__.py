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

from src.agents.orchestrator_agent import OrchestratorAgent
from src.agents.market_data_agent import MarketDataAgent
from src.agents.news_sentiment_agent import NewsSentimentAgent
from src.agents.risk_assessment_agent import RiskAssessmentAgent
from src.agents.fundamental_analysis_agent import FundamentalAnalysisAgent
from src.agents.router_agent import RouterAgent
from src.agents.synthesis_agent import SynthesisAgent

__all__ = [
    "OrchestratorAgent",
    "MarketDataAgent",
    "NewsSentimentAgent",
    "RiskAssessmentAgent",
    "FundamentalAnalysisAgent",
    "RouterAgent",
    "SynthesisAgent",
]

# Agent registry for dynamic instantiation
AGENT_REGISTRY = {
    "orchestrator": OrchestratorAgent,
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
    if agent_name not in AGENT_REGISTRY:
        available = ", ".join(AGENT_REGISTRY.keys())
        raise ValueError(
            f"Agent '{agent_name}' not found. Available agents: {available}"
        )
    
    return AGENT_REGISTRY[agent_name]()
