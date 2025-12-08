"""
Redis Metadata Index with Vector Search
Enables fast semantic search over available datasets
"""

import redis
from redis.commands.search.field import TextField, NumericField, TagField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
import json
import numpy as np
from typing import List, Dict, Any
from datetime import datetime

class DataCatalogIndex:
    """
    Redis-based metadata index with semantic search capabilities
    
    Architecture:
    1. Redis JSON: Store rich metadata documents
    2. RediSearch: Full-text and field-based search
    3. Vector Search: Semantic search using embeddings
    """
    
    def __init__(self, redis_host: str, redis_port: int, redis_password: str):
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            decode_responses=True
        )
        self.index_name = "idx:datasets"
        
    def create_index(self):
        """
        Create RediSearch index with vector search capability
        
        Index Structure:
        - Full-text search on description
        - Tag fields for filtering (ticker, source, asset_class)
        - Numeric fields for range queries (date, size, record_count)
        - Vector field for semantic search
        """
        try:
            # Drop existing index if it exists
            self.redis.ft(self.index_name).dropindex(delete_documents=False)
        except:
            pass
        
        # Define schema
        schema = (
            # Identifiers
            TextField("$.dataset_id", as_name="dataset_id"),
            TextField("$.blob_path", as_name="blob_path"),
            
            # Searchable description
            TextField("$.description", as_name="description", weight=2.0),
            
            # Tag fields (exact match, filterable)
            TagField("$.ticker", as_name="ticker"),
            TagField("$.source", as_name="source"),
            TagField("$.interval", as_name="interval"),
            TagField("$.asset_class", as_name="asset_class"),
            TagField("$.market", as_name="market"),
            
            # Numeric fields (range queries)
            NumericField("$.record_count", as_name="record_count"),
            NumericField("$.file_size_bytes", as_name="file_size_bytes"),
            NumericField("$.start_timestamp", as_name="start_timestamp"),
            NumericField("$.end_timestamp", as_name="end_timestamp"),
            NumericField("$.ingestion_timestamp", as_name="ingestion_timestamp"),
            NumericField("$.completeness_score", as_name="completeness_score"),
            
            # Vector field for semantic search (1536 dimensions for OpenAI embeddings)
            VectorField(
                "$.description_vector",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": 1536,
                    "DISTANCE_METRIC": "COSINE",
                },
                as_name="description_vector"
            )
        )
        
        # Create index
        self.redis.ft(self.index_name).create_index(
            schema,
            definition=IndexDefinition(
                prefix=["dataset:"],
                index_type=IndexType.JSON
            )
        )
        
        print(f"✅ Created index: {self.index_name}")
    
    def index_dataset(self, blob_path: str, metadata: Dict[str, Any], 
                     description_embedding: List[float]):
        """
        Index a dataset in Redis with metadata and vector embedding
        
        Args:
            blob_path: Azure blob path (e.g., "AAPL/1d/2025/12/05.parquet")
            metadata: Rich metadata from ingestion
            description_embedding: Vector embedding of dataset description
        """
        # Create dataset ID
        dataset_id = blob_path.replace("/", "_").replace(".", "_")
        
        # Generate human-readable description
        description = self._generate_description(metadata)
        
        # Create Redis JSON document
        document = {
            "dataset_id": dataset_id,
            "blob_path": blob_path,
            "description": description,
            
            # Identification
            "ticker": metadata.get("ticker", ""),
            "source": metadata.get("source", "yahoo_finance"),
            "interval": metadata.get("interval", "1d"),
            "asset_class": metadata.get("asset_class", "equity"),
            "market": metadata.get("market", "us"),
            
            # Metrics
            "record_count": int(metadata.get("record_count", 0)),
            "file_size_bytes": int(metadata.get("file_size_bytes", 0)),
            "completeness_score": float(metadata.get("completeness_score", 100.0)),
            
            # Timestamps (Unix timestamp for range queries)
            "start_timestamp": self._parse_timestamp(metadata.get("start_date")),
            "end_timestamp": self._parse_timestamp(metadata.get("end_date")),
            "ingestion_timestamp": self._parse_timestamp(metadata.get("ingestion_time")),
            
            # Data quality
            "has_nulls": metadata.get("has_nulls", "false") == "true",
            "quality_checks": metadata.get("quality_checks", {}),
            
            # Schema
            "columns": metadata.get("columns", "").split(","),
            "schema_version": metadata.get("schema_version", "1.0"),
            
            # Vector embedding for semantic search
            "description_vector": description_embedding,
            
            # Full metadata for reference
            "full_metadata": metadata
        }
        
        # Store in Redis
        key = f"dataset:{dataset_id}"
        self.redis.json().set(key, "$", document)
        
        print(f"✅ Indexed: {blob_path}")
        
    def _generate_description(self, metadata: Dict[str, Any]) -> str:
        """Generate human-readable description for semantic search"""
        ticker = metadata.get("ticker", "")
        interval = metadata.get("interval", "")
        start = metadata.get("start_date", "")
        end = metadata.get("end_date", "")
        records = metadata.get("record_count", "")
        
        return (
            f"{ticker} stock price data with {interval} intervals "
            f"from {start} to {end}, containing {records} records. "
            f"Includes OHLCV (open, high, low, close, volume) data "
            f"suitable for financial analysis and agent decision-making."
        )
    
    def _parse_timestamp(self, date_str: str) -> int:
        """Convert date string to Unix timestamp"""
        if not date_str:
            return 0
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return int(dt.timestamp())
        except:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                return int(dt.timestamp())
            except:
                return 0
    
    def search_by_ticker(self, ticker: str) -> List[Dict]:
        """Search datasets by ticker symbol"""
        query = Query(f"@ticker:{{{ticker}}}").return_fields(
            "blob_path", "description", "record_count", "start_timestamp", "end_timestamp"
        )
        results = self.redis.ft(self.index_name).search(query)
        return [self._format_result(doc) for doc in results.docs]
    
    def search_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Search datasets within date range"""
        start_ts = self._parse_timestamp(start_date)
        end_ts = self._parse_timestamp(end_date)
        
        query = Query(
            f"@start_timestamp:[{start_ts} {end_ts}] @end_timestamp:[{start_ts} {end_ts}]"
        ).return_fields("blob_path", "ticker", "description")
        
        results = self.redis.ft(self.index_name).search(query)
        return [self._format_result(doc) for doc in results.docs]
    
    def semantic_search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        """
        Semantic search using vector similarity
        
        Example queries:
        - "Apple stock data from last year"
        - "High frequency intraday trading data"
        - "Technology sector stocks with recent volatility"
        """
        # Convert to byte array
        query_vector = np.array(query_embedding, dtype=np.float32).tobytes()
        
        # KNN search
        query = (
            Query(f"*=>[KNN {top_k} @description_vector $vec AS score]")
            .return_fields("blob_path", "ticker", "description", "score")
            .sort_by("score")
            .dialect(2)
        )
        
        results = self.redis.ft(self.index_name).search(
            query,
            query_params={"vec": query_vector}
        )
        
        return [self._format_result(doc) for doc in results.docs]
    
    def combined_search(self, text_query: str, filters: Dict[str, Any] = None,
                       query_embedding: List[float] = None) -> List[Dict]:
        """
        Hybrid search: Text + Filters + Vector similarity
        
        Example:
            combined_search(
                text_query="price data",
                filters={"ticker": "AAPL", "interval": "1d"},
                query_embedding=[0.1, 0.2, ...]
            )
        """
        # Build query string
        query_parts = []
        
        # Text search
        if text_query:
            query_parts.append(f"@description:({text_query})")
        
        # Filters
        if filters:
            if "ticker" in filters:
                query_parts.append(f"@ticker:{{{filters['ticker']}}}")
            if "interval" in filters:
                query_parts.append(f"@interval:{{{filters['interval']}}}")
            if "asset_class" in filters:
                query_parts.append(f"@asset_class:{{{filters['asset_class']}}}")
        
        # Combine with AND
        query_str = " ".join(query_parts) if query_parts else "*"
        
        # Add vector search if embedding provided
        if query_embedding:
            query_vector = np.array(query_embedding, dtype=np.float32).tobytes()
            query_str += f"=>[KNN 10 @description_vector $vec AS score]"
            
            query = Query(query_str).return_fields(
                "blob_path", "ticker", "description", "record_count", "score"
            ).sort_by("score").dialect(2)
            
            results = self.redis.ft(self.index_name).search(
                query,
                query_params={"vec": query_vector}
            )
        else:
            query = Query(query_str).return_fields(
                "blob_path", "ticker", "description", "record_count"
            )
            results = self.redis.ft(self.index_name).search(query)
        
        return [self._format_result(doc) for doc in results.docs]
    
    def _format_result(self, doc) -> Dict:
        """Format search result"""
        result = {"id": doc.id}
        for key, value in doc.__dict__.items():
            if not key.startswith("_"):
                result[key] = value
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get catalog statistics"""
        info = self.redis.ft(self.index_name).info()
        
        return {
            "total_datasets": info.get("num_docs", 0),
            "index_name": self.index_name,
            "indexing_status": info.get("percent_indexed", 0),
        }


# Example Usage
def example_usage():
    """
    Demonstrate metadata indexing and semantic search
    """
    
    # Initialize catalog
    catalog = DataCatalogIndex(
        redis_host="redis-cluster.eastus.redisenterprise.cache.azure.net",
        redis_port=10000,
        redis_password="your-password"
    )
    
    # Create index
    catalog.create_index()
    
    # Example: Index a dataset
    metadata = {
        "ticker": "AAPL",
        "interval": "1d",
        "start_date": "2020-12-07",
        "end_date": "2025-12-05",
        "record_count": "1256",
        "file_size_bytes": "52428",
        "source": "yahoo_finance",
        "completeness_score": "100.0",
        "asset_class": "equity",
        "market": "us"
    }
    
    # Generate embedding (would use Azure OpenAI in production)
    description_embedding = [0.1] * 1536  # Placeholder
    
    catalog.index_dataset(
        blob_path="AAPL/1d/2025/12/05.parquet",
        metadata=metadata,
        description_embedding=description_embedding
    )
    
    print("\nSEARCH EXAMPLES:")
    print("=" * 60)
    
    # 1. Simple ticker search
    print("\n1. Find all AAPL datasets:")
    results = catalog.search_by_ticker("AAPL")
    for r in results:
        print(f"   - {r['blob_path']}")
    
    # 2. Date range search
    print("\n2. Find datasets from last 6 months:")
    results = catalog.search_by_date_range("2025-06-01", "2025-12-31")
    for r in results:
        print(f"   - {r['ticker']}: {r['blob_path']}")
    
    # 3. Semantic search
    print("\n3. Semantic search: 'Apple stock price history'")
    query_embedding = [0.1] * 1536  # Would be actual query embedding
    results = catalog.semantic_search(query_embedding, top_k=3)
    for r in results:
        print(f"   - {r['ticker']} (similarity: {r.get('score', 'N/A')})")
    
    # 4. Hybrid search
    print("\n4. Hybrid search: text + filters + vector")
    results = catalog.combined_search(
        text_query="price data",
        filters={"ticker": "AAPL", "interval": "1d"},
        query_embedding=query_embedding
    )
    for r in results:
        print(f"   - {r['blob_path']}")


if __name__ == "__main__":
    print("Redis Metadata Index with Vector Search")
    print("=" * 60)
    print()
    print("CAPABILITIES:")
    print("✅ Fast ticker lookup: @ticker:{AAPL}")
    print("✅ Date range queries: @start_timestamp:[ts1 ts2]")
    print("✅ Full-text search: @description:(apple stock)")
    print("✅ Semantic search: KNN vector similarity")
    print("✅ Hybrid queries: Combine text + filters + vectors")
    print()
    print("AGENT USE CASES:")
    print("  • 'What Apple data do we have?' → ticker search")
    print("  • 'Find data from Q4 2024' → date range query")
    print("  • 'Get recent volatility data' → semantic search")
    print("  • 'TSLA intraday data last week' → hybrid search")
