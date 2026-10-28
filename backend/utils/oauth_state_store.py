"""
Google OAuth State Store
Provides a thread-safe, in-memory store for OAuth state tokens
used between the /login and /callback requests.

This replaces Flask session-based state storage which doesn't work
across separate HTTP requests in FastAPI.
"""
import threading
import time
from typing import Optional, Dict, Any


class OAuthStateStore:
    """
    Thread-safe in-memory store for Google OAuth state tokens.
    Entries automatically expire after TTL seconds.
    """
    
    def __init__(self, ttl_seconds: int = 600):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def set(self, state: str, data: Dict[str, Any]) -> None:
        """Store OAuth state data."""
        with self._lock:
            self._store[state] = {
                **data,
                '_expires_at': time.time() + self._ttl
            }

    def get(self, state: str) -> Optional[Dict[str, Any]]:
        """Retrieve OAuth state data if not expired."""
        with self._lock:
            entry = self._store.get(state)
            if entry is None:
                return None
            if time.time() > entry.get('_expires_at', 0):
                del self._store[state]
                return None
            return {k: v for k, v in entry.items() if k != '_expires_at'}

    def pop(self, state: str) -> Optional[Dict[str, Any]]:
        """Retrieve and remove OAuth state data."""
        with self._lock:
            entry = self._store.pop(state, None)
            if entry is None:
                return None
            if time.time() > entry.get('_expires_at', 0):
                return None
            return {k: v for k, v in entry.items() if k != '_expires_at'}

    def cleanup_expired(self) -> None:
        """Remove all expired entries."""
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._store.items() if now > v.get('_expires_at', 0)]
            for k in expired:
                del self._store[k]


# Singleton instance (shared across all requests)
oauth_state_store = OAuthStateStore(ttl_seconds=600)  # 10 minute TTL
