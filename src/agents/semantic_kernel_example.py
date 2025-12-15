"""
Microsoft Agent Framework Implementation Example
Using Semantic Kernel Python SDK

This file demonstrates how to implement FinagentiX agents using
Semantic Kernel's ChatCompletionAgent with proper orchestration patterns.

Official Documentation:
- https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/
- https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview
"""

import asyncio
import os
from typing import Optional, Dict, Any, List
import redis
from pydantic import BaseModel

# Semantic Kernel imports
from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.agents import SequentialOrchestration, ConcurrentOrchestration
from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.functions import kernel_function


# ============================================================================
# STEP 1: Define Structured Data Models
# ============================================================================

class InvestmentQuery(BaseModel):
    """Structured input for investment analysis"""
    ticker: str
    analysis_type: str = "comprehensive"  # comprehensive, technical, fundamental
    risk_tolerance: str = "moderate"  # conservative, moderate, aggressive


class InvestmentRecommendation(BaseModel):
    """Structured output for investment recommendation"""
    action: str  # BUY, SELL, HOLD
    confidence: float  # 0.0 to 1.0
    reasoning: List[str]
    risk_level: str  # LOW, MEDIUM, HIGH
    price_target: Optional[float] = None


# ============================================================================
# STEP 2: Create Semantic Kernel Plugins (Tools)
# ============================================================================

class MarketDataPlugin:
    """
    Plugin for market data operations
    Wraps Redis TimeSeries queries with semantic caching
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    @kernel_function(
        name="get_stock_price",
        description="Get current or historical stock price from Redis TimeSeries"
    )
    async def get_stock_price(self, ticker: str, metric: str = "close") -> Dict[str, Any]:
        """
        Query stock price from Redis TimeSeries
        
        Args:
            ticker: Stock ticker symbol (e.g., AAPL)
            metric: Price metric (open, high, low, close, volume)
        
        Returns:
            Latest price data with timestamp
        """
        try:
            key = f"stock:{ticker}:{metric}"
            # Get last value from TimeSeries
            result = self.redis.execute_command("TS.GET", key)
            
            if result:
                timestamp, value = result
                return {
                    "ticker": ticker,
                    "metric": metric,
                    "value": float(value),
                    "timestamp": timestamp,
                    "success": True
                }
            else:
                return {
                    "ticker": ticker,
                    "error": "No data found",
                    "success": False
                }
        except Exception as e:
            return {
                "ticker": ticker,
                "error": str(e),
                "success": False
            }
    
    @kernel_function(
        name="get_price_range",
        description="Get stock price data for a time range"
    )
    async def get_price_range(
        self, 
        ticker: str, 
        metric: str = "close",
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Query price range from Redis TimeSeries
        
        Args:
            ticker: Stock ticker symbol
            metric: Price metric
            days: Number of days to retrieve
        
        Returns:
            Time series data
        """
        try:
            key = f"stock:{ticker}:{metric}"
            # Calculate timestamp range (last N days)
            import time
            end_ts = int(time.time() * 1000)  # Current timestamp in ms
            start_ts = end_ts - (days * 24 * 60 * 60 * 1000)  # N days ago
            
            # Query range
            result = self.redis.execute_command(
                "TS.RANGE", key, start_ts, end_ts
            )
            
            if result:
                data = [
                    {"timestamp": ts, "value": float(val)}
                    for ts, val in result
                ]
                return {
                    "ticker": ticker,
                    "metric": metric,
                    "data": data,
                    "count": len(data),
                    "success": True
                }
            else:
                return {
                    "ticker": ticker,
                    "error": "No data found",
                    "success": False
                }
        except Exception as e:
            return {
                "ticker": ticker,
                "error": str(e),
                "success": False
            }


class NewsSentimentPlugin:
    """
    Plugin for news sentiment analysis
    Uses Redis vector search for semantic news retrieval
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    @kernel_function(
        name="search_news",
        description="Search news articles using semantic similarity"
    )
    async def search_news(self, query: str, ticker: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search news articles using Redis vector search
        
        Args:
            query: Search query
            ticker: Filter by ticker symbol
            limit: Number of results
        
        Returns:
            Matching news articles with relevance scores
        """
        # TODO: Implement vector search when embeddings are loaded
        # For now, return placeholder
        return {
            "query": query,
            "ticker": ticker,
            "articles": [],
            "note": "Vector search implementation pending",
            "success": True
        }


# ============================================================================
# STEP 3: Initialize Semantic Kernel and Create Agents
# ============================================================================

def create_kernel() -> Kernel:
    """
    Create and configure Semantic Kernel with Azure OpenAI
    """
    kernel = Kernel()
    
    # Add Azure OpenAI service
    kernel.add_service(
        AzureChatCompletion(
            deployment_name="gpt-4",  # or your deployment name
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-08-01-preview"
        )
    )
    
    return kernel


def create_market_data_agent(kernel: Kernel, redis_client: redis.Redis) -> ChatCompletionAgent:
    """
    Create Market Data Agent using Semantic Kernel
    """
    instructions = """
    You are the Market Data Agent for FinagentiX, a financial trading assistant.
    
    Your responsibilities:
    - Query stock prices from Redis TimeSeries
    - Calculate technical indicators
    - Analyze price trends and patterns
    - Provide accurate, real-time market data
    
    You have access to tools:
    - get_stock_price: Get current stock price
    - get_price_range: Get historical price data
    
    Always:
    - Use actual data from tools, never make up prices
    - Include timestamps with all data
    - Handle errors gracefully
    - Cache results for 5 minutes to reduce costs
    
    Format your responses clearly with:
    - Current price
    - Price change ($ and %)
    - Trend direction
    - Data source and timestamp
    """
    
    # Add market data plugin
    market_plugin = MarketDataPlugin(redis_client)
    kernel.add_plugin(market_plugin, plugin_name="MarketData")
    
    # Create agent
    agent = ChatCompletionAgent(
        service_id="azure_openai",
        kernel=kernel,
        name="MarketDataAgent",
        instructions=instructions
    )
    
    return agent


def create_sentiment_agent(kernel: Kernel, redis_client: redis.Redis) -> ChatCompletionAgent:
    """
    Create News Sentiment Agent using Semantic Kernel
    """
    instructions = """
    You are the News Sentiment Agent for FinagentiX.
    
    Your responsibilities:
    - Search and analyze news articles
    - Assess market sentiment from news
    - Identify key themes and trends
    - Detect sentiment shifts
    
    You have access to tools:
    - search_news: Semantic search of news articles
    
    Always:
    - Use vector search to find relevant news
    - Analyze sentiment objectively
    - Cite sources with timestamps
    - Distinguish between facts and opinions
    
    Format your responses with:
    - Overall sentiment (Positive/Neutral/Negative)
    - Key themes
    - Recent developments
    - Sentiment trend (Improving/Stable/Declining)
    """
    
    # Add sentiment plugin
    sentiment_plugin = NewsSentimentPlugin(redis_client)
    kernel.add_plugin(sentiment_plugin, plugin_name="NewsSentiment")
    
    # Create agent
    agent = ChatCompletionAgent(
        service_id="azure_openai",
        kernel=kernel,
        name="NewsSentimentAgent",
        instructions=instructions
    )
    
    return agent


def create_synthesis_agent(kernel: Kernel) -> ChatCompletionAgent:
    """
    Create Synthesis Agent for final recommendations
    """
    instructions = """
    You are the Synthesis Agent for FinagentiX.
    
    Your responsibilities:
    - Combine insights from all agents
    - Generate investment recommendations
    - Assess overall risk
    - Provide actionable advice
    
    You receive:
    - Market data analysis
    - News sentiment analysis
    - Technical analysis
    - Fundamental analysis
    
    Always:
    - Synthesize all perspectives
    - Provide clear BUY/SELL/HOLD recommendation
    - Explain reasoning step-by-step
    - Assess confidence level (0-100%)
    - Note key risks and opportunities
    
    Format your recommendations with:
    - Action (BUY/SELL/HOLD)
    - Confidence level
    - Key reasoning points
    - Risk assessment
    - Price target (if applicable)
    """
    
    # Create agent (no tools needed, synthesizes other agents' outputs)
    agent = ChatCompletionAgent(
        service_id="azure_openai",
        kernel=kernel,
        name="SynthesisAgent",
        instructions=instructions
    )
    
    return agent


# ============================================================================
# STEP 4: Implement Orchestration Patterns
# ============================================================================

async def sequential_analysis_workflow(
    ticker: str,
    redis_client: redis.Redis
) -> Dict[str, Any]:
    """
    Sequential orchestration: Market Data → Sentiment → Synthesis
    
    This pattern runs agents in order, passing results from one to the next.
    """
    # Initialize
    kernel = create_kernel()
    runtime = InProcessRuntime()
    runtime.start()
    
    # Create agents
    market_agent = create_market_data_agent(kernel, redis_client)
    sentiment_agent = create_sentiment_agent(kernel, redis_client)
    synthesis_agent = create_synthesis_agent(kernel)
    
    # Create sequential orchestration
    workflow = SequentialOrchestration(
        members=[market_agent, sentiment_agent, synthesis_agent]
    )
    
    # Execute workflow
    task = f"Analyze {ticker} for investment potential"
    result = await workflow.invoke(task=task, runtime=runtime)
    
    # Get final result
    final_result = await result.get(timeout=30)
    
    # Stop runtime
    await runtime.stop_when_idle()
    
    return final_result


async def concurrent_analysis_workflow(
    ticker: str,
    redis_client: redis.Redis
) -> Dict[str, Any]:
    """
    Concurrent orchestration: Market + Sentiment in parallel → Synthesis
    
    This pattern runs multiple agents simultaneously for faster results.
    """
    # Initialize
    kernel = create_kernel()
    runtime = InProcessRuntime()
    runtime.start()
    
    # Create agents
    market_agent = create_market_data_agent(kernel, redis_client)
    sentiment_agent = create_sentiment_agent(kernel, redis_client)
    
    # Create concurrent orchestration for data gathering
    parallel_workflow = ConcurrentOrchestration(
        members=[market_agent, sentiment_agent]
    )
    
    # Execute parallel data gathering
    task = f"Gather all data for {ticker}"
    result = await parallel_workflow.invoke(task=task, runtime=runtime)
    parallel_results = await result.get(timeout=30)
    
    # Now synthesize results
    synthesis_agent = create_synthesis_agent(kernel)
    synthesis_task = f"Based on the analysis: {parallel_results}, provide investment recommendation for {ticker}"
    synthesis_result = await synthesis_agent.invoke(task=synthesis_task, runtime=runtime)
    final_result = await synthesis_result.get(timeout=30)
    
    # Stop runtime
    await runtime.stop_when_idle()
    
    return final_result


# ============================================================================
# STEP 5: Example Usage
# ============================================================================

async def main():
    """
    Example: Run sequential and concurrent workflows
    """
    # Connect to Redis
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT", "10000")),
        password=os.getenv("REDIS_PASSWORD"),
        ssl=True,
        decode_responses=True
    )
    
    ticker = "AAPL"
    
    print(f"\n{'='*80}")
    print(f"SEQUENTIAL WORKFLOW: Analyzing {ticker}")
    print(f"{'='*80}\n")
    
    sequential_result = await sequential_analysis_workflow(ticker, redis_client)
    print(f"Result: {sequential_result}\n")
    
    print(f"\n{'='*80}")
    print(f"CONCURRENT WORKFLOW: Analyzing {ticker}")
    print(f"{'='*80}\n")
    
    concurrent_result = await concurrent_analysis_workflow(ticker, redis_client)
    print(f"Result: {concurrent_result}\n")


if __name__ == "__main__":
    # Run example
    asyncio.run(main())


# ============================================================================
# NEXT STEPS FOR IMPLEMENTATION
# ============================================================================

"""
1. Install Semantic Kernel:
   pip install semantic-kernel[azure]

2. Set environment variables (see .env for canonical values):
    export AZURE_OPENAI_ENDPOINT="https://<your-endpoint>.openai.azure.com/"
    export AZURE_OPENAI_KEY="<your-api-key>"
    export REDIS_HOST="<your-redis-hostname>"
    export REDIS_PORT="<your-redis-port>"
    export REDIS_PASSWORD="<your-redis-password>"

3. Implement remaining agents:
   - Risk Assessment Agent
   - Technical Analysis Agent
   - Fundamental Analysis Agent
   - Portfolio Management Agent
   - Report Generation Agent

4. Add advanced features:
   - OpenTelemetry observability
   - Structured input/output with Pydantic
   - Human-in-the-loop workflows
   - Model Context Protocol (MCP) integration

5. Deploy to Azure Container Apps:
   - Create FastAPI wrapper
   - Build Docker container
   - Deploy with Bicep template
   - Configure monitoring

See MICROSOFT_AGENT_FRAMEWORK_MIGRATION.md for full migration plan.
"""
