"""
Redis cache client for user data, settings, and API key blacklist
"""
import json
import logging
from typing import Optional, Any
import redis
from ..config.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis client for caching and session management"""
    
    def __init__(self):
        self.client = None
        self.cache_db = None
        self._initialized = False
    
    def initialize(self):
        """Initialize Redis connection"""
        if self._initialized:
            return
        
        try:
            # Common arguments for all connections
            common_kwargs = {
                "decode_responses": True,
                "socket_connect_timeout": 10,
                "socket_timeout": 10
            }
            
            # Only add SSL arguments if the URL scheme is rediss://
            if settings.REDIS_URL.startswith("rediss://"):
                common_kwargs["ssl_cert_reqs"] = "none"
            
            # Main Redis client (for Celery)
            self.client = redis.from_url(settings.REDIS_URL, **common_kwargs)
            
            # Cache database
            cache_kwargs = common_kwargs.copy()
            cache_kwargs["db"] = settings.REDIS_CACHE_DB
            self.cache_db = redis.from_url(settings.REDIS_URL, **cache_kwargs)
            
            # Test connection
            try:
                self.client.ping()
                self.cache_db.ping()
            except redis.exceptions.ResponseError as re:
                if "DB index is out of range" in str(re):
                    logger.warning(f"DB {settings.REDIS_CACHE_DB} not available. Falling back to DB 0.")
                    self.cache_db = self.client
                else:
                    raise
            except Exception as e:
                # If connecting with SSL fails, try without
                if settings.REDIS_URL.startswith("rediss://"):
                     logger.warning(f"SSL ping failed ({e}), retrying without SSL...")
                     plain_url = settings.REDIS_URL.replace("rediss://", "redis://")
                     self.client = redis.from_url(plain_url, decode_responses=True)
                     self.cache_db = redis.from_url(plain_url, db=settings.REDIS_CACHE_DB, decode_responses=True)
                     self.client.ping()
                else:
                    raise
            
            self._initialized = True
            logger.info("Redis cache initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            # Don't raise - allow app to work without cache
    
    # User caching
    def get_user(self, api_key: str) -> Optional[dict]:
        """Get cached user by API key"""
        if not self._initialized:
            return None
        
        try:
            cached = self.cache_db.get(f"user:{api_key}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Error getting cached user: {e}")
        
        return None
    
    def set_user(self, api_key: str, user_data: dict, ttl: int = 300):
        """Cache user data (default 5 minutes)"""
        if not self._initialized:
            return
        
        try:
            self.cache_db.setex(
                f"user:{api_key}",
                ttl,
                json.dumps(user_data)
            )
        except Exception as e:
            logger.error(f"Error caching user: {e}")
    
    def invalidate_user(self, api_key: str):
        """Remove user from cache"""
        if not self._initialized:
            return
        
        try:
            self.cache_db.delete(f"user:{api_key}")
        except Exception as e:
            logger.error(f"Error invalidating user cache: {e}")
    
    # Settings caching
    def get_setting(self, key: str) -> Optional[str]:
        """Get cached setting"""
        if not self._initialized:
            return None
        
        try:
            return self.cache_db.get(f"setting:{key}")
        except Exception as e:
            logger.error(f"Error getting cached setting: {e}")
            return None
    
    def set_setting(self, key: str, value: str, ttl: int = 600):
        """Cache setting (default 10 minutes)"""
        if not self._initialized:
            return
        
        try:
            self.cache_db.setex(f"setting:{key}", ttl, value)
        except Exception as e:
            logger.error(f"Error caching setting: {e}")
    
    def invalidate_setting(self, key: str):
        """Remove setting from cache"""
        if not self._initialized:
            return
        
        try:
            self.cache_db.delete(f"setting:{key}")
        except Exception as e:
            logger.error(f"Error invalidating setting cache: {e}")
    
    # API key blacklist (for instant revocation)
    def blacklist_key(self, api_key: str, ttl: int = 86400):
        """Add API key to blacklist (default 24 hours)"""
        if not self._initialized:
            return False
        
        try:
            self.cache_db.setex(f"blacklist:{api_key}", ttl, "1")
            logger.info(f"API key blacklisted: {api_key[:10]}...")
            return True
        except Exception as e:
            logger.error(f"Error blacklisting key: {e}")
            return False
    
    def is_key_blacklisted(self, api_key: str) -> bool:
        """Check if API key is blacklisted"""
        if not self._initialized:
            return False
        
        try:
            return self.cache_db.exists(f"blacklist:{api_key}") > 0
        except Exception as e:
            logger.error(f"Error checking blacklist: {e}")
            return False
    
    def remove_from_blacklist(self, api_key: str):
        """Remove API key from blacklist"""
        if not self._initialized:
            return
        
        try:
            self.cache_db.delete(f"blacklist:{api_key}")
            logger.info(f"API key removed from blacklist: {api_key[:10]}...")
        except Exception as e:
            logger.error(f"Error removing from blacklist: {e}")
    
    # Rate limiting
    def check_rate_limit(self, user_id: int, limit: int = 100, window: int = 60) -> bool:
        """
        Check if user is within rate limit
        
        Args:
            user_id: User ID
            limit: Maximum requests per window
            window: Time window in seconds
        
        Returns:
            True if within limit, False if exceeded
        """
        if not self._initialized:
            return True  # Allow if Redis unavailable
        
        try:
            key = f"ratelimit:{user_id}"
            current = self.cache_db.get(key)
            
            if current is None:
                # First request in window
                self.cache_db.setex(key, window, "1")
                return True
            
            count = int(current)
            if count >= limit:
                return False
            
            # Increment counter
            self.cache_db.incr(key)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow on error
    
    # Health check
    def health_check(self) -> bool:
        """Check Redis connection health"""
        if not self._initialized:
            return False
        
        try:
            self.client.ping()
            self.cache_db.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# Global Redis cache instance
redis_cache = RedisCache()


def init_cache():
    """Initialize Redis cache (call on app startup)"""
    redis_cache.initialize()


def close_cache():
    """Close Redis connections (call on app shutdown)"""
    if redis_cache.client:
        redis_cache.client.close()
    if redis_cache.cache_db:
        redis_cache.cache_db.close()
    logger.info("Redis cache connections closed")
