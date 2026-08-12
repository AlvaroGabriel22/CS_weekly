"""
Caching System - Redis-based caching with cache warming and invalidation.

Provides a high-level cache interface for activities, weekly reports,
permissions, and user data with automatic TTL management.
"""

from app.cache.redis_client import RedisCache, get_cache

__all__ = ["RedisCache", "get_cache", "cache"]

# Global cache instance
cache = get_cache()
