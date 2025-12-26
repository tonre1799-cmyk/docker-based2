import redis
import json
import logging
from typing import Optional, Any, Callable
from functools import wraps
from core.logging_setup import setup_logging

logger = setup_logging()

class CacheService:
    """Redis caching layer for expensive queries."""
    
    def __init__(self, redis_host: str = "redis", redis_port: int = 6379, db: int = 0):
        try:
            self.redis = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=db,
                decode_responses=True
            )
            # Test connection
            self.redis.ping()
        except Exception as e:
            logger.error(f"Failed to connect to Redis cache: {e}")
            self.redis = None
    
    def cache(self, key_prefix: str, ttl: int = 300):
        """Decorator for caching function results."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                if self.redis is None:
                    return func(*args, **kwargs)
                
                # Generate cache key from function name and args
                # We exclude 'self' from args if it's a method
                # We also handle Path objects in args
                clean_args = [str(a) if isinstance(a, (Path, tuple, list)) or hasattr(a, '__dict__') else a for a in args]
                cache_key = f"{key_prefix}:{func.__name__}:{hash(str(clean_args) + str(kwargs))}"
                
                try:
                    # Try cache first
                    cached = self.redis.get(cache_key)
                    if cached:
                        logger.debug(f"Cache HIT: {cache_key}")
                        return json.loads(cached)
                except Exception as e:
                    logger.warning(f"Cache read error: {e}")
                
                # Cache miss - call function
                logger.debug(f"Cache MISS: {cache_key}")
                result = func(*args, **kwargs)
                
                try:
                    # Store in cache
                    # Use a custom encoder if needed for datetime/timedelta
                    def json_serial(obj):
                        if isinstance(obj, (datetime, date)):
                            return obj.isoformat()
                        raise TypeError ("Type %s not serializable" % type(obj))

                    self.redis.setex(
                        cache_key,
                        ttl,
                        json.dumps(result)
                    )
                except Exception as e:
                    logger.warning(f"Cache write error: {e}")
                
                return result
            return wrapper
        return decorator
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern."""
        if self.redis is None:
            return
        try:
            for key in self.redis.scan_iter(pattern):
                self.redis.delete(key)
                logger.debug(f"Invalidated cache key: {key}")
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")

# Global cache instance
from datetime import datetime, date
from pathlib import Path

_cache_instance = None

def get_cache() -> CacheService:
    global _cache_instance
    if _cache_instance is None:
        # Load config to get redis host/port
        from core.config_validator import load_config
        config = load_config()
        _cache_instance = CacheService(
            redis_host=os.environ.get("REDIS_HOST", "redis"),
            redis_port=int(os.environ.get("REDIS_PORT", "6379"))
        )
    return _cache_instance
