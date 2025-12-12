"""
Test script for new metrics and cost tracking components

This script validates that the enhanced metrics collection system works correctly.
Run this to verify Phase 1 implementation before proceeding to Phase 2.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.cost_tracking import CostCalculator, get_cost_calculator
from src.utils.metrics_collector import MetricsCollector
from src.api.models import (
    EnhancedQueryResponse,
    AgentExecution,
    CacheLayerMetrics,
    CostBreakdown,
    PerformanceMetrics,
    WorkflowExecution,
    SessionMetrics,
    ExecutionTimeline,
    ToolInvocation
)
from datetime import datetime


def test_cost_calculator():
    """Test cost calculation functionality"""
    print("\n" + "="*60)
    print("Testing CostCalculator")
    print("="*60)
    
    calc = CostCalculator(model="gpt-4o")
    
    # Test 1: Token counting
    print("\n1. Token Counting")
    text = "Should I invest in TSLA stock?"
    tokens = calc.count_tokens(text)
    print(f"   Text: '{text}'")
    print(f"   Tokens: {tokens}")
    assert tokens > 0, "Token count should be positive"
    print("   ✅ Token counting works")
    
    # Test 2: LLM cost calculation
    print("\n2. LLM Cost Calculation")
    input_tokens = 1000
    output_tokens = 500
    cost = calc.calculate_llm_cost(input_tokens, output_tokens)
    expected = (1000/1000 * 0.005) + (500/1000 * 0.015)
    print(f"   Input: {input_tokens} tokens")
    print(f"   Output: {output_tokens} tokens")
    print(f"   Cost: ${cost:.6f}")
    print(f"   Expected: ${expected:.6f}")
    assert abs(cost - expected) < 0.000001, "Cost calculation incorrect"
    print("   ✅ LLM cost calculation accurate")
    
    # Test 3: Embedding cost calculation
    print("\n3. Embedding Cost Calculation")
    embed_tokens = 1200
    embed_cost = calc.calculate_embedding_cost(embed_tokens)
    expected_embed = 1200/1000 * 0.001
    print(f"   Tokens: {embed_tokens}")
    print(f"   Cost: ${embed_cost:.6f}")
    print(f"   Expected: ${expected_embed:.6f}")
    assert abs(embed_cost - expected_embed) < 0.000001, "Embedding cost incorrect"
    print("   ✅ Embedding cost calculation accurate")
    
    # Test 4: Baseline estimation
    print("\n4. Baseline Cost Estimation")
    baseline = calc.estimate_baseline_cost("InvestmentAnalysisWorkflow")
    print(f"   Workflow: InvestmentAnalysisWorkflow")
    print(f"   Embedding cost: ${baseline['embedding_cost']:.6f}")
    print(f"   Router cost: ${baseline['router_cost']:.6f}")
    print(f"   Agent cost: ${baseline['agent_cost']:.6f}")
    print(f"   Total baseline: ${baseline['total_cost']:.6f}")
    assert baseline['total_cost'] > 0, "Baseline should be positive"
    print("   ✅ Baseline estimation works")
    
    # Test 5: Cache savings calculation
    print("\n5. Cache Savings Calculation")
    savings = calc.calculate_cache_savings(
        semantic_cache_hit=True,
        router_cache_hit=False,
        tool_cache_hits=2,
        baseline_scenario=baseline
    )
    print(f"   Semantic cache hit: True")
    print(f"   Router cache hit: False")
    print(f"   Tool cache hits: 2")
    print(f"   Savings: ${savings:.6f}")
    assert savings > 0, "Savings should be positive"
    print("   ✅ Cache savings calculation works")
    
    print("\n✅ All CostCalculator tests passed!")


def test_metrics_collector():
    """Test metrics collection functionality"""
    print("\n" + "="*60)
    print("Testing MetricsCollector")
    print("="*60)
    
    # Initialize collector
    collector = MetricsCollector(
        query="Should I invest in TSLA?",
        session_id="test_session_123",
        user_id="test_user"
    )
    
    print(f"\n✅ MetricsCollector initialized")
    print(f"   Query ID: {collector.query_id}")
    print(f"   Session ID: {collector.session_id}")
    
    # Test 1: Event tracking
    print("\n1. Event Tracking")
    event_id = collector.start_event("cache_check", "Semantic Cache Lookup")
    print(f"   Started event: {event_id}")
    
    import time
    time.sleep(0.05)  # Simulate work
    
    collector.end_event(event_id, status="miss", metadata={"similarity": 0.81})
    print(f"   Ended event: {event_id}")
    print(f"   Duration: {collector.events[0]['duration_ms']:.2f}ms")
    assert len(collector.events) == 1, "Should have 1 event"
    print("   ✅ Event tracking works")
    
    # Test 2: Agent execution recording
    print("\n2. Agent Execution Recording")
    collector.record_agent_execution(
        agent_name="Market Data Agent",
        agent_id="market_data_v2",
        duration_ms=380,
        input_tokens=245,
        output_tokens=512,
        model="gpt-4o",
        cost=0.0023,
        status="success",
        response="TSLA is currently trading at $245.67"
    )
    print(f"   Recorded agent: Market Data Agent")
    print(f"   Duration: 380ms")
    print(f"   Tokens: 245 in / 512 out")
    print(f"   Cost: $0.0023")
    assert len(collector.agent_executions) == 1, "Should have 1 agent execution"
    assert collector.total_input_tokens == 245, "Input tokens should match"
    assert collector.total_output_tokens == 512, "Output tokens should match"
    print("   ✅ Agent execution recording works")
    
    # Test 3: Cache check recording
    print("\n3. Cache Check Recording")
    collector.record_cache_check(
        layer_name="semantic_cache",
        hit=False,
        similarity=0.81,
        query_time_ms=12.5,
        cost_saved=0.0
    )
    print(f"   Recorded cache check: semantic_cache")
    print(f"   Hit: False")
    print(f"   Similarity: 0.81")
    assert len(collector.cache_checks) == 1, "Should have 1 cache check"
    print("   ✅ Cache check recording works")
    
    # Test 4: Tool invocation recording
    print("\n4. Tool Invocation Recording")
    collector.record_tool_invocation(
        tool_name="get_stock_price",
        parameters={"ticker": "TSLA"},
        duration_ms=145,
        cache_hit=True,
        cache_similarity=0.97,
        result_size=1024,
        status="success"
    )
    print(f"   Recorded tool: get_stock_price")
    print(f"   Cache hit: True")
    print(f"   Duration: 145ms")
    assert len(collector.tool_invocations) == 1, "Should have 1 tool invocation"
    print("   ✅ Tool invocation recording works")
    
    # Test 5: Timeline generation
    print("\n5. Timeline Generation")
    timeline = collector.get_timeline_data()
    print(f"   Total duration: {timeline['total_duration_ms']:.2f}ms")
    print(f"   Events: {len(timeline['events'])}")
    assert timeline['total_duration_ms'] > 0, "Timeline duration should be positive"
    print("   ✅ Timeline generation works")
    
    # Test 6: Cost calculation
    print("\n6. Cost Calculation")
    collector.record_embedding(500)  # Record embedding call
    costs = collector.calculate_costs("InvestmentAnalysisWorkflow")
    print(f"   Total cost: ${costs['total_cost_usd']:.6f}")
    print(f"   Baseline: ${costs['baseline_cost_usd']:.6f}")
    print(f"   Savings: ${costs['cost_savings_usd']:.6f} ({costs['cost_savings_percent']:.1f}%)")
    assert costs['total_cost_usd'] > 0, "Total cost should be positive"
    assert costs['cost_savings_percent'] >= 0, "Savings percent should be non-negative"
    print("   ✅ Cost calculation works")
    
    # Test 7: Performance metrics
    print("\n7. Performance Metrics")
    collector.record_network_request("azure_openai", 280)
    collector.record_network_request("redis", 3)
    perf = collector.get_performance_metrics(collector.get_timeline_data()['total_duration_ms'])
    print(f"   Total time: {perf['total_time_ms']:.2f}ms")
    print(f"   Azure OpenAI latency: {perf['azure_openai_avg_latency_ms']:.2f}ms")
    print(f"   Redis latency: {perf['redis_avg_latency_ms']:.2f}ms")
    print(f"   Meets latency target: {perf['meets_latency_target']}")
    assert perf['total_time_ms'] > 0, "Total time should be positive"
    print("   ✅ Performance metrics work")
    
    print("\n✅ All MetricsCollector tests passed!")


def test_pydantic_models():
    """Test Pydantic model creation"""
    print("\n" + "="*60)
    print("Testing Pydantic Models")
    print("="*60)
    
    # Test 1: ToolInvocation
    print("\n1. ToolInvocation Model")
    tool = ToolInvocation(
        tool_name="get_stock_price",
        parameters={"ticker": "TSLA"},
        duration_ms=145.5,
        cache_hit=True,
        cache_similarity=0.97,
        result_size_bytes=1024,
        status="success"
    )
    print(f"   Created: {tool.tool_name}")
    print(f"   Cache hit: {tool.cache_hit}")
    print("   ✅ ToolInvocation model works")
    
    # Test 2: AgentExecution
    print("\n2. AgentExecution Model")
    agent = AgentExecution(
        agent_name="Market Data Agent",
        agent_id="market_data_v2",
        agent_index=0,
        start_time=datetime.now(),
        end_time=datetime.now(),
        duration_ms=380,
        status="success",
        input_tokens=245,
        output_tokens=512,
        total_tokens=757,
        model_used="gpt-4o",
        temperature=0.1,
        max_tokens=1500,
        cost_usd=0.0023,
        tools_invoked=[tool]
    )
    print(f"   Created: {agent.agent_name}")
    print(f"   Duration: {agent.duration_ms}ms")
    print(f"   Tools: {len(agent.tools_invoked)}")
    print("   ✅ AgentExecution model works")
    
    # Test 3: CacheLayerMetrics
    print("\n3. CacheLayerMetrics Model")
    cache = CacheLayerMetrics(
        layer_name="semantic_cache",
        checked=True,
        hit=False,
        similarity=0.81,
        query_time_ms=12.5,
        cost_saved_usd=0.0
    )
    print(f"   Created: {cache.layer_name}")
    print(f"   Hit: {cache.hit}")
    print("   ✅ CacheLayerMetrics model works")
    
    # Test 4: CostBreakdown
    print("\n4. CostBreakdown Model")
    cost = CostBreakdown(
        embedding_api_calls=1,
        embedding_total_tokens=1200,
        embedding_cost_usd=0.0012,
        llm_api_calls=4,
        llm_input_tokens=1450,
        llm_output_tokens=2050,
        llm_total_tokens=3500,
        llm_cost_usd=0.0070,
        total_cost_usd=0.0082,
        baseline_cost_usd=0.0615,
        cost_savings_usd=0.0533,
        cost_savings_percent=87,
        cost_per_agent={"market_data": 0.0023}
    )
    print(f"   Total cost: ${cost.total_cost_usd}")
    print(f"   Savings: {cost.cost_savings_percent}%")
    print("   ✅ CostBreakdown model works")
    
    # Test 5: Complete EnhancedQueryResponse
    print("\n5. EnhancedQueryResponse Model")
    response = EnhancedQueryResponse(
        query="Should I invest in TSLA?",
        response="Based on analysis...",
        timestamp=datetime.now(),
        query_id="test_123",
        workflow=WorkflowExecution(
            workflow_name="InvestmentAnalysisWorkflow",
            orchestration_pattern="sequential",
            routing_time_ms=150,
            agents_invoked_count=4,
            agents_available_count=7
        ),
        agents=[agent],
        cache_layers=[cache],
        overall_cache_hit=False,
        cost=cost,
        performance=PerformanceMetrics(
            queue_time_ms=4,
            processing_time_ms=1446,
            total_time_ms=1450,
            azure_openai_avg_latency_ms=280,
            redis_avg_latency_ms=3,
            network_total_requests=5,
            meets_latency_target=True,
            meets_cost_target=True
        ),
        session=SessionMetrics(
            session_id="session_123",
            query_count=47,
            avg_latency_ms=1203,
            total_cost_usd=0.3854,
            cache_hit_rate=68.1
        ),
        timeline=ExecutionTimeline(
            total_duration_ms=1450,
            events=[]
        )
    )
    print(f"   Created complete response")
    print(f"   Query: {response.query}")
    print(f"   Agents: {len(response.agents)}")
    print(f"   Total cost: ${response.cost.total_cost_usd}")
    print(f"   Savings: {response.cost.cost_savings_percent}%")
    print("   ✅ EnhancedQueryResponse model works")
    
    # Test JSON serialization
    print("\n6. JSON Serialization")
    json_data = response.model_dump_json(indent=2)
    print(f"   Serialized to JSON: {len(json_data)} bytes")
    assert len(json_data) > 0, "JSON should not be empty"
    print("   ✅ JSON serialization works")
    
    print("\n✅ All Pydantic model tests passed!")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("FinagentiX Phase 1 - Component Testing")
    print("="*60)
    
    try:
        test_cost_calculator()
        test_metrics_collector()
        test_pydantic_models()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nPhase 1 backend components are working correctly.")
        print("Ready to proceed with Phase 2: Integration")
        print("\nNext steps:")
        print("  1. Update orchestrations to use MetricsCollector")
        print("  2. Enhance cache layers with metrics tracking")
        print("  3. Update main API endpoint to return EnhancedQueryResponse")
        print("  4. Add new metrics endpoints")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
