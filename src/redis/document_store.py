"""
Document Store - RAG/Vector Search for Financial Documents

Implements Redis AI Vision document knowledge base for:
- SEC filings (10-K, 10-Q, 8-K)
- Earnings transcripts
- News articles
- Research reports

Features:
- Vector similarity search using RediSearch HNSW
- Document chunking with metadata
- Hybrid search (vector + keyword)
- <10ms retrieval latency
"""

import asyncio
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from openai import AsyncAzureOpenAI

try:
    from redis.commands.search.field import VectorField, TextField, NumericField, TagField
    from redis.commands.search.indexDefinition import IndexDefinition, IndexType
    from redis.commands.search.query import Query
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False
    logging.warning("⚠️ RediSearch not available. Document search will not work.")

from .client import get_redis_client

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Represents a document chunk with metadata."""
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    # Document fields
    title: str = ""
    source: str = ""  # SEC, NewsAPI, etc.
    doc_type: str = ""  # 10-K, 10-Q, 8-K, article, transcript
    ticker: str = ""
    company: str = ""
    filing_date: Optional[str] = None
    url: Optional[str] = None
    
    # Chunk fields
    chunk_index: int = 0
    total_chunks: int = 1
    
    # Timestamps
    created_at: Optional[str] = None


class DocumentStore:
    """
    Document knowledge base with vector search.
    
    Provides RAG (Retrieval-Augmented Generation) capabilities:
    1. Ingest documents (chunk, embed, store)
    2. Vector similarity search
    3. Hybrid search (vector + keyword filters)
    4. Metadata filtering
    """
    
    def __init__(
        self,
        openai_client: AsyncAzureOpenAI,
        index_name: str = "idx:documents",
        embedding_dim: int = 3072,  # text-embedding-3-large
        chunk_size: int = 1000,  # characters per chunk
        chunk_overlap: int = 200,  # overlap between chunks
    ):
        """Initialize document store."""
        self.redis = get_redis_client()
        self.openai_client = openai_client
        self.index_name = index_name
        self.embedding_dim = embedding_dim
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        if SEARCH_AVAILABLE:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                loop.create_task(self._create_index())
            else:
                asyncio.run(self._create_index())
    
    async def _create_index(self) -> None:
        """Create RediSearch index for document vectors."""
        if not SEARCH_AVAILABLE:
            logger.warning("Skipping index creation - RediSearch not available")
            return
        
        try:
            # Check if index exists
            try:
                await asyncio.to_thread(self.redis.ft(self.index_name).info)
                logger.info(f"Document index '{self.index_name}' already exists")
                return
            except Exception:
                pass  # Index doesn't exist, create it
            
            # Define schema
            schema = (
                VectorField(
                    "embedding",
                    "HNSW",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": self.embedding_dim,
                        "DISTANCE_METRIC": "COSINE",
                        "INITIAL_CAP": 10000,
                    }
                ),
                TextField("content", weight=1.0),
                TextField("title", weight=2.0),
                TextField("company", weight=1.5),
                TagField("source"),
                TagField("doc_type"),
                TagField("ticker"),
                TextField("filing_date", sortable=True),
                TextField("url"),
                NumericField("chunk_index"),
                NumericField("total_chunks"),
                TextField("created_at", sortable=True),
            )
            
            # Create index
            definition = IndexDefinition(
                prefix=["doc:"],
                index_type=IndexType.HASH
            )
            
            await asyncio.to_thread(
                self.redis.ft(self.index_name).create_index,
                schema,
                definition=definition
            )
            
            logger.info(f"✅ Created document index '{self.index_name}'")
            
        except Exception as e:
            logger.error(f"Failed to create document index: {e}")
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Document text to chunk
            
        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + self.chunk_size
            
            # Find sentence boundary near chunk end
            if end < text_length:
                # Look for period, newline, or question mark
                for delimiter in ['. ', '.\n', '? ', '!\n']:
                    last_delim = text.rfind(delimiter, start, end)
                    if last_delim != -1:
                        end = last_delim + len(delimiter)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap
        
        return chunks
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Azure OpenAI."""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return [0.0] * self.embedding_dim
    
    async def ingest_document(
        self,
        content: str,
        title: str,
        source: str,
        doc_type: str,
        ticker: str = "",
        company: str = "",
        filing_date: Optional[str] = None,
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Ingest a document: chunk, embed, and store.
        
        Args:
            content: Full document text
            title: Document title
            source: Data source (SEC, NewsAPI, etc.)
            doc_type: Document type (10-K, 10-Q, article, etc.)
            ticker: Stock ticker symbol
            company: Company name
            filing_date: Filing/publication date (YYYY-MM-DD)
            url: Source URL
            metadata: Additional metadata
            
        Returns:
            List of document chunk IDs
        """
        if not SEARCH_AVAILABLE:
            logger.error("Cannot ingest document - RediSearch not available")
            return []
        
        # Generate base document ID
        base_id = hashlib.sha256(
            f"{source}:{doc_type}:{ticker}:{title}".encode()
        ).hexdigest()[:16]
        
        # Chunk the document
        chunks = self._chunk_text(content)
        total_chunks = len(chunks)
        
        logger.info(f"Ingesting document '{title}' ({total_chunks} chunks)")
        
        # Process chunks in parallel
        chunk_ids = []
        tasks = []
        
        for i, chunk_text in enumerate(chunks):
            chunk_id = f"doc:{base_id}:{i}"
            chunk_ids.append(chunk_id)
            
            # Create embedding task
            tasks.append(self._store_chunk(
                chunk_id=chunk_id,
                content=chunk_text,
                title=title,
                source=source,
                doc_type=doc_type,
                ticker=ticker,
                company=company,
                filing_date=filing_date,
                url=url,
                chunk_index=i,
                total_chunks=total_chunks,
                metadata=metadata,
            ))
        
        # Execute all embeddings and stores in parallel
        await asyncio.gather(*tasks)
        
        logger.info(f"✅ Ingested {total_chunks} chunks for '{title}'")
        return chunk_ids
    
    async def _store_chunk(
        self,
        chunk_id: str,
        content: str,
        title: str,
        source: str,
        doc_type: str,
        ticker: str,
        company: str,
        filing_date: Optional[str],
        url: Optional[str],
        chunk_index: int,
        total_chunks: int,
        metadata: Optional[Dict[str, Any]],
    ) -> None:
        """Store a single document chunk with embedding."""
        # Generate embedding
        embedding = await self._generate_embedding(content)
        
        # Prepare document data
        doc_data = {
            "content": content,
            "embedding": self._embedding_to_bytes(embedding),
            "title": title,
            "source": source,
            "doc_type": doc_type,
            "ticker": ticker,
            "company": company,
            "filing_date": filing_date or "",
            "url": url or "",
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        # Add metadata
        if metadata:
            for key, value in metadata.items():
                if key not in doc_data:
                    doc_data[f"meta_{key}"] = str(value)
        
        # Store in Redis
        await asyncio.to_thread(
            self.redis.hset,
            chunk_id,
            mapping=doc_data
        )
    
    def _embedding_to_bytes(self, embedding: List[float]) -> bytes:
        """Convert embedding list to bytes for Redis storage."""
        import struct
        return struct.pack(f'{len(embedding)}f', *embedding)
    
    def _bytes_to_embedding(self, data: bytes) -> List[float]:
        """Convert bytes back to embedding list."""
        import struct
        return list(struct.unpack(f'{len(data)//4}f', data))
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional filters (ticker, source, doc_type, date_range)
            
        Returns:
            List of matching documents with scores
        """
        if not SEARCH_AVAILABLE:
            logger.error("Cannot search - RediSearch not available")
            return []
        
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)
            embedding_bytes = self._embedding_to_bytes(query_embedding)
            
            # Build filter clause
            filter_clause = "*"
            if filters:
                filter_parts = []
                
                if "ticker" in filters:
                    filter_parts.append(f"@ticker:{{{filters['ticker']}}}")
                
                if "source" in filters:
                    filter_parts.append(f"@source:{{{filters['source']}}}")
                
                if "doc_type" in filters:
                    filter_parts.append(f"@doc_type:{{{filters['doc_type']}}}")
                
                if "date_from" in filters:
                    filter_parts.append(f"@filing_date:[{filters['date_from']} +inf]")
                
                if "date_to" in filters:
                    filter_parts.append(f"@filing_date:[-inf {filters['date_to']}]")
                
                if filter_parts:
                    filter_clause = " ".join(filter_parts)
            
            # Create KNN query
            query_obj = (
                Query(f"({filter_clause})=>[KNN {top_k} @embedding $vec AS score]")
                .return_fields("content", "title", "ticker", "company", "source", "doc_type", "filing_date", "url", "chunk_index", "score")
                .sort_by("score")
                .dialect(2)
            )
            
            # Execute search
            results = await asyncio.to_thread(
                self.redis.ft(self.index_name).search,
                query_obj,
                query_params={"vec": embedding_bytes}
            )
            
            # Parse results
            documents = []
            for doc in results.docs:
                documents.append({
                    "content": doc.content,
                    "title": doc.title,
                    "ticker": doc.ticker,
                    "company": doc.company,
                    "source": doc.source,
                    "doc_type": doc.doc_type,
                    "filing_date": doc.filing_date,
                    "url": doc.url,
                    "chunk_index": int(doc.chunk_index),
                    "score": float(doc.score),
                })
            
            logger.info(f"Found {len(documents)} documents for query: {query[:50]}...")
            return documents
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get document store statistics."""
        if not SEARCH_AVAILABLE:
            return {
                "status": "unavailable",
                "error": "RediSearch not available"
            }
        
        try:
            info = await asyncio.to_thread(
                self.redis.ft(self.index_name).info
            )
            
            return {
                "status": "ready",
                "total_documents": int(info.get("num_docs", 0)),
                "index_name": self.index_name,
                "embedding_dim": self.embedding_dim,
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def delete_by_ticker(self, ticker: str) -> int:
        """Delete all documents for a specific ticker."""
        try:
            # Search for all documents with ticker
            query_obj = Query(f"@ticker:{{{ticker}}}").no_content()
            results = await asyncio.to_thread(
                self.redis.ft(self.index_name).search,
                query_obj
            )
            
            # Delete each document
            deleted = 0
            for doc in results.docs:
                await asyncio.to_thread(self.redis.delete, doc.id)
                deleted += 1
            
            logger.info(f"Deleted {deleted} documents for ticker {ticker}")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return 0
