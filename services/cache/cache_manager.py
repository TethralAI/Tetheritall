"""
Cache Manager

Manages caching with Redis backend and fallback to memory storage.
"""

import asyncio
import logging
import json
import pickle
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.asyncio import Redis

from .models import CacheEntry, CacheType, ExpirationPolicy

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching with Redis backend and memory fallback."""
    
    def __init__(self, redis_url: Optional[str] = None, config: Dict[str, Any] = None):
        self.config = config or {}
        self.redis_url = redis_url
        self.redis_client: Optional[Redis] = None
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.use_redis = bool(redis_url)
        self.use_memory_fallback = self.config.get("use_memory_fallback", True)
        
        # Cache configuration
        self.default_ttl = self.config.get("default_ttl", 3600)  # 1 hour
        self.max_memory_entries = self.config.get("max_memory_entries", 10000)
        self.cleanup_interval = self.config.get("cleanup_interval", 300)  # 5 minutes
        
        # Background tasks
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "redis_errors": 0,
            "memory_entries": 0,
            "redis_connected": False
        }
        
    async def start(self):
        """Start the cache manager."""
        self._running = True
        
        # Initialize Redis connection
        if self.redis_url:
            await self._initialize_redis()
            
        # Start background cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_entries())
        
        logger.info(f"Cache Manager started (Redis: {self.stats['redis_connected']}, Memory: {self.use_memory_fallback})")
        
    async def stop(self):
        """Stop the cache manager."""
        self._running = False
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
            
        logger.info("Cache Manager stopped")
        
    async def _initialize_redis(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=False,  # We'll handle encoding ourselves
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            self.stats["redis_connected"] = True
            logger.info("Redis connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.stats["redis_connected"] = False
            self.redis_client = None
            
    async def get(self, key: str, cache_type: Optional[CacheType] = None) -> Optional[Any]:
        """Get value from cache."""
        try:
            # Try Redis first
            if self.redis_client and self.stats["redis_connected"]:
                try:
                    data = await self.redis_client.get(key)
                    if data:
                        entry = pickle.loads(data)
                        if isinstance(entry, CacheEntry):
                            if not entry.is_expired():
                                entry.update_access()
                                await self._update_entry_in_redis(key, entry)
                                self.stats["hits"] += 1
                                return entry.value
                            else:
                                # Remove expired entry
                                await self.delete(key)
                                
                except Exception as e:
                    logger.error(f"Redis get error: {e}")
                    self.stats["redis_errors"] += 1
                    
            # Fallback to memory cache
            if self.use_memory_fallback and key in self.memory_cache:
                entry = self.memory_cache[key]
                if not entry.is_expired():
                    entry.update_access()
                    self.stats["hits"] += 1
                    return entry.value
                else:
                    # Remove expired entry
                    del self.memory_cache[key]
                    
            self.stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.stats["misses"] += 1
            return None
            
    async def set(
        self,
        key: str,
        value: Any,
        cache_type: CacheType = CacheType.METADATA,
        ttl_seconds: Optional[int] = None,
        priority: int = 0,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Set value in cache."""
        try:
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                cache_type=cache_type,
                priority=priority,
                tags=tags or [],
                expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds or self.default_ttl)
            )
            
            # Store in Redis
            if self.redis_client and self.stats["redis_connected"]:
                try:
                    serialized_entry = pickle.dumps(entry)
                    await self.redis_client.setex(
                        key,
                        ttl_seconds or self.default_ttl,
                        serialized_entry
                    )
                except Exception as e:
                    logger.error(f"Redis set error: {e}")
                    self.stats["redis_errors"] += 1
                    
            # Store in memory cache as fallback
            if self.use_memory_fallback:
                # Check memory limits
                if len(self.memory_cache) >= self.max_memory_entries:
                    await self._evict_memory_entries()
                    
                self.memory_cache[key] = entry
                
            self.stats["sets"] += 1
            self.stats["memory_entries"] = len(self.memory_cache)
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
            
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            deleted = False
            
            # Delete from Redis
            if self.redis_client and self.stats["redis_connected"]:
                try:
                    result = await self.redis_client.delete(key)
                    deleted = result > 0
                except Exception as e:
                    logger.error(f"Redis delete error: {e}")
                    self.stats["redis_errors"] += 1
                    
            # Delete from memory cache
            if key in self.memory_cache:
                del self.memory_cache[key]
                deleted = True
                
            if deleted:
                self.stats["deletes"] += 1
                self.stats["memory_entries"] = len(self.memory_cache)
                
            return deleted
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
            
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        value = await self.get(key)
        return value is not None
        
    async def clear(self, cache_type: Optional[CacheType] = None, tags: Optional[List[str]] = None) -> int:
        """Clear cache entries by type or tags."""
        try:
            cleared_count = 0
            
            # Clear from Redis
            if self.redis_client and self.stats["redis_connected"]:
                try:
                    if cache_type is None and tags is None:
                        # Clear all
                        await self.redis_client.flushdb()
                        cleared_count += 1  # Approximate
                    else:
                        # Need to scan and filter (expensive operation)
                        # For production, consider using Redis modules or separate indexes
                        pass
                except Exception as e:
                    logger.error(f"Redis clear error: {e}")
                    self.stats["redis_errors"] += 1
                    
            # Clear from memory cache
            if cache_type is None and tags is None:
                cleared_count += len(self.memory_cache)
                self.memory_cache.clear()
            else:
                keys_to_delete = []
                for key, entry in self.memory_cache.items():
                    should_delete = False
                    
                    if cache_type and entry.cache_type == cache_type:
                        should_delete = True
                    elif tags and any(tag in entry.tags for tag in tags):
                        should_delete = True
                        
                    if should_delete:
                        keys_to_delete.append(key)
                        
                for key in keys_to_delete:
                    del self.memory_cache[key]
                    cleared_count += 1
                    
            self.stats["memory_entries"] = len(self.memory_cache)
            return cleared_count
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0
            
    async def get_keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        keys = []
        
        try:
            # Get keys from Redis
            if self.redis_client and self.stats["redis_connected"]:
                try:
                    redis_keys = await self.redis_client.keys(pattern)
                    keys.extend([key.decode() if isinstance(key, bytes) else key for key in redis_keys])
                except Exception as e:
                    logger.error(f"Redis keys error: {e}")
                    self.stats["redis_errors"] += 1
                    
            # Get keys from memory cache
            import fnmatch
            memory_keys = [key for key in self.memory_cache.keys() if fnmatch.fnmatch(key, pattern)]
            keys.extend(memory_keys)
            
            # Remove duplicates
            return list(set(keys))
            
        except Exception as e:
            logger.error(f"Cache get_keys error: {e}")
            return []
            
    async def get_entry(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry with metadata."""
        try:
            # Try Redis first
            if self.redis_client and self.stats["redis_connected"]:
                try:
                    data = await self.redis_client.get(key)
                    if data:
                        entry = pickle.loads(data)
                        if isinstance(entry, CacheEntry) and not entry.is_expired():
                            entry.update_access()
                            await self._update_entry_in_redis(key, entry)
                            return entry
                            
                except Exception as e:
                    logger.error(f"Redis get_entry error: {e}")
                    self.stats["redis_errors"] += 1
                    
            # Fallback to memory cache
            if self.use_memory_fallback and key in self.memory_cache:
                entry = self.memory_cache[key]
                if not entry.is_expired():
                    entry.update_access()
                    return entry
                else:
                    del self.memory_cache[key]
                    
            return None
            
        except Exception as e:
            logger.error(f"Cache get_entry error: {e}")
            return None
            
    async def _update_entry_in_redis(self, key: str, entry: CacheEntry):
        """Update entry in Redis (for access tracking)."""
        try:
            if self.redis_client and self.stats["redis_connected"]:
                serialized_entry = pickle.dumps(entry)
                ttl = await self.redis_client.ttl(key)
                if ttl > 0:
                    await self.redis_client.setex(key, ttl, serialized_entry)
                    
        except Exception as e:
            logger.error(f"Redis update entry error: {e}")
            self.stats["redis_errors"] += 1
            
    async def _evict_memory_entries(self):
        """Evict entries from memory cache using LRU policy."""
        try:
            if len(self.memory_cache) <= self.max_memory_entries:
                return
                
            # Sort by access time (LRU)
            sorted_entries = sorted(
                self.memory_cache.items(),
                key=lambda x: (x[1].priority, x[1].accessed_at),
                reverse=False  # Oldest first
            )
            
            # Remove 20% of entries
            entries_to_remove = len(sorted_entries) // 5
            for i in range(entries_to_remove):
                key, _ = sorted_entries[i]
                del self.memory_cache[key]
                
            logger.info(f"Evicted {entries_to_remove} entries from memory cache")
            
        except Exception as e:
            logger.error(f"Memory eviction error: {e}")
            
    async def _cleanup_expired_entries(self):
        """Clean up expired entries from memory cache."""
        while self._running:
            try:
                current_time = datetime.utcnow()
                expired_keys = []
                
                for key, entry in self.memory_cache.items():
                    if entry.is_expired():
                        expired_keys.append(key)
                        
                for key in expired_keys:
                    del self.memory_cache[key]
                    
                if expired_keys:
                    logger.info(f"Cleaned up {len(expired_keys)} expired entries")
                    
                self.stats["memory_entries"] = len(self.memory_cache)
                
                await asyncio.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
                
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        hit_rate = 0
        if self.stats["hits"] + self.stats["misses"] > 0:
            hit_rate = self.stats["hits"] / (self.stats["hits"] + self.stats["misses"])
            
        return {
            **self.stats,
            "hit_rate": hit_rate,
            "memory_usage_mb": len(str(self.memory_cache)) / (1024 * 1024),  # Approximate
            "redis_url": self.redis_url,
            "use_memory_fallback": self.use_memory_fallback,
            "default_ttl": self.default_ttl,
            "max_memory_entries": self.max_memory_entries,
            "running": self._running
        }
