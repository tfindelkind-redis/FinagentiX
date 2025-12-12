# Test Fix Reference Guide

## Current Status
- **43/109 tests passing (39.4%)**
- Market Data Plugin: ✅ 19/19 (100%)
- Infrastructure: ✅ Complete and proven
- Remaining: Test expectations vs implementation alignment

## Quick Fix Guide

### Portfolio Plugin

**Function Name Changes**:
```python
# Tests Call → Should Call
get_portfolio_summary() → get_positions()
calculate_performance() → calculate_metrics()  # No 'days' param
get_top_performers() → get_performance()       # Takes 'days' param
```

**Return Structure - `get_positions()`**:
```python
{
    "portfolio_id": str,
    "positions": [
        {
            "ticker": str,
            "shares": float,
            "cost_basis": float,
            "current_price": float,
            "current_value": float,
            "gain_loss": float,
            "gain_loss_pct": float,
            "allocation_pct": float
        }
    ],
    "total_value": float,
    "success": bool
}
```

**Return Structure - `analyze_allocation()`**:
```python
{
    "portfolio_id": str,
    "diversification": str,  # "low", "moderate", "high"
    "concentration_risk": str,
    "large_positions": int,
    "recommendation": str,
    "success": bool
}
# Note: No 'allocations' array in response
```

### Technical Analysis Plugin

**Function Name/Parameter Changes**:
```python
# Tests Call → Should Call
calculate_moving_averages(periods=[20,50]) → calculate_sma(period=20)
identify_patterns() → detect_crossover()
calculate_volatility() → get_volatility()
get_momentum_indicators() → calculate_rsi()  # Or create new tests
```

**Return Structure - `calculate_rsi()`**:
```python
{
    "ticker": str,
    "rsi": float,
    "period": int,
    "signal": str,  # Full sentence, not just "oversold"
    "current_price": float,
    "success": bool
}
# signal examples:
# - "consider buying or accumulating"
# - "consider selling or taking profits"  
# - "no strong signal"
```

**Return Structure - `detect_crossover()`**:
```python
{
    "ticker": str,
    "crossover_type": str,  # "bullish", "bearish", "none"
    "short_ma": {"period": int, "value": float},
    "long_ma": {"period": int, "value": float},
    "current_price": float,
    "success": bool
}
# Note: No 'patterns' array
```

### Risk Analysis Plugin

**Return Structure - `calculate_var()`**:
```python
{
    "ticker": str,
    "var_pct": float,
    "var_dollar": float,
    "risk_level": str,
    "holding_period": int,
    "success": bool
}
# Note: No 'confidence' field in return
```

**Return Structure - `stress_test()`**:
```python
{
    "ticker": str,
    "scenarios": [
        {
            "scenario": str,        # Not 'name'
            "description": str,
            "loss_pct": float,
            "loss_dollar": float
            # No 'severity' field
        }
    ],
    "worst_case_loss": float,
    "success": bool
}
```

**Return Structure - `assess_tail_risk()`**:
```python
{
    "ticker": str,
    "kurtosis": float,
    "tail_events_total": int,
    "assessment": str,  # Not 'tail_risk_level'
    "success": bool
}
```

### News Sentiment Plugin

**Functions that don't exist - need to skip or rewrite**:
- ❌ `analyze_sentiment()` - use `get_news_sentiment()` instead
- ❌ `get_sentiment_summary()` - doesn't exist
- ❌ `get_trending_topics()` - doesn't exist  
- ❌ `get_sentiment_timeline()` - doesn't exist

**Actual Functions**:
- ✅ `search_news(query, limit=5)`
- ✅ `get_ticker_news(ticker, limit=5)`
- ✅ `get_recent_news(limit=10)`
- ✅ `get_news_sentiment(ticker)`
- ✅ `analyze_news_impact(ticker, days=7)`

**Return Structure - `search_news()`**:
```python
{
    "query": str,
    "results": [  # Not 'articles'
        {
            "id": str,
            "title": str,
            "content": str,
            "ticker": str,
            "date": str,
            "sentiment": str,
            "source": str
        }
    ],
    "count": int,
    "success": bool
}
```

## Fix Strategy

### Option 1: Quick Wins (Recommended)
Focus on fixing tests that just need parameter/name changes:
1. Portfolio: Function name changes (30 min)
2. Technical: Parameter fixes (30 min)  
3. Risk: Return field adjustments (30 min)

**Expected Result**: 70-80 passing tests

### Option 2: Complete Overhaul
Rewrite News Sentiment tests to match actual functions (2-3 hours)

### Option 3: Skip Non-Existent Functions
Comment out tests for functions that don't exist, document as TODO

## Example Fixes

### Fix Portfolio Tests
```python
# Before
result = await plugin.get_portfolio_summary("default")
assert result_dict["total_positions"] == 3

# After  
result = await plugin.get_positions("default")
assert len(result["positions"]) == 3
```

### Fix Technical Analysis Tests
```python
# Before
result = await plugin.calculate_moving_averages("AAPL", periods=[20, 50])
assert result["ma_20"] == 150.0

# After
result = await plugin.calculate_sma("AAPL", period=20)
assert result["sma"] == 150.0
```

### Fix Risk Analysis Tests
```python
# Before
assert result_dict["confidence"] == 0.95

# After
# Remove - 'confidence' is input param, not in return
```

## Validation

After fixes, run:
```bash
pytest tests/agents/test_portfolio_plugin.py -v
pytest tests/agents/test_technical_analysis_plugin.py -v
pytest tests/agents/test_risk_analysis_plugin.py -v
```

Target: >90% passing for each plugin
