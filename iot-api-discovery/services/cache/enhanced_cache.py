"""
Enhanced Caching System
Multi-layer caching with compression, intelligent eviction, and performance monitoring.
"""

import asyncio
import time
import logging
import json
import pickle
import gzip
import hashlib
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
from collections import OrderedDict, defaultdict
from enum import Enum
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# Prometheus metrics
CACHE_OPERATIONS = Counter('cache_operations_total', 'Cache operations', ['operation', 'cache_layer', 'status'])
CACHE_SIZE = Gauge('cache_size_bytes', 'Cache size in bytes', ['cache_layer'])
CACHE_ITEMS = Gauge('cache_items_total', 'Number of items in cache', ['cache_layer'])
CACHE_COMPRESSION_RATIO = Histogram('cache_compression_ratio', 'Cache compression ratio', ['cache_layer'])

class CacheLayer(Enum):
    """Cache layer types."""
    L1 = "l1"  # In-memory (fastest)
    L2 = "l2"  # Redis (fast)
    L3 = "l3"  # Database (slowest)

class EvictionPolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    RANDOM = "random"  # Random eviction

@dataclass
class CacheItem:
    """Cache item with metadata."""
    key: str
    value: Any
    created_at: float
    accessed_at: float
    access_count: int = 0
    size_bytes: int = 0
    compressed: bool = False
    ttl: Optional[int] = None
    
    def is_expired(self) -> bool:
        """Check if item is expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def update_access(self):
        """Update access metadata."""
        self.accessed_at = time.time()
        self.access_count += 1

@dataclass
class CacheConfig:
    """Cache configuration."""
    max_size: int = 10000
    max_memory_bytes: int = 100 * 1024 * 1024  # 100MB
    default_ttl: int = 3600  # 1 hour
    compression_threshold: int = 1024  # bytes
    compression_level: int = 6
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    enable_compression: bool = True
    enable_metrics: bool = True
    cleanup_interval: int = 300  # 5 minutes

class LRUCache:
    """LRU cache implementation."""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheItem] = OrderedDict()
        self.size_bytes = 0
        
    def get(self, key: str) -> Optional[CacheItem]:
        """Get item from cache."""
        if key in self.cache:
            item = self.cache[key]
            if item.is_expired():
                del self.cache[key]
                self.size_bytes -= item.size_bytes
                return None
            
            item.update_access()
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return item
        return None
    
    def put(self, key: str, item: CacheItem):
        """Put item in cache."""
        if key in self.cache:
            # Update existing item
            old_item = self.cache[key]
            self.size_bytes -= old_item.size_bytes
        
        # Evict if necessary
        while len(self.cache) >= self.max_size:
            self._evict_lru()
        
        self.cache[key] = item
        self.size_bytes += item.size_bytes
    
    def _evict_lru(self):
        """Evict least recently used item."""
        if self.cache:
            key, item = self.cache.popitem(last=False)
            self.size_bytes -= item.size_bytes
    
    def clear(self):
        """Clear all items."""
        self.cache.clear()
        self.size_bytes = 0

class LFUCache:
    """LFU cache implementation."""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.cache: Dict[str, CacheItem] = {}
        self.frequency: Dict[int, OrderedDict[str, None]] = defaultdict(OrderedDict)
        self.min_frequency = 1
        self.size_bytes = 0
    
    def get(self, key: str) -> Optional[CacheItem]:
        """Get item from cache."""
        if key in self.cache:
            item = self.cache[key]
            if item.is_expired():
                self._remove_item(key)
                return None
            
            item.update_access()
            self._update_frequency(key, item.access_count)
            return item
        return None
    
    def put(self, key: str, item: CacheItem):
        """Put item in cache."""
        if key in self.cache:
            old_item = self.cache[key]
            self.size_bytes -= old_item.size_bytes
            self._remove_item(key)
        
        # Evict if necessary
        while len(self.cache) >= self.max_size:
            self._evict_lfu()
        
        self.cache[key] = item
        self.size_bytes += item.size_bytes
        self._update_frequency(key, item.access_count)
    
    def _update_frequency(self, key: str, frequency: int):
        """Update frequency of an item."""
        if key in self.cache:
            old_freq = self.cache[key].access_count - 1
            if old_freq > 0:
                self.frequency[old_freq].pop(key, None)
                if not self.frequency[old_freq]:
                    del self.frequency[old_freq]
        
        self.frequency[frequency][key] = None
    
    def _remove_item(self, key: str):
        """Remove item from cache."""
        if key in self.cache:
            item = self.cache[key]
            freq = item.access_count
            self.frequency[freq].pop(key, None)
            if not self.frequency[freq]:
                del self.frequency[freq]
            del self.cache[key]
            self.size_bytes -= item.size_bytes
    
    def _evict_lfu(self):
        """Evict least frequently used item."""
        if self.frequency:
            # Find minimum frequency
            min_freq = min(self.frequency.keys())
            # Get first item with minimum frequency
            key = next(iter(self.frequency[min_freq]))
            self._remove_item(key)
    
    def clear(self):
        """Clear all items."""
        self.cache.clear()
        self.frequency.clear()
        self.size_bytes = 0

class EnhancedCache:
    """Enhanced multi-layer caching system."""
    
    def __init__(self, config: CacheConfig, redis_url: Optional[str] = None):
        self.config = config
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        
        # Initialize cache layers
        if config.eviction_policy == EvictionPolicy.LRU:
            self.l1_cache = LRUCache(config.max_size)
        elif config.eviction_policy == EvictionPolicy.LFU:
            self.l1_cache = LFUCache(config.max_size)
        else:
            self.l1_cache = LRUCache(config.max_size)  # Default to LRU
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def initialize(self):
        """Initialize the cache system."""
        if self.redis_url:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=False,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                await self.redis_client.ping()
                logger.info("Enhanced cache Redis connection established")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis for caching: {e}")
                self.redis_client = None
        
        # Start cleanup task
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_items())
        
        logger.info("Enhanced cache system initialized")
    
    async def stop(self):
        """Stop the cache system."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Enhanced cache system stopped")
    
    async def get(self, key: str, cache_layer: CacheLayer = CacheLayer.L1) -> Optional[Any]:
        """Get item from cache."""
        try:
            if cache_layer == CacheLayer.L1:
                return await self._get_l1(key)
            elif cache_layer == CacheLayer.L2 and self.redis_client:
                return await self._get_l2(key)
            else:
                return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            CACHE_OPERATIONS.labels(
                operation="get",
                cache_layer=cache_layer.value,
                status="error"
            ).inc()
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, 
                  cache_layer: CacheLayer = CacheLayer.L1) -> bool:
        """Set item in cache."""
        try:
            if cache_layer == CacheLayer.L1:
                return await self._set_l1(key, value, ttl)
            elif cache_layer == CacheLayer.L2 and self.redis_client:
                return await self._set_l2(key, value, ttl)
            else:
                return False
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            CACHE_OPERATIONS.labels(
                operation="set",
                cache_layer=cache_layer.value,
                status="error"
            ).inc()
            return False
    
    async def delete(self, key: str, cache_layer: CacheLayer = CacheLayer.L1) -> bool:
        """Delete item from cache."""
        try:
            if cache_layer == CacheLayer.L1:
                return await self._delete_l1(key)
            elif cache_layer == CacheLayer.L2 and self.redis_client:
                return await self._delete_l2(key)
            else:
                return False
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            CACHE_OPERATIONS.labels(
                operation="delete",
                cache_layer=cache_layer.value,
                status="error"
            ).inc()
            return False
    
    async def _get_l1(self, key: str) -> Optional[Any]:
        """Get from L1 cache (in-memory)."""
        item = self.l1_cache.get(key)
        if item:
            CACHE_OPERATIONS.labels(
                operation="get",
                cache_layer=CacheLayer.L1.value,
                status="hit"
            ).inc()
            return item.value
        else:
            CACHE_OPERATIONS.labels(
                operation="get",
                cache_layer=CacheLayer.L1.value,
                status="miss"
            ).inc()
            return None
    
    async def _set_l1(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set in L1 cache (in-memory)."""
        # Serialize and compress if needed
        serialized_value = self._serialize_value(value)
        compressed_value = self._compress_value(serialized_value) if self.config.enable_compression else serialized_value
        
        item = CacheItem(
            key=key,
            value=compressed_value,
            created_at=time.time(),
            accessed_at=time.time(),
            size_bytes=len(compressed_value),
            compressed=self.config.enable_compression and len(serialized_value) > self.config.compression_threshold,
            ttl=ttl or self.config.default_ttl
        )
        
        self.l1_cache.put(key, item)
        
        # Update metrics
        CACHE_OPERATIONS.labels(
            operation="set",
            cache_layer=CacheLayer.L1.value,
            status="success"
        ).inc()
        
        CACHE_SIZE.labels(cache_layer=CacheLayer.L1.value).set(self.l1_cache.size_bytes)
        CACHE_ITEMS.labels(cache_layer=CacheLayer.L1.value).set(len(self.l1_cache.cache))
        
        return True
    
    async def _delete_l1(self, key: str) -> bool:
        """Delete from L1 cache (in-memory)."""
        if key in self.l1_cache.cache:
            item = self.l1_cache.cache[key]
            del self.l1_cache.cache[key]
            self.l1_cache.size_bytes -= item.size_bytes
            
            CACHE_OPERATIONS.labels(
                operation="delete",
                cache_layer=CacheLayer.L1.value,
                status="success"
            ).inc()
            
            return True
        return False
    
    async def _get_l2(self, key: str) -> Optional[Any]:
        """Get from L2 cache (Redis)."""
        try:
            data = await self.redis_client.get(f"cache:{key}")
            if data:
                # Decompress if needed
                decompressed_data = self._decompress_value(data)
                deserialized_value = self._deserialize_value(decompressed_data)
                
                CACHE_OPERATIONS.labels(
                    operation="get",
                    cache_layer=CacheLayer.L2.value,
                    status="hit"
                ).inc()
                
                return deserialized_value
            else:
                CACHE_OPERATIONS.labels(
                    operation="get",
                    cache_layer=CacheLayer.L2.value,
                    status="miss"
                ).inc()
                return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def _set_l2(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set in L2 cache (Redis)."""
        try:
            # Serialize and compress
            serialized_value = self._serialize_value(value)
            compressed_value = self._compress_value(serialized_value) if self.config.enable_compression else serialized_value
            
            # Set in Redis
            redis_key = f"cache:{key}"
            await self.redis_client.set(redis_key, compressed_value, ex=ttl or self.config.default_ttl)
            
            CACHE_OPERATIONS.labels(
                operation="set",
                cache_layer=CacheLayer.L2.value,
                status="success"
            ).inc()
            
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def _delete_l2(self, key: str) -> bool:
        """Delete from L2 cache (Redis)."""
        try:
            redis_key = f"cache:{key}"
            result = await self.redis_client.delete(redis_key)
            
            CACHE_OPERATIONS.labels(
                operation="delete",
                cache_layer=CacheLayer.L2.value,
                status="success" if result else "not_found"
            ).inc()
            
            return bool(result)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value to bytes."""
        try:
            return pickle.dumps(value)
        except Exception:
            # Fallback to JSON for simple types
            return json.dumps(value).encode('utf-8')
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from bytes."""
        try:
            return pickle.loads(data)
        except Exception:
            # Fallback to JSON
            return json.loads(data.decode('utf-8'))
    
    def _compress_value(self, data: bytes) -> bytes:
        """Compress data if it meets threshold."""
        if len(data) > self.config.compression_threshold:
            compressed = gzip.compress(data, compresslevel=self.config.compression_level)
            ratio = len(compressed) / len(data)
            CACHE_COMPRESSION_RATIO.labels(cache_layer=CacheLayer.L1.value).observe(ratio)
            return compressed
        return data
    
    def _decompress_value(self, data: bytes) -> bytes:
        """Decompress data if it was compressed."""
        try:
            return gzip.decompress(data)
        except Exception:
            # Not compressed, return as-is
            return data
    
    async def _cleanup_expired_items(self):
        """Background task to clean up expired items."""
        while self._running:
            try:
                # Clean up L1 cache
                expired_keys = []
                for key, item in self.l1_cache.cache.items():
                    if item.is_expired():
                        expired_keys.append(key)
                
                for key in expired_keys:
                    await self._delete_l1(key)
                
                if expired_keys:
                    logger.debug(f"Cleaned up {len(expired_keys)} expired items from L1 cache")
                
                await asyncio.sleep(self.config.cleanup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def get_or_set(self, key: str, getter_func: Callable, ttl: Optional[int] = None,
                        cache_layer: CacheLayer = CacheLayer.L1) -> Any:
        """Get from cache or set using getter function."""
        # Try to get from cache first
        cached_value = await self.get(key, cache_layer)
        if cached_value is not None:
            return cached_value
        
        # If not in cache, call getter function
        value = await getter_func()
        
        # Store in cache
        await self.set(key, value, ttl, cache_layer)
        
        return value
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "l1_cache": {
                "items": len(self.l1_cache.cache),
                "size_bytes": self.l1_cache.size_bytes,
                "max_size": self.config.max_size
            },
            "l2_cache": {
                "enabled": self.redis_client is not None,
                "connected": self.redis_client is not None
            },
            "config": {
                "eviction_policy": self.config.eviction_policy.value,
                "compression_enabled": self.config.enable_compression,
                "default_ttl": self.config.default_ttl
            }
        }

# Global enhanced cache instance
enhanced_cache = EnhancedCache(CacheConfig())
