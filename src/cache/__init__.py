"""
Cache module initialization
"""
from .redis_client import redis_cache, init_cache, close_cache

__all__ = [
    'redis_cache',
    'init_cache',
    'close_cache'
]
