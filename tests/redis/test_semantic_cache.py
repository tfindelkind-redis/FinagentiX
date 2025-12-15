import os
import sys

import pytest

# Ensure project root on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import src.redis.semantic_cache as semantic_cache
from src.redis.semantic_cache import SemanticCache


class FakeRedis:
    def __init__(self):
        self.hset_calls = []
        self.expire_calls = []

    def hset(self, key, mapping):
        self.hset_calls.append((key, mapping))

    def expire(self, key, seconds):
        self.expire_calls.append((key, seconds))

    def scan_iter(self, pattern, count=1000):
        return []


@pytest.fixture
def fake_redis(monkeypatch):
    # Avoid RediSearch interactions during tests
    monkeypatch.setattr(semantic_cache, "SEARCH_AVAILABLE", False)
    return FakeRedis()


def test_semantic_cache_set_applies_default_ttl(fake_redis):
    cache = SemanticCache(redis_client=fake_redis)

    cache.set(
        query="What is the price?",
        query_embedding=[0.1, 0.2, 0.3],
        response="Cached answer",
        model="test-model",
        tokens_saved=42,
    )

    assert fake_redis.expire_calls, "Cache entries should set a TTL"
    key, ttl_seconds = fake_redis.expire_calls[0]
    assert ttl_seconds == 300
    assert fake_redis.hset_calls, "Cache entries should be stored in Redis"
