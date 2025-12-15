"""
Cost Tracking and Token Counting Utilities

This module provides accurate cost calculation for Azure OpenAI API calls,
including token counting using tiktoken and cost estimation based on
current Azure OpenAI pricing.
"""

import json
import tiktoken
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


# Azure OpenAI Pricing (as of January 2025)
# Source: https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/
PRICING = {
    "gpt-4o": {
        "input_per_1k": 0.0050,   # $0.005 per 1K input tokens
        "output_per_1k": 0.0150,  # $0.015 per 1K output tokens
    },
    "gpt-4o-mini": {
        "input_per_1k": 0.00015,  # $0.00015 per 1K input tokens
        "output_per_1k": 0.0006,  # $0.0006 per 1K output tokens
    },
    "gpt-4": {
        "input_per_1k": 0.03,     # $0.03 per 1K input tokens
        "output_per_1k": 0.06,    # $0.06 per 1K output tokens
    },
    "gpt-35-turbo": {
        "input_per_1k": 0.0015,   # $0.0015 per 1K input tokens
        "output_per_1k": 0.002,   # $0.002 per 1K output tokens
    },
    "text-embedding-3-large": {
        "per_1k": 0.0010,         # $0.001 per 1K tokens
    },
    "text-embedding-3-small": {
        "per_1k": 0.0002,         # $0.0002 per 1K tokens
    },
    "text-embedding-ada-002": {
        "per_1k": 0.0001,         # $0.0001 per 1K tokens
    }
}


@dataclass
class TokenUsage:
    """Token usage data"""
    input_tokens: int
    output_tokens: int
    total_tokens: int


class CostCalculator:
    """Accurate cost calculation with token counting"""
    
    def __init__(self, model: str = "gpt-4o", embedding_model: str = "text-embedding-3-large"):
        """
        Initialize cost calculator
        
        Args:
            model: LLM model name for token counting
            embedding_model: Embedding model for cost calculation
        """
        self.model = model
        self.embedding_model = embedding_model
        
        # Initialize tiktoken encoder
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base for unknown models
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: Any) -> int:
        """
        Count tokens in text using tiktoken
        
        Args:
            text: Text or structured payload to count tokens for
            
        Returns:
            Number of tokens
        """
        if text is None:
            return 0
        if not isinstance(text, str):
            # Normalize structured responses before token counting
            if isinstance(text, (dict, list)):
                try:
                    text = json.dumps(text, sort_keys=True)
                except (TypeError, ValueError):
                    text = str(text)
            else:
                text = str(text)
        if not text:
            return 0
        return len(self.encoding.encode(text))
    
    def count_messages(self, messages: List[Dict[str, str]]) -> int:
        """
        Count tokens in chat messages format
        
        Based on OpenAI's token counting methodology:
        - Every message has 3 tokens of formatting overhead
        - Role and content are counted
        - Name field (if present) adds tokens
        - 3 tokens added for assistant reply priming
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            
        Returns:
            Total token count
        """
        tokens = 0
        
        for message in messages:
            tokens += 3  # Message formatting overhead
            
            # Count role
            if "role" in message:
                tokens += self.count_tokens(message["role"])
            
            # Count content
            if "content" in message:
                tokens += self.count_tokens(message["content"])
            
            # Count name if present
            if "name" in message:
                tokens += self.count_tokens(message["name"])
        
        tokens += 3  # Assistant reply priming
        
        return tokens
    
    def calculate_llm_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: Optional[str] = None
    ) -> float:
        """
        Calculate cost for LLM API call
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name (uses instance default if None)
            
        Returns:
            Cost in USD
        """
        model_name = model or self.model
        pricing = PRICING.get(model_name, PRICING["gpt-4o"])
        
        input_cost = (input_tokens / 1000) * pricing["input_per_1k"]
        output_cost = (output_tokens / 1000) * pricing["output_per_1k"]
        
        return round(input_cost + output_cost, 6)
    
    def calculate_embedding_cost(
        self,
        tokens: int,
        model: Optional[str] = None
    ) -> float:
        """
        Calculate cost for embedding API call
        
        Args:
            tokens: Number of tokens to embed
            model: Embedding model name (uses instance default if None)
            
        Returns:
            Cost in USD
        """
        model_name = model or self.embedding_model
        pricing = PRICING.get(model_name, PRICING["text-embedding-3-large"])
        
        cost = (tokens / 1000) * pricing["per_1k"]
        
        return round(cost, 6)
    
    def estimate_baseline_cost(self, workflow_name: str) -> Dict[str, float]:
        """
        Estimate cost without caching based on workflow type
        
        This provides a baseline for calculating cache savings by estimating
        what the cost would be if no caching was used.
        
        Args:
            workflow_name: Name of the workflow being executed
            
        Returns:
            Dictionary with cost components:
            - embedding_cost: Cost of query embedding
            - router_cost: Cost of router agent
            - agent_cost: Total cost of all agents
            - total_cost: Sum of all costs
            - per_agent_costs: List of individual agent costs
        """
        # Average token estimates based on workflow type
        WORKFLOW_ESTIMATES = {
            "InvestmentAnalysisWorkflow": {
                "embedding_tokens": 500,
                "router_input": 300,
                "router_output": 50,
                "agents": [
                    {"input": 800, "output": 1200},   # Market Data Agent
                    {"input": 700, "output": 1000},   # Risk Analysis Agent
                    {"input": 600, "output": 900},    # News Sentiment Agent
                    {"input": 900, "output": 1300},   # Synthesis Agent
                ]
            },
            "QuickQuoteWorkflow": {
                "embedding_tokens": 300,
                "router_input": 200,
                "router_output": 30,
                "agents": [
                    {"input": 400, "output": 600},    # Market Data Agent
                    {"input": 300, "output": 400},    # Quick Analysis Agent
                ]
            },
            "PortfolioReviewWorkflow": {
                "embedding_tokens": 600,
                "router_input": 350,
                "router_output": 60,
                "agents": [
                    {"input": 1000, "output": 1500},  # Portfolio Agent
                    {"input": 800, "output": 1200},   # Risk Agent
                    {"input": 700, "output": 1000},   # Performance Agent
                    {"input": 900, "output": 1400},   # Recommendations Agent
                    {"input": 1200, "output": 1800},  # Summary Agent
                ]
            },
            "MarketResearchWorkflow": {
                "embedding_tokens": 550,
                "router_input": 320,
                "router_output": 55,
                "agents": [
                    {"input": 750, "output": 1100},   # Market Data Agent
                    {"input": 850, "output": 1300},   # News Agent
                    {"input": 950, "output": 1450},   # Research Agent
                ]
            }
        }
        
        # Get workflow estimates or use default
        estimates = WORKFLOW_ESTIMATES.get(
            workflow_name,
            {
                "embedding_tokens": 500,
                "router_input": 300,
                "router_output": 50,
                "agents": [
                    {"input": 600, "output": 900},
                    {"input": 600, "output": 900},
                    {"input": 600, "output": 900},
                ]
            }
        )
        
        # Calculate costs
        embedding_cost = self.calculate_embedding_cost(tokens=estimates["embedding_tokens"])
        
        router_cost = self.calculate_llm_cost(
            input_tokens=estimates["router_input"],
            output_tokens=estimates["router_output"]
        )
        
        per_agent_costs = []
        for agent_estimate in estimates["agents"]:
            agent_cost = self.calculate_llm_cost(
                input_tokens=agent_estimate["input"],
                output_tokens=agent_estimate["output"]
            )
            per_agent_costs.append(agent_cost)
        
        total_agent_cost = sum(per_agent_costs)
        total_cost = embedding_cost + router_cost + total_agent_cost
        
        return {
            "embedding_cost": embedding_cost,
            "router_cost": router_cost,
            "agent_cost": total_agent_cost,
            "total_cost": total_cost,
            "per_agent_costs": per_agent_costs,
            "avg_tool_cost": 0.003  # Average tool execution cost estimate
        }
    
    def calculate_cache_savings(
        self,
        semantic_cache_hit: bool,
        router_cache_hit: bool,
        tool_cache_hits: int,
        baseline_scenario: Dict[str, Any]
    ) -> float:
        """
        Calculate cost savings from caching
        
        Args:
            semantic_cache_hit: Whether semantic cache hit
            router_cache_hit: Whether router cache hit
            tool_cache_hits: Number of tool cache hits
            baseline_scenario: Expected costs without caching (from estimate_baseline_cost)
            
        Returns:
            Total cost saved in USD
        """
        savings = 0.0
        
        # Semantic cache hit avoids entire LLM call chain
        if semantic_cache_hit:
            # Save everything except the embedding lookup
            savings += baseline_scenario.get("total_cost", 0.015) - baseline_scenario.get("embedding_cost", 0.001)
        
        # Router cache hit avoids router LLM call
        if router_cache_hit:
            savings += baseline_scenario.get("router_cost", 0.002)
        
        # Each tool cache hit avoids tool execution + potential API calls
        if tool_cache_hits > 0:
            savings += tool_cache_hits * baseline_scenario.get("avg_tool_cost", 0.003)
        
        return round(savings, 6)


# Global instance for easy access
_default_calculator: Optional[CostCalculator] = None


def get_cost_calculator(
    model: str = "gpt-4o",
    embedding_model: str = "text-embedding-3-large"
) -> CostCalculator:
    """
    Get global cost calculator instance (singleton pattern)
    
    Args:
        model: LLM model name
        embedding_model: Embedding model name
        
    Returns:
        CostCalculator instance
    """
    global _default_calculator
    
    if _default_calculator is None:
        _default_calculator = CostCalculator(model=model, embedding_model=embedding_model)
    
    return _default_calculator
