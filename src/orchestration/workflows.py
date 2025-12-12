"""
Orchestration workflows for FinagentiX
Coordinates multiple agents to accomplish complex tasks
"""

import asyncio
from typing import Dict, Any, List, Optional
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import ChatHistory

from ..agents.plugins.market_data_plugin import MarketDataPlugin
from ..agents.plugins.technical_analysis_plugin import TechnicalAnalysisPlugin
from ..agents.plugins.risk_analysis_plugin import RiskAnalysisPlugin
from ..agents.plugins.news_sentiment_plugin import NewsSentimentPlugin
from ..agents.plugins.portfolio_plugin import PortfolioPlugin
from ..redis import ToolCache


class BaseWorkflow:
    """Base class for orchestration workflows"""
    
    def __init__(self, kernel: Optional[Kernel] = None, tool_cache: Optional[ToolCache] = None):
        """
        Initialize workflow
        
        Args:
            kernel: Semantic Kernel instance
            tool_cache: Tool cache for caching plugin outputs
        """
        self.kernel = kernel
        self.tool_cache = tool_cache or ToolCache()
        
        # Initialize plugins
        self.market_data = MarketDataPlugin()
        self.technical_analysis = TechnicalAnalysisPlugin()
        self.risk_analysis = RiskAnalysisPlugin()
        self.news_sentiment = NewsSentimentPlugin()
        self.portfolio = PortfolioPlugin()
    
    async def execute(self, **params) -> Dict[str, Any]:
        """Execute workflow - to be implemented by subclasses"""
        raise NotImplementedError


class InvestmentAnalysisWorkflow(BaseWorkflow):
    """
    Complete investment analysis workflow
    
    Agents: Market Data + Technical Analysis + Risk Analysis + News Sentiment
    Use case: "Should I invest in AAPL?"
    """
    
    async def execute(self, ticker: str, **params) -> Dict[str, Any]:
        """
        Execute investment analysis
        
        Args:
            ticker: Stock ticker symbol
            **params: Additional parameters
        
        Returns:
            Complete investment analysis
        """
        print(f"\n🚀 Starting Investment Analysis for {ticker}")
        
        # Run agents in parallel for speed
        results = await asyncio.gather(
            self._get_market_data(ticker),
            self._get_technical_analysis(ticker),
            self._get_risk_analysis(ticker),
            self._get_news_sentiment(ticker),
            return_exceptions=True
        )
        
        market_data, technical, risk, sentiment = results
        
        # Synthesize recommendation
        recommendation = self._synthesize_recommendation(
            ticker=ticker,
            market_data=market_data,
            technical=technical,
            risk=risk,
            sentiment=sentiment
        )
        
        return {
            "workflow": "InvestmentAnalysisWorkflow",
            "ticker": ticker,
            "market_data": market_data,
            "technical_analysis": technical,
            "risk_analysis": risk,
            "sentiment_analysis": sentiment,
            "recommendation": recommendation,
            "timestamp": "now",
        }
    
    async def _get_market_data(self, ticker: str) -> Dict[str, Any]:
        """Get market data"""
        # Check cache first
        cached = self.tool_cache.get("market_data", ticker=ticker)
        if cached:
            print(f"  ✅ Market data (cached)")
            return cached
        
        # Get current price
        price_data = await self.market_data.get_stock_price(ticker)
        
        # Get historical data
        historical = await self.market_data.get_historical_data(ticker, period="1mo")
        
        result = {
            "current_price": price_data,
            "historical": historical,
        }
        
        # Cache result
        self.tool_cache.set("market_data", result, ticker=ticker, ttl_seconds=60)
        
        print(f"  ✅ Market data")
        return result
    
    async def _get_technical_analysis(self, ticker: str) -> Dict[str, Any]:
        """Get technical analysis"""
        cached = self.tool_cache.get("technical_analysis", ticker=ticker)
        if cached:
            print(f"  ✅ Technical analysis (cached)")
            return cached
        
        # Run technical indicators in parallel
        sma_50 = await self.technical_analysis.calculate_sma(ticker, period=50)
        sma_200 = await self.technical_analysis.calculate_sma(ticker, period=200)
        rsi = await self.technical_analysis.calculate_rsi(ticker, period=14)
        volatility = await self.technical_analysis.get_volatility(ticker, days=30)
        
        result = {
            "sma_50": sma_50,
            "sma_200": sma_200,
            "rsi": rsi,
            "volatility": volatility,
        }
        
        self.tool_cache.set("technical_analysis", result, ticker=ticker, ttl_seconds=300)
        
        print(f"  ✅ Technical analysis")
        return result
    
    async def _get_risk_analysis(self, ticker: str) -> Dict[str, Any]:
        """Get risk analysis"""
        cached = self.tool_cache.get("risk_analysis", ticker=ticker)
        if cached:
            print(f"  ✅ Risk analysis (cached)")
            return cached
        
        # Calculate risk metrics
        var = await self.risk_analysis.calculate_var(ticker, confidence=0.95, holding_period=1)
        volatility = await self.risk_analysis.calculate_volatility(ticker, window=30)
        
        result = {
            "var": var,
            "volatility": volatility,
        }
        
        self.tool_cache.set("risk_analysis", result, ticker=ticker, ttl_seconds=600)
        
        print(f"  ✅ Risk analysis")
        return result
    
    async def _get_news_sentiment(self, ticker: str) -> Dict[str, Any]:
        """Get news sentiment"""
        cached = self.tool_cache.get("news_sentiment", ticker=ticker)
        if cached:
            print(f"  ✅ News sentiment (cached)")
            return cached
        
        # Get news and sentiment
        news = await self.news_sentiment.get_ticker_news(ticker, limit=5)
        sentiment = await self.news_sentiment.get_news_sentiment(ticker)
        
        result = {
            "news": news,
            "sentiment": sentiment,
        }
        
        self.tool_cache.set("news_sentiment", result, ticker=ticker, ttl_seconds=1800)
        
        print(f"  ✅ News sentiment")
        return result
    
    def _synthesize_recommendation(
        self,
        ticker: str,
        market_data: Dict,
        technical: Dict,
        risk: Dict,
        sentiment: Dict
    ) -> Dict[str, Any]:
        """Synthesize investment recommendation"""
        
        # Simple rule-based recommendation (can be enhanced with LLM)
        signals = []
        
        # Technical signals
        if technical.get("sma_50", {}).get("success"):
            sma_50_val = technical["sma_50"].get("sma", 0)
            sma_200_val = technical["sma_200"].get("sma", 0)
            
            if sma_50_val > sma_200_val:
                signals.append("bullish_trend")
            else:
                signals.append("bearish_trend")
        
        # RSI signals
        if technical.get("rsi", {}).get("success"):
            rsi_val = technical["rsi"].get("rsi", 50)
            if rsi_val < 30:
                signals.append("oversold")
            elif rsi_val > 70:
                signals.append("overbought")
        
        # Sentiment signals
        if sentiment.get("sentiment", {}).get("success"):
            sent_score = sentiment["sentiment"].get("overall_sentiment", "neutral")
            if "positive" in sent_score.lower():
                signals.append("positive_sentiment")
            elif "negative" in sent_score.lower():
                signals.append("negative_sentiment")
        
        # Determine overall recommendation
        bullish_count = sum(1 for s in signals if s in ["bullish_trend", "oversold", "positive_sentiment"])
        bearish_count = sum(1 for s in signals if s in ["bearish_trend", "overbought", "negative_sentiment"])
        
        if bullish_count > bearish_count:
            action = "BUY"
            confidence = "moderate"
        elif bearish_count > bullish_count:
            action = "SELL"
            confidence = "moderate"
        else:
            action = "HOLD"
            confidence = "low"
        
        return {
            "action": action,
            "confidence": confidence,
            "signals": signals,
            "summary": f"Based on technical analysis, risk metrics, and sentiment, recommend {action} for {ticker}",
        }


class PortfolioReviewWorkflow(BaseWorkflow):
    """
    Portfolio review workflow
    
    Agents: Portfolio + Risk Analysis
    Use case: "Review my portfolio performance"
    """
    
    async def execute(self, portfolio_id: str = "default", **params) -> Dict[str, Any]:
        """Execute portfolio review"""
        print(f"\n🚀 Starting Portfolio Review")
        
        # Get portfolio data
        positions = await self.portfolio.get_positions(portfolio_id)
        metrics = await self.portfolio.calculate_metrics(portfolio_id)
        allocation = await self.portfolio.analyze_allocation(portfolio_id)
        
        # Get risk analysis for portfolio
        # (This would normally analyze the entire portfolio)
        
        return {
            "workflow": "PortfolioReviewWorkflow",
            "portfolio_id": portfolio_id,
            "positions": positions,
            "metrics": metrics,
            "allocation": allocation,
            "timestamp": "now",
        }


class MarketResearchWorkflow(BaseWorkflow):
    """
    Market research workflow
    
    Agents: Market Data + News Sentiment + Technical Analysis
    Use case: "What's happening in the tech sector?"
    """
    
    async def execute(self, query: str, tickers: Optional[List[str]] = None, **params) -> Dict[str, Any]:
        """Execute market research"""
        print(f"\n🚀 Starting Market Research")
        
        # Default tickers if none provided
        if not tickers:
            tickers = ["AAPL", "MSFT", "GOOGL", "NVDA", "META"]
        
        # Get market overview for each ticker
        results = []
        for ticker in tickers[:5]:  # Limit to 5
            data = await self._get_ticker_overview(ticker)
            results.append(data)
        
        # Get general market news
        market_news = await self.news_sentiment.get_recent_news(limit=10)
        
        return {
            "workflow": "MarketResearchWorkflow",
            "query": query,
            "tickers": results,
            "market_news": market_news,
            "timestamp": "now",
        }
    
    async def _get_ticker_overview(self, ticker: str) -> Dict[str, Any]:
        """Get overview for single ticker"""
        price = await self.market_data.get_stock_price(ticker)
        news = await self.news_sentiment.get_ticker_news(ticker, limit=3)
        
        return {
            "ticker": ticker,
            "price": price,
            "news": news,
        }


class QuickQuoteWorkflow(BaseWorkflow):
    """
    Quick quote workflow
    
    Agents: Market Data only
    Use case: "What's AAPL's price?"
    """
    
    async def execute(self, ticker: str, **params) -> Dict[str, Any]:
        """Execute quick quote"""
        print(f"\n🚀 Getting Quick Quote for {ticker}")
        
        # Get current price only
        price_data = await self.market_data.get_stock_price(ticker)
        
        return {
            "workflow": "QuickQuoteWorkflow",
            "ticker": ticker,
            "price_data": price_data,
            "timestamp": "now",
        }


if __name__ == "__main__":
    # Test workflows
    async def test_workflows():
        # Test Investment Analysis
        workflow = InvestmentAnalysisWorkflow()
        result = await workflow.execute(ticker="AAPL")
        print(f"\n✅ Investment Analysis Result:")
        print(f"   Action: {result['recommendation']['action']}")
        print(f"   Signals: {result['recommendation']['signals']}")
        
        # Test Quick Quote
        quick = QuickQuoteWorkflow()
        result2 = await quick.execute(ticker="MSFT")
        print(f"\n✅ Quick Quote Result:")
        print(f"   Price: {result2['price_data']}")
    
    asyncio.run(test_workflows())
