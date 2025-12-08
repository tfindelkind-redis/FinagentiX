#!/usr/bin/env python3
"""
Test script for Redis connection and vector operations
"""

import redis
import json
from redis.commands.search.field import VectorField, TextField, TagField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
import numpy as np
import os

# Redis connection details from environment
REDIS_HOST = os.getenv('REDIS_HOST', 'redis-545d8fdb508d4.eastus.redis.azure.net')
REDIS_PORT = int(os.getenv('REDIS_PORT', '10000'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

if not REDIS_PASSWORD:
    raise ValueError("REDIS_PASSWORD environment variable must be set")

def test_connection():
    """Test basic Redis connection"""
    print("Testing Redis connection...")
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            decode_responses=False,
            ssl=True,
            ssl_cert_reqs='required'
        )
        
        # Test ping
        client.ping()
        print("✅ Redis connection successful")
        
        # Test set/get
        client.set('test:key', 'test_value')
        value = client.get('test:key')
        print(f"✅ Set/Get test: {value}")
        
        # Get server info
        info = client.info('server')
        print(f"✅ Redis version: {info.get('redis_version', 'unknown')}")
        
        # Check modules
        modules = client.execute_command('MODULE', 'LIST')
        print(f"✅ Loaded modules: {len(modules)} modules")
        for mod in modules:
            if isinstance(mod, list):
                name = mod[1].decode() if isinstance(mod[1], bytes) else mod[1]
                ver = mod[3] if len(mod) > 3 else 0
                print(f"   - {name}: v{ver}")
        
        return client
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return None

def test_json_operations(client):
    """Test RedisJSON operations"""
    print("\nTesting RedisJSON operations...")
    try:
        test_doc = {
            "name": "Test Document",
            "ticker": "TEST",
            "value": 123.45,
            "tags": ["test", "example"]
        }
        
        client.json().set('test:json:doc1', '$', test_doc)
        retrieved = client.json().get('test:json:doc1')
        print(f"✅ JSON Set/Get test: {retrieved}")
        
        return True
    except Exception as e:
        print(f"❌ JSON operations failed: {str(e)}")
        return False

def test_vector_index(client):
    """Test RediSearch vector index creation"""
    print("\nTesting RediSearch vector index...")
    try:
        index_name = "idx:test_vectors"
        
        # Drop index if exists
        try:
            client.ft(index_name).dropindex()
        except:
            pass
        
        # Create index
        schema = (
            TextField("$.name", as_name="name"),
            TagField("$.ticker", as_name="ticker"),
            VectorField(
                "$.vector",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": 3,
                    "DISTANCE_METRIC": "COSINE",
                },
                as_name="vector"
            ),
        )
        
        definition = IndexDefinition(
            prefix=["testvec:"],
            index_type=IndexType.JSON
        )
        
        client.ft(index_name).create_index(fields=schema, definition=definition)
        print(f"✅ Created vector index: {index_name}")
        
        # Insert test vectors
        for i in range(5):
            vec = np.random.rand(3).tolist()
            doc = {
                "name": f"Document {i}",
                "ticker": "TEST",
                "vector": vec
            }
            client.json().set(f"testvec:doc{i}", '$', doc)
        
        print("✅ Inserted 5 test documents with vectors")
        
        # Search
        query_vector = np.random.rand(3).astype(np.float32).tobytes()
        query = Query("*=>[KNN 3 @vector $vec AS score]").return_fields("name", "score").sort_by("score").dialect(2)
        
        results = client.ft(index_name).search(query, query_params={"vec": query_vector})
        print(f"✅ Vector search returned {len(results.docs)} results")
        for doc in results.docs:
            print(f"   - {doc.name}: score={doc.score}")
        
        # Cleanup
        client.ft(index_name).dropindex(delete_documents=True)
        print("✅ Cleaned up test index")
        
        return True
    except Exception as e:
        print(f"❌ Vector index test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("Redis Connection & Feature Test")
    print("=" * 60)
    
    client = test_connection()
    if not client:
        return
    
    test_json_operations(client)
    test_vector_index(client)
    
    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
