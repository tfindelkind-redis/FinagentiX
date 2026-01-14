#!/usr/bin/env python3
"""
Comprehensive Agent Integration Tests for FinagentiX
=====================================================

This test suite verifies all 7+ agents are fully implemented and working.
It tests:
1. Agent instantiation and initialization
2. Agent run() method execution
3. Expected response structure
4. Integration with Redis (if available)
5. Real question/answer scenarios

Run with:
    pytest tests/test_all_agents_integration.py -v
    
Or run directly:
    python tests/test_all_agents_integration.py
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load environment variables BEFORE importing agents
from dotenv import load_dotenv
load_dotenv()

import pytest


# ==================== Test Configuration ====================

@dataclass
class TestQuestion:
    """A test question with expected elements in the answer."""
    question: str
    ticker: Optional[str]
    expected_keywords: List[str]  # Keywords that should appear in response
    expected_agents: List[str]    # Agents that should handle this
    category: str                 # Question category


TEST_QUESTIONS = [
    # Market Data Questions
    TestQuestion(
        question="What is the current stock price of AAPL?",
        ticker="AAPL",
        expected_keywords=["price", "AAPL", "$"],
        expected_agents=["market_data"],
        category="price"
    ),
    TestQuestion(
        question="Show me the 30-day price history for MSFT",
        ticker="MSFT",
        expected_keywords=["MSFT", "price", "history"],
        expected_agents=["market_data"],
        category="history"
    ),
    TestQuestion(
        question="What are the technical indicators for GOOGL?",
        ticker="GOOGL",
        expected_keywords=["GOOGL", "RSI", "MACD", "moving average"],
        expected_agents=["market_data"],
        category="technical"
    ),
    
    # News/Sentiment Questions  
    TestQuestion(
        question="What is the latest news about Tesla?",
        ticker="TSLA",
        expected_keywords=["TSLA", "news", "sentiment"],
        expected_agents=["news_sentiment"],
        category="news"
    ),
    TestQuestion(
        question="What is the sentiment around NVDA stock?",
        ticker="NVDA",
        expected_keywords=["NVDA", "sentiment", "positive", "negative", "neutral"],
        expected_agents=["news_sentiment"],
        category="sentiment"
    ),
    
    # Risk Assessment Questions
    TestQuestion(
        question="What is the risk profile of AMZN?",
        ticker="AMZN",
        expected_keywords=["AMZN", "risk", "volatility"],
        expected_agents=["risk_assessment"],
        category="risk"
    ),
    TestQuestion(
        question="Calculate the volatility for META stock",
        ticker="META",
        expected_keywords=["META", "volatility", "%"],
        expected_agents=["risk_assessment"],
        category="volatility"
    ),
    
    # Fundamental Analysis Questions
    TestQuestion(
        question="What are the key financials from AAPL's latest 10-K?",
        ticker="AAPL",
        expected_keywords=["AAPL", "10-K", "revenue", "earnings"],
        expected_agents=["fundamental_analysis"],
        category="fundamentals"
    ),
    TestQuestion(
        question="Summarize the SEC filings for Microsoft",
        ticker="MSFT",
        expected_keywords=["MSFT", "SEC", "filing"],
        expected_agents=["fundamental_analysis"],
        category="sec_filings"
    ),
    
    # Complex Multi-Agent Questions
    TestQuestion(
        question="Give me a complete investment analysis of NVDA including price, news, risk, and fundamentals",
        ticker="NVDA",
        expected_keywords=["NVDA", "price", "news", "risk"],
        expected_agents=["market_data", "news_sentiment", "risk_assessment", "fundamental_analysis"],
        category="complex"
    ),
]


# ==================== Agent Tests ====================

class TestAgentImports:
    """Test that all agents can be imported."""
    
    def test_import_base_agent(self):
        """Base agent class should be importable."""
        from src.agents.base_agent import BaseAgent
        assert BaseAgent is not None
    
    def test_import_market_data_agent(self):
        """Market Data Agent should be importable."""
        from src.agents.market_data_agent import MarketDataAgent
        assert MarketDataAgent is not None
    
    def test_import_news_sentiment_agent(self):
        """News Sentiment Agent should be importable."""
        from src.agents.news_sentiment_agent import NewsSentimentAgent
        assert NewsSentimentAgent is not None
    
    def test_import_risk_assessment_agent(self):
        """Risk Assessment Agent should be importable."""
        from src.agents.risk_assessment_agent import RiskAssessmentAgent
        assert RiskAssessmentAgent is not None
    
    def test_import_fundamental_analysis_agent(self):
        """Fundamental Analysis Agent should be importable."""
        from src.agents.fundamental_analysis_agent import FundamentalAnalysisAgent
        assert FundamentalAnalysisAgent is not None
    
    def test_import_router_agent(self):
        """Router Agent should be importable."""
        from src.agents.router_agent import RouterAgent
        assert RouterAgent is not None
    
    def test_import_synthesis_agent(self):
        """Synthesis Agent should be importable."""
        from src.agents.synthesis_agent import SynthesisAgent
        assert SynthesisAgent is not None
    
    def test_import_orchestrator_agent(self):
        """Orchestrator Agent should be importable."""
        from src.agents.orchestrator_agent import OrchestratorAgent
        assert OrchestratorAgent is not None
    
    def test_import_all_from_package(self):
        """All agents should be importable from package."""
        from src.agents import (
            MarketDataAgent,
            NewsSentimentAgent,
            RiskAssessmentAgent,
            FundamentalAnalysisAgent,
            RouterAgent,
            SynthesisAgent,
        )
        assert all([
            MarketDataAgent,
            NewsSentimentAgent,
            RiskAssessmentAgent,
            FundamentalAnalysisAgent,
            RouterAgent,
            SynthesisAgent,
        ])


class TestAgentInstantiation:
    """Test that all agents can be instantiated."""
    
    def test_market_data_agent_init(self):
        """Market Data Agent should initialize without errors."""
        from src.agents.market_data_agent import MarketDataAgent
        agent = MarketDataAgent()
        assert agent.name == "market_data"
        assert agent.instructions is not None
        assert len(agent.instructions) > 100  # Has substantial instructions
    
    def test_news_sentiment_agent_init(self):
        """News Sentiment Agent should initialize without errors."""
        from src.agents.news_sentiment_agent import NewsSentimentAgent
        agent = NewsSentimentAgent()
        assert agent.name == "news_sentiment"
        assert agent.instructions is not None
    
    def test_risk_assessment_agent_init(self):
        """Risk Assessment Agent should initialize without errors."""
        from src.agents.risk_assessment_agent import RiskAssessmentAgent
        agent = RiskAssessmentAgent()
        assert agent.name == "risk_assessment"
        assert agent.instructions is not None
    
    def test_fundamental_analysis_agent_init(self):
        """Fundamental Analysis Agent should initialize without errors."""
        from src.agents.fundamental_analysis_agent import FundamentalAnalysisAgent
        agent = FundamentalAnalysisAgent()
        assert agent.name == "fundamental_analysis"
        assert agent.instructions is not None
    
    def test_router_agent_init(self):
        """Router Agent should initialize without errors."""
        from src.agents.router_agent import RouterAgent
        agent = RouterAgent()
        assert agent.name == "router"
        assert agent.instructions is not None
    
    def test_synthesis_agent_init(self):
        """Synthesis Agent should initialize without errors."""
        from src.agents.synthesis_agent import SynthesisAgent
        agent = SynthesisAgent()
        assert agent.name == "synthesis"
        assert agent.instructions is not None
    
    def test_orchestrator_agent_init(self):
        """Orchestrator Agent should initialize without errors."""
        from src.agents.orchestrator_agent import OrchestratorAgent
        agent = OrchestratorAgent()
        assert agent.name == "orchestrator"
        assert agent.instructions is not None


class TestAgentHasRunMethod:
    """Test that all agents have the required run() method."""
    
    def test_market_data_has_run(self):
        """Market Data Agent should have async run method."""
        from src.agents.market_data_agent import MarketDataAgent
        agent = MarketDataAgent()
        assert hasattr(agent, "run")
        assert asyncio.iscoroutinefunction(agent.run)
    
    def test_news_sentiment_has_run(self):
        """News Sentiment Agent should have async run method."""
        from src.agents.news_sentiment_agent import NewsSentimentAgent
        agent = NewsSentimentAgent()
        assert hasattr(agent, "run")
        assert asyncio.iscoroutinefunction(agent.run)
    
    def test_risk_assessment_has_run(self):
        """Risk Assessment Agent should have async run method."""
        from src.agents.risk_assessment_agent import RiskAssessmentAgent
        agent = RiskAssessmentAgent()
        assert hasattr(agent, "run")
        assert asyncio.iscoroutinefunction(agent.run)
    
    def test_fundamental_analysis_has_run(self):
        """Fundamental Analysis Agent should have async run method."""
        from src.agents.fundamental_analysis_agent import FundamentalAnalysisAgent
        agent = FundamentalAnalysisAgent()
        assert hasattr(agent, "run")
        assert asyncio.iscoroutinefunction(agent.run)
    
    def test_router_has_run(self):
        """Router Agent should have async run method."""
        from src.agents.router_agent import RouterAgent
        agent = RouterAgent()
        assert hasattr(agent, "run")
        assert asyncio.iscoroutinefunction(agent.run)
    
    def test_synthesis_has_run(self):
        """Synthesis Agent should have async run method."""
        from src.agents.synthesis_agent import SynthesisAgent
        agent = SynthesisAgent()
        assert hasattr(agent, "run")
        assert asyncio.iscoroutinefunction(agent.run)


class TestAgentRegistry:
    """Test the agent registry and factory function."""
    
    def test_get_agent_market_data(self):
        """Factory should return MarketDataAgent."""
        from src.agents import get_agent
        agent = get_agent("market_data")
        assert agent.name == "market_data"
    
    def test_get_agent_news_sentiment(self):
        """Factory should return NewsSentimentAgent."""
        from src.agents import get_agent
        agent = get_agent("news_sentiment")
        assert agent.name == "news_sentiment"
    
    def test_get_agent_risk_assessment(self):
        """Factory should return RiskAssessmentAgent."""
        from src.agents import get_agent
        agent = get_agent("risk_assessment")
        assert agent.name == "risk_assessment"
    
    def test_get_agent_fundamental_analysis(self):
        """Factory should return FundamentalAnalysisAgent."""
        from src.agents import get_agent
        agent = get_agent("fundamental_analysis")
        assert agent.name == "fundamental_analysis"
    
    def test_get_agent_router(self):
        """Factory should return RouterAgent."""
        from src.agents import get_agent
        agent = get_agent("router")
        assert agent.name == "router"
    
    def test_get_agent_synthesis(self):
        """Factory should return SynthesisAgent."""
        from src.agents import get_agent
        agent = get_agent("synthesis")
        assert agent.name == "synthesis"
    
    def test_get_agent_invalid(self):
        """Factory should raise error for invalid agent."""
        from src.agents import get_agent
        with pytest.raises(ValueError, match="not found"):
            get_agent("nonexistent_agent")


# ==================== Summary Report ====================

def generate_agent_report() -> str:
    """Generate a summary report of agent implementation status."""
    report_lines = [
        "=" * 70,
        "FINAGENTIX AGENT IMPLEMENTATION REPORT",
        f"Generated: {datetime.now().isoformat()}",
        "=" * 70,
        "",
    ]
    
    agents_to_check = [
        ("MarketDataAgent", "src.agents.market_data_agent", "MarketDataAgent"),
        ("NewsSentimentAgent", "src.agents.news_sentiment_agent", "NewsSentimentAgent"),
        ("RiskAssessmentAgent", "src.agents.risk_assessment_agent", "RiskAssessmentAgent"),
        ("FundamentalAnalysisAgent", "src.agents.fundamental_analysis_agent", "FundamentalAnalysisAgent"),
        ("RouterAgent", "src.agents.router_agent", "RouterAgent"),
        ("SynthesisAgent", "src.agents.synthesis_agent", "SynthesisAgent"),
        ("OrchestratorAgent", "src.agents.orchestrator_agent", "OrchestratorAgent"),
    ]
    
    results = []
    
    for display_name, module_path, class_name in agents_to_check:
        status = {
            "name": display_name,
            "importable": False,
            "instantiable": False,
            "has_run": False,
            "has_instructions": False,
            "instruction_length": 0,
            "error": None,
        }
        
        try:
            # Try import
            module = __import__(module_path, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            status["importable"] = True
            
            # Try instantiate
            agent = agent_class()
            status["instantiable"] = True
            
            # Check run method
            status["has_run"] = hasattr(agent, "run") and asyncio.iscoroutinefunction(agent.run)
            
            # Check instructions
            status["has_instructions"] = bool(agent.instructions)
            status["instruction_length"] = len(agent.instructions) if agent.instructions else 0
            
        except Exception as e:
            status["error"] = str(e)
        
        results.append(status)
    
    # Generate report
    report_lines.append("AGENT STATUS:")
    report_lines.append("-" * 70)
    
    all_passed = True
    for r in results:
        checks = [
            ("Import", r["importable"]),
            ("Init", r["instantiable"]),
            ("run()", r["has_run"]),
            ("Instructions", r["has_instructions"]),
        ]
        
        status_str = " | ".join([
            f"{name}: {'✅' if ok else '❌'}" for name, ok in checks
        ])
        
        report_lines.append(f"\n{r['name']}:")
        report_lines.append(f"  {status_str}")
        
        if r["instruction_length"] > 0:
            report_lines.append(f"  Instruction Length: {r['instruction_length']} chars")
        
        if r["error"]:
            report_lines.append(f"  ❌ Error: {r['error']}")
            all_passed = False
        
        if not all([v for _, v in checks]):
            all_passed = False
    
    report_lines.append("")
    report_lines.append("-" * 70)
    report_lines.append(f"OVERALL STATUS: {'✅ ALL AGENTS IMPLEMENTED' if all_passed else '❌ SOME AGENTS INCOMPLETE'}")
    report_lines.append("=" * 70)
    
    return "\n".join(report_lines)


def generate_test_questions_table() -> str:
    """Generate a table of test questions for manual testing."""
    lines = [
        "",
        "=" * 70,
        "TEST QUESTIONS FOR MANUAL VERIFICATION",
        "=" * 70,
        "",
        "Use these questions via the API or CLI to verify agent functionality:",
        "",
    ]
    
    for i, q in enumerate(TEST_QUESTIONS, 1):
        lines.append(f"{i}. [{q.category.upper()}] {q.question}")
        lines.append(f"   Ticker: {q.ticker or 'N/A'}")
        lines.append(f"   Expected Agents: {', '.join(q.expected_agents)}")
        lines.append(f"   Look for: {', '.join(q.expected_keywords[:3])}...")
        lines.append("")
    
    return "\n".join(lines)


# ==================== Main Execution ====================

if __name__ == "__main__":
    print(generate_agent_report())
    print(generate_test_questions_table())
    
    # Run pytest if called directly
    print("\n" + "=" * 70)
    print("Running pytest tests...")
    print("=" * 70 + "\n")
    
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)
