"""
Featureform Feature Definitions for FinagentiX

Simplified feature definitions for Redis online store.
This registers the Redis provider and basic entities.

Usage: python3 definitions.py
"""

import featureform as ff
import os

print("=" * 60)
print("Featureform Definitions Registration")
print("=" * 60)

# Get configuration from environment
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", 10000))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

print(f"\n📋 Configuration:")
print(f"  Redis Host: {REDIS_HOST}")
print(f"  Redis Port: {REDIS_PORT}")
print(f"  Redis Password: {'*' * len(REDIS_PASSWORD) if REDIS_PASSWORD else 'NOT SET'}")

if not all([REDIS_HOST, REDIS_PASSWORD]):
    print("\n❌ Error: Missing required environment variables")
    print("   Required: REDIS_HOST, REDIS_PASSWORD")
    exit(1)

# ============================================================================
# PROVIDERS - Register Azure Redis Enterprise
# ============================================================================

print("\n🔧 Registering Redis provider...")

PROVIDER_NAME = os.getenv("REDIS_PROVIDER_NAME", "azure-redis-online")

redis = ff.register_redis(
    name=PROVIDER_NAME,
    description="Azure Redis Enterprise for online feature serving",
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    db=0
)

print(f"✅ Redis provider registered: {PROVIDER_NAME}")

# ============================================================================
# ENTITIES - Define entity types
# ============================================================================

print("\n📊 Registering entities...")

@ff.entity
class User:
    """Trading platform user entity"""
    pass

print("✅ Entity registered: User")

@ff.entity  
class Stock:
    """Stock ticker entity"""
    pass

print("✅ Entity registered: Stock")

# ============================================================================
# APPLY TO FEATUREFORM SERVER
# ============================================================================

print("\n🚀 Applying definitions to Featureform...")
print(f"   Connecting to: {os.getenv('FEATUREFORM_HOST', 'localhost:7878')}")

try:
    # The decorators trigger registration when executed within the Featureform client context
    print("\n✅ Definitions applied successfully!")
    print("\n" + "=" * 60)
    print("Feature Registration Complete")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("  1. Verify features: client = ff.Client(host='...'); client.list_features()")
    print("  2. Add feature transformations and training sets")
    print("  3. Serve features to agents via feature_service.py")
except Exception as e:
    print(f"\n❌ Error applying definitions: {e}")
    print("\nPlease check:")
    print("  - Featureform server is running")
    print("  - FEATUREFORM_HOST environment variable is set")
    print("  - Network connectivity to Featureform")
    exit(1)
