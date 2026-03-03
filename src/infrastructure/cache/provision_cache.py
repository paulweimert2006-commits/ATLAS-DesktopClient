"""
TTL-basierter In-Memory-Cache fuer Provision-Daten.

Thread-safe ueber threading.Lock. Lazy-Eviction bei get().
Explizite Invalidierung ueber Prefix-Match (z.B. nach Import).
"""

import hashlib
import json
import logging
import threading
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Default-TTLs (Sekunden) ──────────────────────────────────────────────
TTL_EMPLOYEES = 180
TTL_MODELS = 180
TTL_MAPPINGS = 180
TTL_COMMISSIONS = 60
TTL_DASHBOARD = 120
TTL_CLEARANCE = 120
TTL_ABRECHNUNGEN = 120
TTL_PERFORMANCE = 120
TTL_FREE_COMMISSIONS = 120
TTL_IMPORT_BATCHES = 60
TTL_CONTRACTS = 120


def _make_key(prefix: str, **kwargs) -> str:
    """Erzeugt einen deterministischen Cache-Key aus Prefix + sortierten Params."""
    filtered = {k: v for k, v in sorted(kwargs.items()) if v is not None}
    if not filtered:
        return prefix
    raw = json.dumps(filtered, sort_keys=True, default=str)
    suffix = hashlib.md5(raw.encode()).hexdigest()[:10]
    return f"{prefix}:{suffix}"


class _CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: float):
        self.value = value
        self.expires_at = time.monotonic() + ttl


class ProvisionCache:
    """Singleton-faehiger, thread-safe In-Memory-Cache."""

    _instance: Optional["ProvisionCache"] = None
    _init_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "ProvisionCache":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                del self._store[key]
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl: float = 120) -> None:
        with self._lock:
            self._store[key] = _CacheEntry(value, ttl)

    def invalidate(self, key_prefix: str) -> int:
        """Loescht alle Eintraege deren Key mit *key_prefix* beginnt.

        Gibt die Anzahl entfernter Eintraege zurueck.
        """
        with self._lock:
            to_delete = [k for k in self._store if k.startswith(key_prefix)]
            for k in to_delete:
                del self._store[k]
        if to_delete:
            logger.debug("Cache invalidiert: prefix=%s, entfernt=%d", key_prefix, len(to_delete))
        return len(to_delete)

    def invalidate_all(self) -> None:
        with self._lock:
            count = len(self._store)
            self._store.clear()
        if count:
            logger.debug("Cache komplett geleert: %d Eintraege entfernt", count)

    def stats(self) -> dict:
        """Diagnose-Info (nicht fuer Produktionslogik gedacht)."""
        now = time.monotonic()
        with self._lock:
            total = len(self._store)
            expired = sum(1 for e in self._store.values() if now > e.expires_at)
        return {"total": total, "expired": expired, "active": total - expired}
