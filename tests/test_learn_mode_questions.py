#!/usr/bin/env python3
"""
Comprehensive Test Suite for FinagentiX Learn Mode Questions
Tests all predefined questions and validates response format and content.
"""

import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import httpx

# Configuration
API_BASE_URL = "https://ca-agent-api-3ae172dc9e9da.redflower-348a14ef.westus3.azurecontainerapps.io"
TIMEOUT = 60.0  # seconds per request


class ResponseType(Enum):
    NATURAL_LANGUAGE = "natural_language"
    JSON_DATA = "json_data"
    ERROR = "error"


@dataclass
class TestQuestion:
    """Test question definition"""
    id: str
    question: str
    category: str
    expected_workflow: str
    expected_response_type: ResponseType
    validation_patterns: List[str] = field(default_factory=list)
    expected_tickers: List[str] = field(default_factory=list)
    min_response_length: int = 20
    should_not_contain: List[str] = field(default_factory=list)


@dataclass
class TestResult:
    """Test result for a single question"""
    question_id: str
    question: str
    passed: bool
    response: str
    workflow_used: str
    response_time_ms: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ============================================================================
# Test Question Definitions
# ============================================================================

TEST_QUESTIONS: List[TestQuestion] = [
    # Quick Quote Questions
    TestQuestion(
        id="quick-1",
        question="What's the current price of AAPL?",
        category="quick",
        expected_workflow="QuickQuoteWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[
            r"AAPL",
            r"\$[\d,]+\.?\d*",  # Price format
        ],
        expected_tickers=["AAPL"],
        should_not_contain=["workflow", "agent_results", "timestamp"],
    ),
    TestQuestion(
        id="quick-2",
        question="What's Tesla's stock price today?",
        category="quick",
        expected_workflow="QuickQuoteWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[
            r"TSLA|Tesla",
            r"\$[\d,]+\.?\d*",
        ],
        expected_tickers=["TSLA"],
        should_not_contain=["workflow", "agent_results"],
    ),
    TestQuestion(
        id="quick-3",
        question="MSFT stock price",
        category="quick",
        expected_workflow="QuickQuoteWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[
            r"MSFT|Microsoft",
            r"\$[\d,]+\.?\d*",
        ],
        expected_tickers=["MSFT"],
    ),
    TestQuestion(
        id="quick-4",
        question="What's Apple's current stock price?",
        category="quick",
        expected_workflow="QuickQuoteWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[r"AAPL|Apple", r"\$[\d,]+\.?\d*"],
        expected_tickers=["AAPL"],
    ),
    
    # Investment Analysis Questions
    TestQuestion(
        id="invest-1",
        question="Should I invest in NVDA? Give me a comprehensive analysis.",
        category="investment",
        expected_workflow="InvestmentAnalysisWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[
            r"NVDA|Nvidia",
            r"(BUY|SELL|HOLD|recommend|analysis)",
        ],
        expected_tickers=["NVDA"],
        min_response_length=100,
    ),
    TestQuestion(
        id="invest-2",
        question="Analyze Microsoft stock for long-term investment potential.",
        category="investment",
        expected_workflow="InvestmentAnalysisWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[
            r"MSFT|Microsoft",
            r"(analysis|recommend|investment|potential)",
        ],
        expected_tickers=["MSFT"],
        min_response_length=100,
    ),
    TestQuestion(
        id="invest-3",
        question="Is AMD a good investment right now?",
        category="investment",
        expected_workflow="InvestmentAnalysisWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[r"AMD", r"(BUY|SELL|HOLD|recommend|analysis)"],
        expected_tickers=["AMD"],
    ),
    
    # Technical Analysis Questions
    TestQuestion(
        id="tech-1",
        question="What do the technical indicators say about AAPL? Show me RSI, MACD, and Bollinger Bands.",
        category="technical",
        expected_workflow="InvestmentAnalysisWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[
            r"AAPL|Apple",
        ],
        expected_tickers=["AAPL"],
        min_response_length=50,
    ),
    TestQuestion(
        id="tech-2",
        question="Is GOOGL showing any bullish or bearish patterns?",
        category="technical",
        expected_workflow="InvestmentAnalysisWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[
            r"GOOGL|Google|Alphabet",
            r"(bullish|bearish|pattern|signal|trend)",
        ],
        expected_tickers=["GOOGL"],
    ),
    
    # Risk Assessment Questions
    TestQuestion(
        id="risk-1",
        question="How risky is investing in AMD? Calculate VaR and show me the risk metrics.",
        category="risk",
        expected_workflow="InvestmentAnalysisWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[
            r"AMD",
        ],
        expected_tickers=["AMD"],
    ),
    TestQuestion(
        id="risk-2",
        question="What's the beta and volatility of AMZN compared to the market?",
        category="risk",
        expected_workflow="InvestmentAnalysisWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[
            r"AMZN|Amazon",
        ],
        expected_tickers=["AMZN"],
    ),
    
    # Portfolio Review Questions
    TestQuestion(
        id="portfolio-1",
        question="Review my portfolio performance and suggest rebalancing.",
        category="portfolio",
        expected_workflow="PortfolioReviewWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[
            r"(portfolio|position|allocation|rebalance|review)",
        ],
        min_response_length=50,
    ),
    
    # Market Research Questions
    TestQuestion(
        id="market-1",
        question="What's happening in the tech sector today?",
        category="market",
        expected_workflow="MarketResearchWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[
            r"(tech|technology|sector|market)",
        ],
        min_response_length=50,
    ),
    TestQuestion(
        id="market-2",
        question="Summarize the semiconductor industry outlook and analyst views",
        category="market",
        expected_workflow="MarketResearchWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[
            r"(semiconductor|chip|analyst|industry|trend|market|outlook)",
        ],
    ),
    
    # News & Sentiment Questions
    TestQuestion(
        id="news-1",
        question="What is the current market sentiment for Apple based on recent news?",
        category="news",
        expected_workflow="MarketResearchWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[
            r"(Apple|AAPL|sentiment|news)",
        ],
        expected_tickers=["AAPL"],
    ),
    
    # Cache Demo Questions
    TestQuestion(
        id="cache-demo-1",
        question="What's Apple's current stock price?",
        category="quick",
        expected_workflow="QuickQuoteWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[r"AAPL|Apple", r"\$[\d,]+\.?\d*"],
        expected_tickers=["AAPL"],
    ),
    TestQuestion(
        id="cache-demo-2",
        question="Give me a technical analysis of MSFT with RSI and MACD.",
        category="technical",
        expected_workflow="InvestmentAnalysisWorkflow",
        expected_response_type=ResponseType.NATURAL_LANGUAGE,
        validation_patterns=[r"MSFT|Microsoft"],
        expected_tickers=["MSFT"],
    ),
]


# ============================================================================
# Test Execution
# ============================================================================

class TestRunner:
    """Runs tests against the API"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.results: List[TestResult] = []
        self.session_id = f"test-session-{int(time.time())}"
        
    async def run_single_test(self, question: TestQuestion) -> TestResult:
        """Run a single test question"""
        errors = []
        warnings = []
        
        start_time = time.perf_counter()
        
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/api/query/enhanced",
                    json={
                        "query": question.question,
                        "user_id": self.session_id,
                    },
                    headers={"Content-Type": "application/json"},
                )
                
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                
                if response.status_code != 200:
                    return TestResult(
                        question_id=question.id,
                        question=question.question,
                        passed=False,
                        response=f"HTTP {response.status_code}",
                        workflow_used="",
                        response_time_ms=elapsed_ms,
                        errors=[f"HTTP Error: {response.status_code}"],
                    )
                
                data = response.json()
                response_text = data.get("response", "")
                workflow_info = data.get("workflow", {})
                workflow_used = workflow_info.get("workflow_name", "") if isinstance(workflow_info, dict) else ""
                
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return TestResult(
                question_id=question.id,
                question=question.question,
                passed=False,
                response="",
                workflow_used="",
                response_time_ms=elapsed_ms,
                errors=[f"Exception: {str(e)}"],
            )
        
        # Validate response
        passed = True
        
        # 1. Check response type (should not be raw JSON for natural language)
        if question.expected_response_type == ResponseType.NATURAL_LANGUAGE:
            # Check for raw JSON indicators
            if response_text.strip().startswith("{") or '"workflow":' in response_text:
                errors.append("Response appears to be raw JSON instead of natural language")
                passed = False
            
            # Check for JSON structure indicators
            for forbidden in question.should_not_contain:
                if f'"{forbidden}"' in response_text:
                    errors.append(f"Response contains JSON field '{forbidden}'")
                    passed = False
        
        # 2. Check workflow routing
        if question.expected_workflow and workflow_used:
            if workflow_used != question.expected_workflow:
                warnings.append(f"Expected workflow '{question.expected_workflow}', got '{workflow_used}'")
        
        # 3. Check validation patterns
        for pattern in question.validation_patterns:
            if not re.search(pattern, response_text, re.IGNORECASE):
                errors.append(f"Pattern not found: {pattern}")
                passed = False
        
        # 4. Check minimum response length
        if len(response_text) < question.min_response_length:
            errors.append(f"Response too short: {len(response_text)} < {question.min_response_length}")
            passed = False
        
        # 5. Check for error messages
        if "error" in response_text.lower() and "Unable to" in response_text:
            # This might be acceptable for some queries
            warnings.append("Response contains error message")
        
        return TestResult(
            question_id=question.id,
            question=question.question,
            passed=passed,
            response=response_text[:500] + ("..." if len(response_text) > 500 else ""),
            workflow_used=workflow_used,
            response_time_ms=elapsed_ms,
            errors=errors,
            warnings=warnings,
        )
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return summary"""
        print("\n" + "=" * 70)
        print("🧪 FINAGENTIX COMPREHENSIVE API TEST")
        print("=" * 70)
        print(f"API: {self.base_url}")
        print(f"Session: {self.session_id}")
        print(f"Questions: {len(TEST_QUESTIONS)}")
        print("=" * 70 + "\n")
        
        for i, question in enumerate(TEST_QUESTIONS, 1):
            print(f"[{i}/{len(TEST_QUESTIONS)}] Testing: {question.id}")
            print(f"    Question: {question.question[:60]}...")
            
            result = await self.run_single_test(question)
            self.results.append(result)
            
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"    {status} ({result.response_time_ms:.0f}ms)")
            
            if result.errors:
                for error in result.errors:
                    print(f"    ⚠️  Error: {error}")
            
            if result.warnings:
                for warning in result.warnings:
                    print(f"    ℹ️  Warning: {warning}")
            
            print()
            
            # Small delay between requests
            await asyncio.sleep(0.5)
        
        return self.generate_summary()
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate test summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        # Group by category
        category_results = {}
        for result in self.results:
            # Find question to get category
            question = next((q for q in TEST_QUESTIONS if q.id == result.question_id), None)
            if question:
                cat = question.category
                if cat not in category_results:
                    category_results[cat] = {"passed": 0, "failed": 0}
                if result.passed:
                    category_results[cat]["passed"] += 1
                else:
                    category_results[cat]["failed"] += 1
        
        avg_time = sum(r.response_time_ms for r in self.results) / total if total > 0 else 0
        
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")
        print(f"Avg Response Time: {avg_time:.0f}ms")
        print()
        
        print("By Category:")
        for cat, stats in sorted(category_results.items()):
            total_cat = stats["passed"] + stats["failed"]
            pct = stats["passed"] / total_cat * 100 if total_cat > 0 else 0
            print(f"  {cat}: {stats['passed']}/{total_cat} ({pct:.0f}%)")
        
        print()
        
        if failed > 0:
            print("❌ FAILED TESTS:")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.question_id}: {result.question[:50]}...")
                    for error in result.errors:
                        print(f"      Error: {error}")
        
        print("=" * 70)
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total * 100 if total > 0 else 0,
            "avg_response_time_ms": avg_time,
            "by_category": category_results,
            "failed_tests": [r.question_id for r in self.results if not r.passed],
            "results": [
                {
                    "id": r.question_id,
                    "passed": r.passed,
                    "workflow": r.workflow_used,
                    "time_ms": r.response_time_ms,
                    "errors": r.errors,
                    "response_preview": r.response[:200],
                }
                for r in self.results
            ],
        }


async def main():
    """Main entry point"""
    runner = TestRunner()
    summary = await runner.run_all_tests()
    
    # Save results to file
    with open("test_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📁 Results saved to test_results.json")
    
    # Exit with error code if tests failed
    if summary["failed"] > 0:
        print(f"\n❌ {summary['failed']} test(s) failed!")
        return 1
    else:
        print("\n✅ All tests passed!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
