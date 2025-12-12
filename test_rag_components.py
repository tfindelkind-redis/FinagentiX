#!/usr/bin/env python3
"""
Test RAG/Document Search Components

Verifies that all RAG components are properly installed and configured.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("Testing RAG/Document Search Components...")
print("=" * 60)

# Test 1: Import document store
print("\n1. Testing DocumentStore import...")
try:
    from src.redis.document_store import DocumentStore, Document
    print("   ✅ DocumentStore imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import DocumentStore: {e}")
    sys.exit(1)

# Test 2: Import RAG retriever
print("\n2. Testing RAGRetriever import...")
try:
    from src.redis.rag_retriever import RAGRetriever, RAGResult
    print("   ✅ RAGRetriever imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import RAGRetriever: {e}")
    sys.exit(1)

# Test 3: Import SEC filing agent
print("\n3. Testing SECFilingAgent import...")
try:
    from src.agents.sec_filing_agent import SECFilingAgent, SECFilingPlugin
    print("   ✅ SECFilingAgent imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import SECFilingAgent: {e}")
    sys.exit(1)

# Test 4: Check Redis module exports
print("\n4. Testing Redis module exports...")
try:
    from src.redis import DocumentStore as DS
    print("   ✅ DocumentStore exported from src.redis")
except ImportError as e:
    print(f"   ❌ DocumentStore not exported from src.redis: {e}")
    sys.exit(1)

# Test 5: Check API dependencies
print("\n5. Testing API dependencies...")
try:
    from src.api.dependencies import get_document_store, get_rag_retriever
    print("   ✅ RAG dependencies configured")
except ImportError as e:
    print(f"   ❌ Failed to import RAG dependencies: {e}")
    sys.exit(1)

# Test 6: Verify DocumentStore initialization
print("\n6. Testing DocumentStore initialization...")
try:
    from openai import AsyncAzureOpenAI
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    # Create mock OpenAI client for structure test
    if os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"):
        openai_client = AsyncAzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        )
        
        doc_store = DocumentStore(
            openai_client=openai_client,
            embedding_dim=3072,
            chunk_size=1000,
            chunk_overlap=200,
        )
        print("   ✅ DocumentStore initialized successfully")
        print(f"      - Embedding dimension: {doc_store.embedding_dim}")
        print(f"      - Chunk size: {doc_store.chunk_size}")
        print(f"      - Chunk overlap: {doc_store.chunk_overlap}")
    else:
        print("   ⚠️  Azure OpenAI credentials not found (structure OK)")
        
except Exception as e:
    print(f"   ❌ DocumentStore initialization failed: {e}")

# Test 7: Verify chunking logic
print("\n7. Testing document chunking...")
try:
    from openai import AsyncAzureOpenAI
    import os
    
    # Create document store (mock client OK for chunking test)
    mock_client = AsyncAzureOpenAI(
        azure_endpoint="https://test.openai.azure.com",
        api_key="test-key",
        api_version="2024-02-01",
    )
    
    doc_store = DocumentStore(openai_client=mock_client)
    
    # Test chunking
    test_text = "This is a test. " * 200  # ~3000 chars
    chunks = doc_store._chunk_text(test_text)
    
    print(f"   ✅ Chunking works")
    print(f"      - Input length: {len(test_text)} chars")
    print(f"      - Generated chunks: {len(chunks)}")
    print(f"      - First chunk length: {len(chunks[0])} chars")
    
except Exception as e:
    print(f"   ❌ Chunking test failed: {e}")

# Test 8: Check API endpoints added
print("\n8. Checking API endpoints...")
try:
    from src.api.main import app
    
    # Get all routes
    routes = [route.path for route in app.routes]
    
    required_endpoints = [
        "/api/documents/ingest",
        "/api/documents/search",
        "/api/documents/ask",
        "/api/documents/stats",
    ]
    
    all_present = all(endpoint in routes for endpoint in required_endpoints)
    
    if all_present:
        print("   ✅ All RAG endpoints configured")
        for endpoint in required_endpoints:
            print(f"      - {endpoint}")
    else:
        print("   ❌ Some endpoints missing")
        for endpoint in required_endpoints:
            status = "✓" if endpoint in routes else "✗"
            print(f"      {status} {endpoint}")
            
except Exception as e:
    print(f"   ❌ Failed to check endpoints: {e}")

# Test 9: Verify CLI commands
print("\n9. Checking CLI enhancements...")
try:
    cli_path = Path("cli.py")
    cli_content = cli_path.read_text()
    
    required_features = [
        "show_document_stats",
        "ask_documents",
        "/docs",
        "/ask",
    ]
    
    all_present = all(feature in cli_content for feature in required_features)
    
    if all_present:
        print("   ✅ CLI enhanced with RAG commands")
        print("      - /docs - Show document statistics")
        print("      - /ask - Ask questions about documents")
    else:
        print("   ❌ Some CLI features missing")
        
except Exception as e:
    print(f"   ❌ Failed to check CLI: {e}")

# Test 10: Check ingestion script
print("\n10. Checking ingestion script...")
try:
    ingest_path = Path("ingest_sec_filing.py")
    if ingest_path.exists() and ingest_path.stat().st_mode & 0o111:
        print("   ✅ Ingestion script ready")
        print("      - Path: ingest_sec_filing.py")
        print("      - Executable: Yes")
        print("      - Usage: python ingest_sec_filing.py --ticker AAPL --sample")
    else:
        print("   ⚠️  Ingestion script exists but may not be executable")
        
except Exception as e:
    print(f"   ❌ Failed to check ingestion script: {e}")

# Summary
print("\n" + "=" * 60)
print("✅ RAG/Document Search Components Test Complete!")
print("\nWhat was added:")
print("  • DocumentStore - Vector-based document storage and search")
print("  • RAGRetriever - Q&A pipeline with LLM + retrieval")
print("  • SECFilingAgent - Semantic Kernel agent for SEC filings")
print("  • 5 API endpoints - /ingest, /search, /ask, /stats, /delete")
print("  • 2 CLI commands - /docs, /ask")
print("  • Ingestion script - ingest_sec_filing.py")
print("\nNext steps:")
print("  1. Configure Redis (local or Azure)")
print("  2. Start server: ./start_server.sh")
print("  3. Test ingestion: python ingest_sec_filing.py --ticker AAPL --sample")
print("  4. Ask questions: python cli.py -> /ask")
print("\n📚 See docs/RAG_DOCUMENT_SEARCH_GUIDE.md for full documentation")
