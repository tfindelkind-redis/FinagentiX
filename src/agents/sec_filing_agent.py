"""
SEC Filing Search Agent - Semantic Kernel Agent for Document Search

Provides natural language interface to SEC filings and financial documents.
Uses RAG (Retrieval-Augmented Generation) for Q&A.
"""

import logging
from typing import Annotated

from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.kernel import Kernel
from semantic_kernel.functions import kernel_function

from ..redis.rag_retriever import RAGRetriever, RAGResult

logger = logging.getLogger(__name__)


class SECFilingPlugin:
    """
    Plugin for searching and analyzing SEC filings.
    
    Tools:
    - search_filings: Search across SEC documents
    - get_filing_summary: Summarize a specific filing
    - compare_filings: Compare filings across periods
    """
    
    def __init__(self, rag_retriever: RAGRetriever):
        """Initialize with RAG retriever."""
        self.rag = rag_retriever
    
    @kernel_function(
        name="search_filings",
        description="Search SEC filings (10-K, 10-Q, 8-K) for specific information. Use for questions about company financials, risks, business operations."
    )
    async def search_filings(
        self,
        question: Annotated[str, "The question to answer using SEC filings"],
        ticker: Annotated[str, "Stock ticker symbol (e.g., AAPL, MSFT)"] = "",
        doc_type: Annotated[str, "Document type: 10-K (annual), 10-Q (quarterly), 8-K (events)"] = "",
    ) -> Annotated[str, "Answer with citations to SEC filings"]:
        """Search SEC filings and answer questions."""
        logger.info(f"Searching SEC filings: {question} (ticker={ticker}, doc_type={doc_type})")
        
        try:
            result: RAGResult = await self.rag.ask(
                question=question,
                ticker=ticker if ticker else None,
                doc_type=doc_type if doc_type else None,
                source="SEC",
                top_k=5,
            )
            
            # Format response with sources
            response_parts = [result.answer]
            
            if result.sources:
                response_parts.append("\n\n**Sources:**")
                for i, source in enumerate(result.sources, 1):
                    response_parts.append(
                        f"{i}. {source['title']} ({source['filing_date'] or 'N/A'}) "
                        f"- Relevance: {int(source['relevance_score'] * 100)}%"
                    )
                    if source.get('url'):
                        response_parts.append(f"   URL: {source['url']}")
            
            response_parts.append(f"\n*Confidence: {result.confidence}*")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"SEC filing search failed: {e}")
            return f"Error searching SEC filings: {str(e)}"
    
    @kernel_function(
        name="get_filing_summary",
        description="Get a comprehensive summary of a specific SEC filing (10-K or 10-Q) for a company."
    )
    async def get_filing_summary(
        self,
        ticker: Annotated[str, "Stock ticker symbol (e.g., AAPL, MSFT)"],
        doc_type: Annotated[str, "Document type: 10-K (annual) or 10-Q (quarterly)"],
        filing_date: Annotated[str, "Optional filing date (YYYY-MM-DD)"] = "",
    ) -> Annotated[str, "Structured summary of the filing"]:
        """Get a summary of a specific SEC filing."""
        logger.info(f"Summarizing {doc_type} for {ticker} (date={filing_date})")
        
        try:
            result: RAGResult = await self.rag.summarize_document(
                ticker=ticker,
                doc_type=doc_type,
                filing_date=filing_date if filing_date else None,
            )
            
            response_parts = [
                f"# {ticker} {doc_type} Summary\n",
                result.answer,
            ]
            
            if result.sources and result.sources[0].get('filing_date'):
                response_parts.append(f"\n*Filing Date: {result.sources[0]['filing_date']}*")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Filing summary failed: {e}")
            return f"Error generating filing summary: {str(e)}"
    
    @kernel_function(
        name="search_news",
        description="Search financial news articles about a company or topic."
    )
    async def search_news(
        self,
        question: Annotated[str, "Question or topic to search in news"],
        ticker: Annotated[str, "Stock ticker symbol (optional)"] = "",
    ) -> Annotated[str, "News search results with citations"]:
        """Search financial news articles."""
        logger.info(f"Searching news: {question} (ticker={ticker})")
        
        try:
            result: RAGResult = await self.rag.ask(
                question=question,
                ticker=ticker if ticker else None,
                source="NewsAPI",
                top_k=5,
            )
            
            # Format response
            response_parts = [result.answer]
            
            if result.sources:
                response_parts.append("\n\n**News Sources:**")
                for i, source in enumerate(result.sources, 1):
                    response_parts.append(
                        f"{i}. {source['title']} ({source['filing_date'] or 'Recent'})"
                    )
                    if source.get('excerpt'):
                        response_parts.append(f"   \"{source['excerpt']}\"")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"News search failed: {e}")
            return f"Error searching news: {str(e)}"


class SECFilingAgent:
    """
    SEC Filing Search Agent using Semantic Kernel.
    
    Provides natural language Q&A on:
    - SEC filings (10-K, 10-Q, 8-K)
    - Earnings transcripts
    - Financial news
    - Research reports
    """
    
    def __init__(
        self,
        kernel: Kernel,
        service_id: str,
        rag_retriever: RAGRetriever,
        name: str = "SEC Filing Agent",
    ):
        """Initialize SEC filing agent."""
        self.kernel = kernel
        self.service_id = service_id
        self.rag = rag_retriever
        
        # Add SEC filing plugin to kernel
        sec_plugin = SECFilingPlugin(rag_retriever)
        self.kernel.add_plugin(sec_plugin, plugin_name="sec_filing_plugin")
        
        # Create agent
        self.agent = ChatCompletionAgent(
            service_id=service_id,
            kernel=kernel,
            name=name,
            instructions="""You are a financial document research assistant specializing in SEC filings and financial news.

Your capabilities:
- Search and analyze SEC filings (10-K, 10-Q, 8-K)
- Summarize financial documents
- Search financial news articles
- Answer specific questions with citations

When answering:
1. Use the search_filings tool for SEC filing questions
2. Use get_filing_summary for comprehensive document summaries
3. Use search_news for news-related queries
4. Always cite your sources
5. Indicate confidence level in your answers
6. Admit when information is not available

Be precise, factual, and helpful.""",
        )
    
    async def analyze(
        self,
        query: str,
        ticker: str = "",
        chat_history: ChatHistory | None = None,
    ) -> str:
        """
        Analyze SEC filings or news based on query.
        
        Args:
            query: User's question or request
            ticker: Optional ticker to focus search
            chat_history: Optional conversation history
            
        Returns:
            Analysis with citations
        """
        logger.info(f"SEC agent analyzing: {query[:100]}...")
        
        # Create chat history if not provided
        if chat_history is None:
            chat_history = ChatHistory()
        
        # Add user message
        user_message = query
        if ticker:
            user_message = f"[Ticker: {ticker}] {query}"
        
        chat_history.add_message(
            ChatMessageContent(
                role=AuthorRole.USER,
                content=user_message,
            )
        )
        
        try:
            # Get agent response
            async for response in self.agent.invoke(chat_history):
                if response.content:
                    chat_history.add_message(response)
                    return response.content
            
            return "No response generated"
            
        except Exception as e:
            logger.error(f"SEC agent analysis failed: {e}")
            return f"Error analyzing query: {str(e)}"
    
    async def summarize_filing(
        self,
        ticker: str,
        doc_type: str,
        filing_date: str = "",
    ) -> str:
        """
        Get a summary of a specific SEC filing.
        
        Args:
            ticker: Stock ticker
            doc_type: 10-K or 10-Q
            filing_date: Optional specific date
            
        Returns:
            Formatted summary
        """
        query = f"Provide a comprehensive summary of the {doc_type} filing for {ticker}"
        if filing_date:
            query += f" filed on {filing_date}"
        
        return await self.analyze(query, ticker)
