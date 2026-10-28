"""
Auth Cache Service - High Performance Hash Map Engine (O(1) Lookup)
Caches Public API Key validations (X-API-Key: pymai_<token>), tenant permissions,
and company plan_type feature flags in memory with TTL.

Zero-Downtime & Non-Destructive: Operates as an acceleration layer.
"""
import time
from typing import Dict, Any, Optional, Tuple

class AuthHashMapCache:
    """
    In-Memory Hash Map Cache for API Key and Multi-Tenant Auth (O(1))
    """
    _cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    _TTL_SECONDS: int = 300  # 5 minutes TTL

    @classmethod
    def get_api_key_identity(cls, api_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached API Key identity in O(1) time"""
        if not api_key:
            return None
        
        now = time.time()
        if api_key in cls._cache:
            timestamp, data = cls._cache[api_key]
            if now - timestamp < cls._TTL_SECONDS:
                print(f"[AuthHashMapCache HIT O(1)]: {api_key[:12]}...")
                return data
            else:
                del cls._cache[api_key]
        return None

    @classmethod
    def set_api_key_identity(cls, api_key: str, company_data: Dict[str, Any]):
        """Cache API Key identity in O(1) time"""
        if api_key and company_data:
            cls._cache[api_key] = (time.time(), company_data)

    @classmethod
    def invalidate_key(cls, api_key: str):
        """Invalidate a specific key from cache"""
        if api_key in cls._cache:
            del cls._cache[api_key]

    @classmethod
    def clear_all(cls):
        """Clear entire cache"""
        cls._cache.clear()
