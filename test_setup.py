#!/usr/bin/env python3
"""
Test FinagentiX API setup
"""

import asyncio
from src.redis import get_redis_client, SemanticCache, ContextualMemory, SemanticRouter

def test_redis_connection():
    """Test Redis connection"""
    print("1. Testing Redis connection...")
    try:
        client = get_redis_client()
        result = client.ping()
        print(f"   ✅ Redis connected: {result}")
        return True
    except Exception as e:
        print(f"   ❌ Redis connection failed: {e}")
        return False


def test_semantic_cache():
    """Test semantic cache"""
    print("\n2. Testing Semantic Cache...")
    try:
        cache = SemanticCache()
        
        # Test embedding (dummy for now)
        dummy_embedding = [0.1] * 3072
        
        cache.set(
            query="Test query",
            query_embedding=dummy_embedding,
            response="Test response",
            model="gpt-4o"
        )
        
        result = cache.get(
            query="Test query",
            query_embedding=dummy_embedding
        )
        
        if result and result.get("cache_hit"):
            print(f"   ✅ Semantic cache working")
            return True
        else:
            print(f"   ❌ Cache not working properly")
            return False
            
    except Exception as e:
        print(f"   ❌ Semantic cache error: {e}")
        return False


def test_contextual_memory():
    """Test contextual memory"""
    print("\n3. Testing Contextual Memory...")
    try:
        memory = ContextualMemory()
        
        # Update user preferences
        memory.update_user_preferences("test_user", {
            "risk_tolerance": "moderate"
        })
        
        # Add message
        memory.add_message("test_user", "user", "Test message")
        
        # Get context
        context = memory.get_context("test_user")
        
        if context.get("profile"):
            print(f"   ✅ Contextual memory working")
            return True
        else:
            print(f"   ❌ Memory not working properly")
            return False
            
    except Exception as e:
        print(f"   ❌ Contextual memory error: {e}")
        return False


def test_semantic_router():
    """Test semantic router"""
    print("\n4. Testing Semantic Router...")
    try:
        router = SemanticRouter()
        
        # Test route finding
        route = router.find_route("Should I buy AAPL?")
        
        if route and route.get("workflow"):
            print(f"   ✅ Semantic router working")
            print(f"      Found workflow: {route['workflow']}")
            return True
        else:
            print(f"   ❌ Router not finding routes")
            return False
            
    except Exception as e:
        print(f"   ❌ Semantic router error: {e}")
        return False


async def test_workflows():
    """Test workflows"""
    print("\n5. Testing Workflows...")
    try:
        from src.orchestration.workflows import QuickQuoteWorkflow
        
        workflow = QuickQuoteWorkflow()
        # This will fail without real data, but tests import
        print(f"   ✅ Workflow imports working")
        return True
            
    except Exception as e:
        print(f"   ❌ Workflow error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("FinagentiX Setup Test")
    print("=" * 60)
    
    results = []
    
    # Test components
    results.append(test_redis_connection())
    results.append(test_semantic_cache())
    results.append(test_contextual_memory())
    results.append(test_semantic_router())
    
    # Test async workflow
    results.append(asyncio.run(test_workflows()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed! System is ready.")
        print("\nNext steps:")
        print("  1. Start server: ./start_server.sh")
        print("  2. Test CLI:     python cli.py")
        print("  3. Open docs:    http://localhost:8000/docs")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        print("\nCommon issues:")
        print("  - Make sure Redis credentials in .env are correct")
        print("  - Check Redis is accessible (port 10000, SSL enabled)")


if __name__ == "__main__":
    main()
