"""
LLM Response Caching Module.

Provides caching for LLM API responses to:
1. Reduce API costs
2. Speed up repeated queries
3. Handle rate limiting gracefully

Works with or without Redis:
- With Redis: Persistent cache, shared across workers
- Without Redis: In-memory cache, per-process only
"""
import os
import json
import hashlib
import logging
from typing import Optional, Any
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL_SECONDS = int(os.getenv("LLM_CACHE_TTL", 86400))  # 24 hours default
CACHE_ENABLED = os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL")

# In-memory cache fallback
_memory_cache: dict[str, tuple[Any, datetime]] = {}


class CacheBackend:
    """Abstract cache backend interface."""
    
    def get(self, key: str) -> Optional[str]:
        raise NotImplementedError
    
    def set(self, key: str, value: str, ttl: int = CACHE_TTL_SECONDS) -> bool:
        raise NotImplementedError
    
    def delete(self, key: str) -> bool:
        raise NotImplementedError
    
    def clear(self) -> bool:
        raise NotImplementedError


class MemoryCache(CacheBackend):
    """In-memory cache for development (not shared across workers)."""
    
    def get(self, key: str) -> Optional[str]:
        if key in _memory_cache:
            value, expires_at = _memory_cache[key]
            if datetime.now() < expires_at:
                logger.debug(f"[CACHE] Memory HIT: {key[:32]}...")
                return value
            else:
                # Expired
                del _memory_cache[key]
        logger.debug(f"[CACHE] Memory MISS: {key[:32]}...")
        return None
    
    def set(self, key: str, value: str, ttl: int = CACHE_TTL_SECONDS) -> bool:
        expires_at = datetime.now() + timedelta(seconds=ttl)
        _memory_cache[key] = (value, expires_at)
        logger.debug(f"[CACHE] Memory SET: {key[:32]}... (TTL: {ttl}s)")
        return True
    
    def delete(self, key: str) -> bool:
        if key in _memory_cache:
            del _memory_cache[key]
            return True
        return False
    
    def clear(self) -> bool:
        _memory_cache.clear()
        return True


class RedisCache(CacheBackend):
    """Redis cache for production (shared across workers)."""
    
    def __init__(self, redis_url: str):
        try:
            import redis
            self.client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.client.ping()
            logger.info("[CACHE] Redis connection established")
        except Exception as e:
            logger.warning(f"[CACHE] Redis connection failed: {e}, falling back to memory")
            self.client = None
    
    def get(self, key: str) -> Optional[str]:
        if not self.client:
            return None
        try:
            value = self.client.get(f"llm_cache:{key}")
            if value:
                logger.debug(f"[CACHE] Redis HIT: {key[:32]}...")
            else:
                logger.debug(f"[CACHE] Redis MISS: {key[:32]}...")
            return value
        except Exception as e:
            logger.error(f"[CACHE] Redis GET error: {e}")
            return None
    
    def set(self, key: str, value: str, ttl: int = CACHE_TTL_SECONDS) -> bool:
        if not self.client:
            return False
        try:
            self.client.setex(f"llm_cache:{key}", ttl, value)
            logger.debug(f"[CACHE] Redis SET: {key[:32]}... (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"[CACHE] Redis SET error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        if not self.client:
            return False
        try:
            return bool(self.client.delete(f"llm_cache:{key}"))
        except Exception:
            return False
    
    def clear(self) -> bool:
        if not self.client:
            return False
        try:
            # Delete all llm_cache keys
            keys = self.client.keys("llm_cache:*")
            if keys:
                self.client.delete(*keys)
            return True
        except Exception:
            return False


# Initialize cache backend
def get_cache_backend() -> CacheBackend:
    """Get the appropriate cache backend based on configuration."""
    if REDIS_URL:
        redis_cache = RedisCache(REDIS_URL)
        if redis_cache.client:
            return redis_cache
    return MemoryCache()


# Global cache instance
cache = get_cache_backend()


def generate_cache_key(prompt: str, model: str = "", temperature: float = 0.0) -> str:
    """
    Generate a unique cache key for an LLM request.
    
    Args:
        prompt: The prompt text
        model: Model name
        temperature: Temperature setting
    
    Returns:
        SHA256 hash of the request parameters
    """
    key_data = json.dumps({
        "prompt": prompt,
        "model": model,
        "temperature": temperature
    }, sort_keys=True)
    return hashlib.sha256(key_data.encode()).hexdigest()


def cached_llm_call(ttl: int = CACHE_TTL_SECONDS):
    """
    Decorator to cache LLM API responses.
    
    Usage:
        @cached_llm_call(ttl=3600)
        async def classify_merchant(description: str) -> dict:
            # API call here
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not CACHE_ENABLED:
                return await func(*args, **kwargs)
            
            # Generate cache key from arguments
            cache_key = generate_cache_key(
                prompt=str(args) + str(kwargs),
                model=kwargs.get("model", "default"),
                temperature=kwargs.get("temperature", 0.0)
            )
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result:
                try:
                    return json.loads(cached_result)
                except json.JSONDecodeError:
                    pass
            
            # Call the function
            result = await func(*args, **kwargs)
            
            # Cache the result
            if result is not None:
                try:
                    cache.set(cache_key, json.dumps(result), ttl)
                except Exception as e:
                    logger.warning(f"[CACHE] Failed to cache result: {e}")
            
            return result
        
        return wrapper
    return decorator


# Convenience functions
def cache_get(key: str) -> Optional[Any]:
    """Get a value from cache."""
    value = cache.get(key)
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return None


def cache_set(key: str, value: Any, ttl: int = CACHE_TTL_SECONDS) -> bool:
    """Set a value in cache."""
    try:
        return cache.set(key, json.dumps(value), ttl)
    except Exception:
        return cache.set(key, str(value), ttl)


def cache_delete(key: str) -> bool:
    """Delete a value from cache."""
    return cache.delete(key)


def cache_clear() -> bool:
    """Clear all cached values."""
    return cache.clear()


def get_cache_stats() -> dict:
    """Get cache statistics."""
    return {
        "backend": "redis" if REDIS_URL and isinstance(cache, RedisCache) else "memory",
        "enabled": CACHE_ENABLED,
        "ttl_seconds": CACHE_TTL_SECONDS,
        "memory_cache_size": len(_memory_cache) if isinstance(cache, MemoryCache) else None,
    }
