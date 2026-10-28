import os
import json
import logging
import time
from config import Config

logger = logging.getLogger(__name__)

class CacheService:
    _local_cache = {}  # Local memory fallback (process RAM)
    _redis_client = None
    _redis_failed = False

    @classmethod
    def get_redis(cls):
        """Get or initialize the Redis client connection."""
        if cls._redis_failed:
            return None
            
        if cls._redis_client is None:
            try:
                import redis
                # Retrieve Redis connection details from Celery Config
                redis_url = os.getenv('CELERY_BROKER_URL') or getattr(Config, 'CELERY_BROKER_URL', 'redis://localhost:6380/0')
                cls._redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
                cls._redis_client.ping()
                logger.info("CacheService connected to Redis successfully.")
            except Exception as e:
                logger.warning(f"CacheService failed to connect to Redis: {e}. Falling back to local process RAM.")
                cls._redis_failed = True
                cls._redis_client = None
        return cls._redis_client

    @classmethod
    def get(cls, key: str):
        """Retrieve a value from the cache (Redis with memory fallback)."""
        redis_client = cls.get_redis()
        if redis_client:
            try:
                val = redis_client.get(key)
                if val:
                    return json.loads(val)
                return None
            except Exception as e:
                logger.warning(f"Error reading from Redis cache: {e}. Attempting local RAM.")
                
        # Local memory fallback
        if key in cls._local_cache:
            val, expiry = cls._local_cache[key]
            if expiry is None or expiry > time.time():
                return val
            else:
                del cls._local_cache[key]
        return None

    @classmethod
    def set(cls, key: str, value, ttl: int = 300, timeout: int = None):
        """Write a value to the cache with a specified TTL (in seconds). Supports ttl or timeout alias."""
        if timeout is not None:
            ttl = timeout
        redis_client = cls.get_redis()
        if redis_client:
            try:
                redis_client.set(key, json.dumps(value), ex=ttl)
                return True
            except Exception as e:
                logger.warning(f"Error writing to Redis cache: {e}. Writing to local RAM instead.")
                
        # Local memory fallback
        expiry = time.time() + ttl if ttl else None
        cls._local_cache[key] = (value, expiry)
        return True

    @classmethod
    def delete(cls, key: str):
        """Invalidate a cache entry by key."""
        redis_client = cls.get_redis()
        if redis_client:
            try:
                redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Error deleting key from Redis cache: {e}")
                
        # Local memory fallback
        cls._local_cache.pop(key, None)
        return True
