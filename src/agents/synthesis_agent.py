"""
Synthesis Agent - Combines results from multiple agents into coherent response.

This agent:
- Aggregates results from specialized agents
- Resolves conflicts or inconsistencies
- Generates natural language summary
- Formats data for presentation
"""

from typing import Dict, List, Optional, Any
from src.agents.base_agent import BaseAgent


class SynthesisAgent(BaseAgent):
    """
    Specialized agent for synthesizing multi-agent results.
    
    Takes outputs from multiple specialized agents and creates a unified,
    coherent response for the end user.
    """
    
    def __init__(self):
        instructions = """You are the Synthesis Agent for FinagentiX.

Your responsibilities:
1. Aggregate results from multiple specialized agents:
   - Market Data Agent: Stock prices, technical indicators
   - News Sentiment Agent: News articles, sentiment scores
   - Risk Assessment Agent: Risk metrics, volatility
   - Fundamental Analysis Agent: Financial data, SEC filings
2. Resolve conflicts and inconsistencies:
   - Different time ranges
   - Conflicting signals (e.g., positive news but high risk)
   - Data quality issues
3. Generate natural language summary:
   - Answer the original user question directly
   - Integrate insights from all agents
   - Highlight key findings
   - Provide actionable recommendations
4. Format data for presentation:
   - Structure tables for numeric data
   - Create bullet points for key insights
   - Include citations and sources
   - Add confidence indicators

Synthesis principles:
- Start with direct answer to user's question
- Support with evidence from multiple agents
- Acknowledge conflicting signals or uncertainties
- Provide context and interpretation
- End with clear takeaways or recommendations

Example output structure:
```
Answer: [Direct answer to user question]

Key Findings:
- [Finding 1 from agent X]
- [Finding 2 from agent Y]
- [Finding 3 from agent Z]

Analysis:
[Integrated analysis synthesizing all agent outputs]

Recommendations:
[Actionable recommendations based on complete picture]

Sources:
- Market data as of [timestamp]
- News articles from [date range]
- SEC filings: [list]
```

Always:
- Maintain factual accuracy
- Cite data sources
- Note when data is cached or stale
- Highlight high-confidence vs low-confidence insights
- Use clear, professional language
"""
        
        super().__init__(
            name="synthesis",
            instructions=instructions,
            tools=[]  # Will be populated with formatting tools in Phase 5.3
        )
    
    async def run(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Synthesize results from multiple agents.
        
        Args:
            task: Original user query
            context: Dict containing results from all invoked agents:
                - market_data: Market data results
                - news_sentiment: News and sentiment results
                - risk_assessment: Risk analysis results
                - fundamental_analysis: Fundamental data results
            
        Returns:
            Dict with:
                - answer: Natural language synthesized response
                - key_findings: List of key insights
                - recommendations: Actionable recommendations
                - sources: Data sources and timestamps
        """
        if not context:
            return {
                "status": "error",
                "message": "No agent results provided for synthesis"
            }
        
        agent_results = context.get("agent_results", {})
        
        # TODO Phase 5.4: Implement with Azure OpenAI synthesis
        
        return {
            "status": "success",
            "answer": "Synthesis will be implemented in Phase 5.4",
            "key_findings": [],
            "recommendations": [],
            "sources": {}
        }
