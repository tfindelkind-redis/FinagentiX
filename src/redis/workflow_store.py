"""Persistence layer for workflow outcomes used by the orchestrator."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, Optional

from redis import Redis

from .client import get_redis_client


class WorkflowOutcomeStore:
    """Persists workflow outputs for reuse across orchestrator invocations."""

    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        prefix: str = "workflow:outcome:",
        default_ttl_seconds: int = 900,
    ) -> None:
        self.redis = redis_client or get_redis_client()
        self.prefix = prefix
        self.default_ttl_seconds = default_ttl_seconds

    @staticmethod
    def _serialize_key(key_payload: Dict[str, Any]) -> str:
        normalized = json.dumps(key_payload, sort_keys=True, default=str)
        digest = hashlib.md5(normalized.encode("utf-8")).hexdigest()
        return digest

    def _redis_key(self, workflow: str, key_payload: Dict[str, Any]) -> str:
        key_hash = self._serialize_key(key_payload)
        return f"{self.prefix}{workflow}:{key_hash}"

    @staticmethod
    def _json_default(value: Any) -> str:
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:  # pragma: no cover - defensive
                pass
        return str(value)

    def store(
        self,
        workflow: str,
        key_payload: Dict[str, Any],
        result: Dict[str, Any],
        *,
        synthesis: Optional[Dict[str, Any]] = None,
        final_answer: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Persist workflow outcome with optional synthesis and answer."""
        redis_key = self._redis_key(workflow, key_payload)
        envelope = {
            "workflow": workflow,
            "key": key_payload,
            "result": result,
            "synthesis": synthesis,
            "final_answer": final_answer,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        ttl = ttl_seconds or self.default_ttl_seconds
        payload = json.dumps(envelope, default=self._json_default)
        self.redis.setex(redis_key, ttl, payload)

    def fetch(self, workflow: str, key_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve previously stored workflow result if available."""
        redis_key = self._redis_key(workflow, key_payload)
        raw = self.redis.get(redis_key)
        if not raw:
            return None
        try:
            serialized = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            return json.loads(serialized)
        except Exception:  # pragma: no cover - defensive
            return None

    def invalidate(self, workflow: str, key_payload: Dict[str, Any]) -> None:
        """Remove cached outcome for a specific workflow/key pair."""
        redis_key = self._redis_key(workflow, key_payload)
        self.redis.delete(redis_key)

    def clear(self, workflow: Optional[str] = None) -> int:
        """Clear cached outcomes. Returns number of entries removed."""
        pattern = f"{self.prefix}{workflow}:*" if workflow else f"{self.prefix}*"
        to_delete = list(self.redis.scan_iter(pattern, count=200))
        deleted = 0
        if not to_delete:
            return deleted
        try:
            deleted = self.redis.delete(*to_delete)
        except TypeError:
            for key in to_delete:
                if self.redis.delete(key):
                    deleted += 1
        return deleted
