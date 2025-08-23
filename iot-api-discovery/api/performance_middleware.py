"""
Performance Middleware
Enhanced rate limiting, connection pooling, circuit breakers, and performance monitoring.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from collections import defaultdict, deque
import hashlib
import json

from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge, Summary

logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('api_request_duration_seconds', 'API request duration', ['method', 'endpoint'])
ACTIVE_REQUESTS = Gauge('api_active_requests', 'Number of active requests', ['endpoint'])
ERROR_COUNT = Counter('api_errors_total', 'Total API errors', ['method', 'endpoint', 'error_type'])
CACHE_HITS = Counter('cache_hits_total', 'Total cache hits', ['cache_type'])
CACHE_MISSES = Counter('cache_misses_total', 'Total cache misses', ['cache_type'])
CIRCUIT_BREAKER_STATE = Gauge('circuit_breaker_state', 'Circuit breaker state', ['service'])
CONNECTION_POOL_SIZE = Gauge('connection_pool_size', 'Connection pool size', ['pool_type'])

@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_minute: int = 120
    requests_per_second: float = 2.0
    burst_size: int = 10
    window_size: int = 60  # seconds
    use_redis: bool = True
    redis_url: Optional[str] = None

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    expected_exception: type = Exception
    half_open_max_calls: int = 3

@dataclass
class ConnectionPoolConfig:
    """Connection pool configuration."""
    max_connections: int = 20
    max_keepalive_connections: int = 10
    keepalive_timeout: int = 30
    connection_timeout: int = 10
    retry_attempts: int = 3
    retry_delay: float = 1.0

@dataclass
class CacheConfig:
    """Cache configuration."""
    default_ttl: int = 3600  # 1 hour
    max_size: int = 10000
    eviction_policy: str = "lru"  # lru, lfu, ttl
    compression_threshold: int = 1024  # bytes

class TokenBucketRateLimiter:
    """Token bucket rate limiter with Redis support."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self.local_buckets: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'tokens': config.burst_size,
            'last_refill': time.time(),
            'requests': deque(maxlen=config.requests_per_minute)
        })
        
    async def initialize(self):
        """Initialize Redis connection if enabled."""
        if self.config.use_redis and self.config.redis_url:
            try:
                self.redis_client = redis.from_url(
                    self.config.redis_url,
                    decode_responses=False,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                await self.redis_client.ping()
                logger.info("Rate limiter Redis connection established")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis for rate limiting: {e}")
                self.redis_client = None
    
    async def is_allowed(self, key: str) -> bool:
        """Check if request is allowed based on rate limits."""
        if self.redis_client:
            return await self._redis_check(key)
        else:
            return self._local_check(key)
    
    async def _redis_check(self, key: str) -> bool:
        """Check rate limit using Redis."""
        try:
            now = int(time.time())
            window_key = f"rate_limit:{key}:{now // self.config.window_size}"
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            pipe.incr(window_key)
            pipe.expire(window_key, self.config.window_size)
            results = await pipe.execute()
            
            current_count = results[0]
            return current_count <= self.config.requests_per_minute
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fallback to local check
            return self._local_check(key)
    
    def _local_check(self, key: str) -> bool:
        """Check rate limit using local storage."""
        bucket = self.local_buckets[key]
        now = time.time()
        
        # Refill tokens
        time_passed = now - bucket['last_refill']
        tokens_to_add = time_passed * (self.config.requests_per_minute / 60)
        bucket['tokens'] = min(self.config.burst_size, bucket['tokens'] + tokens_to_add)
        bucket['last_refill'] = now
        
        # Check if request is allowed
        if bucket['tokens'] >= 1:
            bucket['tokens'] -= 1
            bucket['requests'].append(now)
            return True
        
        return False

class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.last_failure_time = 0
        self.success_count = 0
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.config.recovery_timeout:
                self.state = "HALF_OPEN"
                self.success_count = 0
            else:
                raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.config.half_open_max_calls:
                self.state = "CLOSED"
                self.success_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == "HALF_OPEN" or (
            self.state == "CLOSED" and self.failure_count >= self.config.failure_threshold
        ):
            self.state = "OPEN"
        
        CIRCUIT_BREAKER_STATE.labels(service=self.name).set(
            1 if self.state == "OPEN" else 0
        )

class ConnectionPool:
    """Generic connection pool for external services."""
    
    def __init__(self, name: str, config: ConnectionPoolConfig):
        self.name = name
        self.config = config
        self.connections: deque = deque(maxlen=config.max_connections)
        self.active_connections = 0
        self.semaphore = asyncio.Semaphore(config.max_connections)
        
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool."""
        async with self.semaphore:
            self.active_connections += 1
            CONNECTION_POOL_SIZE.labels(pool_type=self.name).set(self.active_connections)
            
            try:
                if self.connections:
                    connection = self.connections.popleft()
                else:
                    connection = await self._create_connection()
                
                yield connection
                
                # Return connection to pool if still valid
                if await self._is_connection_valid(connection):
                    self.connections.append(connection)
                else:
                    await self._close_connection(connection)
                    
            finally:
                self.active_connections -= 1
                CONNECTION_POOL_SIZE.labels(pool_type=self.name).set(self.active_connections)
    
    async def _create_connection(self):
        """Create a new connection."""
        # This is a placeholder - implement based on connection type
        return None
    
    async def _is_connection_valid(self, connection) -> bool:
        """Check if connection is still valid."""
        # This is a placeholder - implement based on connection type
        return True
    
    async def _close_connection(self, connection):
        """Close a connection."""
        # This is a placeholder - implement based on connection type
        pass

class PerformanceMiddleware:
    """Main performance middleware class."""
    
    def __init__(self, rate_limit_config: RateLimitConfig):
        self.rate_limiter = TokenBucketRateLimiter(rate_limit_config)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.connection_pools: Dict[str, ConnectionPool] = {}
        self.cache_config = CacheConfig()
        
    async def initialize(self):
        """Initialize all components."""
        await self.rate_limiter.initialize()
        logger.info("Performance middleware initialized")
    
    async def rate_limit_middleware(self, request: Request):
        """Enhanced rate limiting middleware."""
        start_time = time.time()
        
        # Create rate limit key based on client IP and user
        client_ip = request.client.host if request.client else "unknown"
        user_id = request.headers.get("X-User-ID", "anonymous")
        rate_limit_key = f"{client_ip}:{user_id}"
        
        # Check rate limit
        if not await self.rate_limiter.is_allowed(rate_limit_key):
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=429
            ).inc()
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Record metrics
        duration = time.time() - start_time
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        ACTIVE_REQUESTS.labels(endpoint=request.url.path).inc()
        
        # Add timing info to request state
        request.state.start_time = start_time
        request.state.rate_limit_key = rate_limit_key
    
    async def performance_monitoring_middleware(self, request: Request, call_next):
        """Performance monitoring middleware."""
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Record success metrics
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()
            
            return response
            
        except Exception as e:
            # Record error metrics
            error_type = type(e).__name__
            ERROR_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                error_type=error_type
            ).inc()
            
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=500
            ).inc()
            
            raise
        finally:
            # Record timing
            duration = time.time() - start_time
            REQUEST_DURATION.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
            
            ACTIVE_REQUESTS.labels(endpoint=request.url.path).dec()
    
    def get_circuit_breaker(self, service_name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """Get or create a circuit breaker for a service."""
        if service_name not in self.circuit_breakers:
            config = config or CircuitBreakerConfig()
            self.circuit_breakers[service_name] = CircuitBreaker(service_name, config)
        return self.circuit_breakers[service_name]
    
    def get_connection_pool(self, pool_name: str, config: ConnectionPoolConfig = None) -> ConnectionPool:
        """Get or create a connection pool."""
        if pool_name not in self.connection_pools:
            config = config or ConnectionPoolConfig()
            self.connection_pools[pool_name] = ConnectionPool(pool_name, config)
        return self.connection_pools[pool_name]

# Global instance
performance_middleware = PerformanceMiddleware(
    RateLimitConfig(
        requests_per_minute=120,
        requests_per_second=2.0,
        burst_size=10,
        use_redis=True
    )
)

# Dependency for rate limiting
async def enhanced_rate_limiter(request: Request):
    """Enhanced rate limiting dependency."""
    await performance_middleware.rate_limit_middleware(request)

# Dependency for performance monitoring
async def performance_monitor(request: Request, call_next):
    """Performance monitoring dependency."""
    return await performance_middleware.performance_monitoring_middleware(request, call_next)
