"""
Redis Client - High-level caching interface with TTL and serialization.

Provides cache operations for activities, weekly reports, sessions,
and permissions with automatic expiration.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import pytz
import redis

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis-based cache client with TTL management and serialization.

    Features:
    - Key-value caching with TTL
    - JSON serialization for complex types
    - Cache warming strategies
    - Cache invalidation on updates
    - Session storage
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ssl: bool = False,
        default_ttl: int = 3600,
    ):
        """
        Initialize Redis cache client.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            ssl: Use SSL connection
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.default_ttl = default_ttl
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                ssl=ssl,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Redis cache connected: {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.redis_client = None

    def _is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self.redis_client is not None

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self._is_connected():
            return None

        try:
            value = self.redis_client.get(key)
            if value:
                # Try to parse as JSON
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return None
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {str(e)}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (uses default if not specified)

        Returns:
            True if successful, False otherwise
        """
        if not self._is_connected():
            return False

        try:
            ttl = ttl or self.default_ttl

            # Serialize value
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value, default=str)
            else:
                serialized = str(value)

            self.redis_client.setex(key, ttl, serialized)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {str(e)}")
            return False

    def delete(self, *keys: str) -> int:
        """
        Delete one or more keys from cache.

        Args:
            keys: Cache keys to delete

        Returns:
            Number of keys deleted
        """
        if not self._is_connected():
            return 0

        try:
            result = self.redis_client.delete(*keys)
            logger.debug(f"Cache DELETE: {len(keys)} key(s)")
            return result
        except Exception as e:
            logger.error(f"Error deleting cache keys: {str(e)}")
            return 0

    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        if not self._is_connected():
            return False

        try:
            return self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking cache key {key}: {str(e)}")
            return False

    def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment numeric value in cache.

        Args:
            key: Cache key
            amount: Amount to increment

        Returns:
            New value
        """
        if not self._is_connected():
            return 0

        try:
            return self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing cache key {key}: {str(e)}")
            return 0

    def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., "activity:*")

        Returns:
            Number of keys deleted
        """
        if not self._is_connected():
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error clearing cache pattern {pattern}: {str(e)}")
            return 0

    # Domain-specific cache methods

    def get_activity(self, activity_id: str) -> Optional[dict]:
        """
        Get cached activity.

        Args:
            activity_id: Activity ID

        Returns:
            Cached activity or None
        """
        return self.get(f"activity:{activity_id}")

    def set_activity(self, activity_id: str, data: dict, ttl: int = 3600) -> bool:
        """
        Cache activity data.

        Args:
            activity_id: Activity ID
            data: Activity data
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        return self.set(f"activity:{activity_id}", data, ttl)

    def invalidate_activity_cache(self, activity_id: str) -> int:
        """
        Invalidate activity cache.

        Args:
            activity_id: Activity ID

        Returns:
            Number of keys deleted
        """
        return self.delete(f"activity:{activity_id}")

    def get_user_activities(self, user_id: str) -> Optional[list]:
        """
        Get cached user activities list.

        Args:
            user_id: User ID

        Returns:
            Cached activities or None
        """
        return self.get(f"user:{user_id}:activities")

    def set_user_activities(
        self, user_id: str, activities: list, ttl: int = 1800
    ) -> bool:
        """
        Cache user activities list.

        Args:
            user_id: User ID
            activities: List of activities
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        return self.set(f"user:{user_id}:activities", activities, ttl)

    def invalidate_user_activities_cache(self, user_id: str) -> int:
        """
        Invalidate user activities cache.

        Args:
            user_id: User ID

        Returns:
            Number of keys deleted
        """
        return self.delete(f"user:{user_id}:activities")

    def get_weekly_report(self, weekly_id: str) -> Optional[dict]:
        """
        Get cached weekly report.

        Args:
            weekly_id: Weekly report ID

        Returns:
            Cached weekly report or None
        """
        return self.get(f"weekly:{weekly_id}")

    def set_weekly_report(self, weekly_id: str, data: dict, ttl: int = 3600) -> bool:
        """
        Cache weekly report data.

        Args:
            weekly_id: Weekly report ID
            data: Weekly report data
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        return self.set(f"weekly:{weekly_id}", data, ttl)

    def invalidate_weekly_cache(self, weekly_id: str) -> int:
        """
        Invalidate weekly report cache.

        Args:
            weekly_id: Weekly report ID

        Returns:
            Number of keys deleted
        """
        return self.delete(f"weekly:{weekly_id}")

    def get_user_weekly(self, user_id: str) -> Optional[list]:
        """
        Get cached user weekly reports list.

        Args:
            user_id: User ID

        Returns:
            Cached weekly reports or None
        """
        return self.get(f"user:{user_id}:weekly")

    def set_user_weekly(self, user_id: str, reports: list, ttl: int = 1800) -> bool:
        """
        Cache user weekly reports list.

        Args:
            user_id: User ID
            reports: List of weekly reports
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        return self.set(f"user:{user_id}:weekly", reports, ttl)

    def invalidate_user_weekly_cache(self, user_id: str) -> int:
        """
        Invalidate user weekly reports cache.

        Args:
            user_id: User ID

        Returns:
            Number of keys deleted
        """
        return self.delete(f"user:{user_id}:weekly")

    def get_file(self, file_id: str) -> Optional[dict]:
        """
        Get cached file metadata.

        Args:
            file_id: File ID

        Returns:
            Cached file metadata or None
        """
        return self.get(f"file:{file_id}")

    def set_file(self, file_id: str, data: dict, ttl: int = 3600) -> bool:
        """
        Cache file metadata.

        Args:
            file_id: File ID
            data: File metadata
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        return self.set(f"file:{file_id}", data, ttl)

    def invalidate_file_cache(self, file_id: str) -> int:
        """
        Invalidate file cache.

        Args:
            file_id: File ID

        Returns:
            Number of keys deleted
        """
        return self.delete(f"file:{file_id}")

    def get_user_permissions(self, user_id: str) -> Optional[dict]:
        """
        Get cached user permissions.

        Args:
            user_id: User ID

        Returns:
            Cached permissions or None
        """
        return self.get(f"user:{user_id}:permissions")

    def set_user_permissions(self, user_id: str, permissions: dict, ttl: int = 1800) -> bool:
        """
        Cache user permissions.

        Args:
            user_id: User ID
            permissions: User permissions
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        return self.set(f"user:{user_id}:permissions", permissions, ttl)

    def invalidate_user_permissions_cache(self, user_id: str) -> int:
        """
        Invalidate user permissions cache.

        Args:
            user_id: User ID

        Returns:
            Number of keys deleted
        """
        return self.delete(f"user:{user_id}:permissions")

    def invalidate_resource_cache(self, resource_id: str) -> int:
        """
        Invalidate all caches related to a resource.

        Args:
            resource_id: Resource ID

        Returns:
            Number of keys deleted
        """
        # Delete resource itself
        result = self.delete(f"activity:{resource_id}", f"weekly:{resource_id}")
        # Delete related patterns
        result += self.clear_pattern(f"user:*:activities")
        result += self.clear_pattern(f"user:*:weekly")
        return result

    def set_session(self, session_id: str, data: dict, ttl: int = 86400) -> bool:
        """
        Store session data.

        Args:
            session_id: Session ID
            data: Session data
            ttl: Time to live in seconds (default 24 hours)

        Returns:
            True if successful
        """
        return self.set(f"session:{session_id}", data, ttl)

    def get_session(self, session_id: str) -> Optional[dict]:
        """
        Retrieve session data.

        Args:
            session_id: Session ID

        Returns:
            Session data or None
        """
        return self.get(f"session:{session_id}")

    def invalidate_session(self, session_id: str) -> int:
        """
        Invalidate session.

        Args:
            session_id: Session ID

        Returns:
            Number of keys deleted
        """
        return self.delete(f"session:{session_id}")

    def flush_all(self) -> bool:
        """
        Flush all cache (USE WITH CAUTION).

        Returns:
            True if successful
        """
        if not self._is_connected():
            return False

        try:
            self.redis_client.flushdb()
            logger.warning("Cache flushed completely")
            return True
        except Exception as e:
            logger.error(f"Error flushing cache: {str(e)}")
            return False


# Global cache instance
_cache: Optional[RedisCache] = None


def get_cache(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None,
    ssl: bool = False,
    default_ttl: int = 3600,
) -> RedisCache:
    """
    Get or create the global cache instance.

    Args:
        host: Redis host
        port: Redis port
        db: Redis database number
        password: Redis password
        ssl: Use SSL connection
        default_ttl: Default TTL in seconds

    Returns:
        The cache instance
    """
    global _cache

    if _cache is None:
        _cache = RedisCache(
            host=host,
            port=port,
            db=db,
            password=password,
            ssl=ssl,
            default_ttl=default_ttl,
        )

    return _cache
