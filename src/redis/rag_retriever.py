"""
RAG Retriever - Retrieval-Augmented Generation Pipeline

Combines document search with LLM generation for Q&A on financial documents.

Pipeline:
1. User asks question
2. Retrieve relevant document chunks (vector search)
3. Augment LLM prompt with retrieved context
4. Generate answer with citations
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from openai import AsyncAzureOpenAI
from .document_store import DocumentStore

logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    """Result from RAG pipeline."""
    answer: str
    sources: List[Dict[str, Any]]
    query: str
    context_used: str
    confidence: str  # high, medium, low


class RAGRetriever:
    """
    Retrieval-Augmented Generation for financial documents.
    
    Use cases:
    - Q&A on SEC filings (10-K, 10-Q)
    - Earnings transcript analysis
    - News article summarization
    - Research report search
    """
    
    def __init__(
        self,
        document_store: DocumentStore,
        openai_client: AsyncAzureOpenAI,
        deployment_name: str = "gpt-4o",
        max_context_chunks: int = 5,
    ):
        """Initialize RAG retriever."""
        self.document_store = document_store
        self.openai_client = openai_client
        self.deployment_name = deployment_name
        self.max_context_chunks = max_context_chunks
    
    async def ask(
        self,
        question: str,
        ticker: Optional[str] = None,
        doc_type: Optional[str] = None,
        source: Optional[str] = None,
        top_k: int = 5,
    ) -> RAGResult:
        """
        Ask a question about financial documents.
        
        Args:
            question: User's question
            ticker: Optional ticker filter
            doc_type: Optional document type filter (10-K, 10-Q, article, etc.)
            source: Optional source filter (SEC, NewsAPI, etc.)
            top_k: Number of document chunks to retrieve
            
        Returns:
            RAGResult with answer and sources
        """
        logger.info(f"RAG query: {question[:100]}...")
        
        # Build filters
        filters = {}
        if ticker:
            filters["ticker"] = ticker
        if doc_type:
            filters["doc_type"] = doc_type
        if source:
            filters["source"] = source
        
        # Retrieve relevant documents
        documents = await self.document_store.search(
            query=question,
            top_k=top_k,
            filters=filters if filters else None,
        )
        
        if not documents:
            return RAGResult(
                answer="I couldn't find any relevant documents to answer your question. Try rephrasing or check if documents are indexed.",
                sources=[],
                query=question,
                context_used="",
                confidence="low",
            )
        
        # Build context from top documents
        context_chunks = documents[:self.max_context_chunks]
        context_parts = []
        
        for i, doc in enumerate(context_chunks, 1):
            context_parts.append(
                f"[Source {i}] {doc['title']} ({doc['doc_type']}, {doc['filing_date'] or 'N/A'})\n"
                f"{doc['content']}\n"
            )
        
        context = "\n".join(context_parts)
        
        # Generate answer with LLM
        answer, confidence = await self._generate_answer(question, context)
        
        # Format sources
        sources = [
            {
                "title": doc["title"],
                "ticker": doc["ticker"],
                "company": doc["company"],
                "doc_type": doc["doc_type"],
                "filing_date": doc["filing_date"],
                "url": doc["url"],
                "relevance_score": round(1 - float(doc["score"]), 2),  # Convert distance to similarity
                "excerpt": doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
            }
            for doc in context_chunks
        ]
        
        return RAGResult(
            answer=answer,
            sources=sources,
            query=question,
            context_used=context,
            confidence=confidence,
        )
    
    async def _generate_answer(
        self,
        question: str,
        context: str,
    ) -> tuple[str, str]:
        """
        Generate answer using LLM with retrieved context.
        
        Returns:
            (answer, confidence_level)
        """
        system_prompt = """You are a financial analyst assistant with access to SEC filings, earnings transcripts, and news articles.

Your task:
1. Answer the user's question using ONLY the provided context
2. Cite specific sources using [Source N] notation
3. If the context doesn't contain enough information, say so clearly
4. Be precise and factual - avoid speculation
5. Include relevant numbers, dates, and metrics when available

Format your answer:
- Start with a direct answer
- Support with evidence from sources
- End with any caveats or limitations"""

        user_prompt = f"""Question: {question}

Context:
{context}

Please answer the question based on the above context. Cite sources using [Source 1], [Source 2], etc."""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,  # Lower temperature for factual responses
                max_tokens=1000,
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Determine confidence based on response content
            confidence = self._assess_confidence(answer, context)
            
            return answer, confidence
            
        except Exception as e:
            logger.error(f"Failed to generate RAG answer: {e}")
            return f"Error generating answer: {str(e)}", "low"
    
    def _assess_confidence(self, answer: str, context: str) -> str:
        """
        Assess confidence level of the answer.
        
        Heuristics:
        - High: Contains citations, specific numbers/dates
        - Medium: General answer with some context
        - Low: Admits insufficient information or hedges
        """
        answer_lower = answer.lower()
        
        # Low confidence indicators
        low_indicators = [
            "i don't have enough",
            "i couldn't find",
            "not enough information",
            "unclear from the context",
            "cannot determine",
        ]
        
        if any(ind in answer_lower for ind in low_indicators):
            return "low"
        
        # High confidence indicators
        has_citations = "[source" in answer_lower
        has_numbers = any(char.isdigit() for char in answer)
        has_specific_info = len(answer) > 100 and has_citations
        
        if has_specific_info and has_citations and has_numbers:
            return "high"
        
        return "medium"
    
    async def summarize_document(
        self,
        ticker: str,
        doc_type: str,
        filing_date: Optional[str] = None,
    ) -> RAGResult:
        """
        Generate a summary of a specific document.
        
        Args:
            ticker: Stock ticker
            doc_type: Document type (10-K, 10-Q, etc.)
            filing_date: Optional specific filing date
            
        Returns:
            RAGResult with summary and key points
        """
        # Build filters
        filters = {
            "ticker": ticker,
            "doc_type": doc_type,
        }
        if filing_date:
            filters["date_from"] = filing_date
            filters["date_to"] = filing_date
        
        # Retrieve all chunks for the document
        documents = await self.document_store.search(
            query=f"summary of {ticker} {doc_type}",
            top_k=20,  # Get more chunks for full document
            filters=filters,
        )
        
        if not documents:
            return RAGResult(
                answer=f"No {doc_type} found for {ticker}",
                sources=[],
                query=f"Summarize {ticker} {doc_type}",
                context_used="",
                confidence="low",
            )
        
        # Build context
        context_parts = []
        for doc in documents[:10]:  # Limit to top 10 chunks
            context_parts.append(doc["content"])
        
        context = "\n\n".join(context_parts)
        
        # Generate summary
        question = f"Provide a comprehensive summary of the key points from this {doc_type} filing for {ticker}"
        
        system_prompt = """You are a financial analyst summarizing SEC filings and financial documents.

Your task:
1. Provide a structured summary with key sections
2. Highlight financial metrics, risks, and material changes
3. Use bullet points for clarity
4. Focus on information relevant to investors

Format:
- **Key Financial Metrics**: Revenue, earnings, cash flow
- **Business Highlights**: Major developments, initiatives
- **Risks & Challenges**: Material risks disclosed
- **Outlook**: Forward-looking statements (if any)"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{question}\n\nContent:\n{context}"},
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            
            summary = response.choices[0].message.content.strip()
            
            return RAGResult(
                answer=summary,
                sources=[{
                    "title": documents[0]["title"],
                    "ticker": ticker,
                    "company": documents[0]["company"],
                    "doc_type": doc_type,
                    "filing_date": documents[0]["filing_date"],
                    "url": documents[0]["url"],
                    "relevance_score": 1.0,
                    "excerpt": "Full document summary",
                }],
                query=question,
                context_used=context,
                confidence="high",
            )
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return RAGResult(
                answer=f"Error generating summary: {str(e)}",
                sources=[],
                query=question,
                context_used="",
                confidence="low",
            )
