"""
Performance Configuration
Centralized configuration for all performance-related settings.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pydantic import BaseSettings, Field

@dataclass
class DatabasePoolConfig:
    """Database connection pool configuration."""
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 1800
    pool_pre_ping: bool = True
    echo: bool = False

@dataclass
class RedisConfig:
    """Redis configuration for caching and rate limiting."""
    url: str = "redis://localhost:6379/0"
    max_connections: int = 20
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    socket_keepalive: bool = True
    socket_keepalive_options: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_minute: int = 120
    requests_per_second: float = 2.0
    burst_size: int = 10
    window_size: int = 60
    use_redis: bool = True
    redis_url: Optional[str] = None
    per_user_limits: Dict[str, int] = field(default_factory=dict)
    per_org_limits: Dict[str, int] = field(default_factory=dict)

@dataclass
class CacheConfig:
    """Cache configuration."""
    max_size: int = 10000
    max_memory_bytes: int = 100 * 1024 * 1024  # 100MB
    default_ttl: int = 3600  # 1 hour
    compression_threshold: int = 1024  # bytes
    compression_level: int = 6
    eviction_policy: str = "lru"  # lru, lfu, ttl, random
    enable_compression: bool = True
    enable_metrics: bool = True
    cleanup_interval: int = 300  # 5 minutes
    l1_cache_size: int = 5000
    l2_cache_enabled: bool = True

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    half_open_max_calls: int = 3
    enable_metrics: bool = True
    per_service_config: Dict[str, Dict[str, Any]] = field(default_factory=dict)

@dataclass
class ConnectionPoolConfig:
    """Connection pool configuration."""
    max_connections: int = 20
    max_keepalive_connections: int = 10
    keepalive_timeout: int = 30
    connection_timeout: int = 10
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_metrics: bool = True

@dataclass
class LoadBalancerConfig:
    """Load balancer configuration."""
    algorithm: str = "round_robin"  # round_robin, least_connections, weighted
    health_check_interval: int = 30
    health_check_timeout: int = 5
    max_failures: int = 3
    enable_sticky_sessions: bool = False
    session_timeout: int = 3600

@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration."""
    enable_prometheus: bool = True
    enable_tracing: bool = True
    enable_logging: bool = True
    log_level: str = "INFO"
    metrics_interval: int = 60
    health_check_interval: int = 30
    enable_alerting: bool = False
    alert_thresholds: Dict[str, float] = field(default_factory=dict)

@dataclass
class AsyncConfig:
    """Asynchronous processing configuration."""
    max_workers: int = 10
    max_concurrent_tasks: int = 100
    task_timeout: int = 300
    enable_background_tasks: bool = True
    background_task_interval: int = 60
    enable_task_queuing: bool = True
    queue_size: int = 1000

class PerformanceSettings(BaseSettings):
    """Performance settings loaded from environment variables."""
    
    # Database
    database_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=1800, env="DB_POOL_RECYCLE")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    redis_health_check_interval: int = Field(default=30, env="REDIS_HEALTH_CHECK_INTERVAL")
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(default=120, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_requests_per_second: float = Field(default=2.0, env="RATE_LIMIT_PER_SECOND")
    rate_limit_burst_size: int = Field(default=10, env="RATE_LIMIT_BURST_SIZE")
    rate_limit_use_redis: bool = Field(default=True, env="RATE_LIMIT_USE_REDIS")
    
    # Caching
    cache_max_size: int = Field(default=10000, env="CACHE_MAX_SIZE")
    cache_default_ttl: int = Field(default=3600, env="CACHE_DEFAULT_TTL")
    cache_compression_enabled: bool = Field(default=True, env="CACHE_COMPRESSION_ENABLED")
    cache_compression_threshold: int = Field(default=1024, env="CACHE_COMPRESSION_THRESHOLD")
    cache_eviction_policy: str = Field(default="lru", env="CACHE_EVICTION_POLICY")
    
    # Circuit Breakers
    circuit_breaker_failure_threshold: int = Field(default=5, env="CIRCUIT_BREAKER_FAILURE_THRESHOLD")
    circuit_breaker_recovery_timeout: int = Field(default=60, env="CIRCUIT_BREAKER_RECOVERY_TIMEOUT")
    circuit_breaker_half_open_max_calls: int = Field(default=3, env="CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS")
    
    # Connection Pools
    connection_pool_max_connections: int = Field(default=20, env="CONNECTION_POOL_MAX_CONNECTIONS")
    connection_pool_connection_timeout: int = Field(default=10, env="CONNECTION_POOL_TIMEOUT")
    connection_pool_retry_attempts: int = Field(default=3, env="CONNECTION_POOL_RETRY_ATTEMPTS")
    
    # Async Processing
    async_max_workers: int = Field(default=10, env="ASYNC_MAX_WORKERS")
    async_max_concurrent_tasks: int = Field(default=100, env="ASYNC_MAX_CONCURRENT_TASKS")
    async_task_timeout: int = Field(default=300, env="ASYNC_TASK_TIMEOUT")
    
    # Monitoring
    monitoring_enable_prometheus: bool = Field(default=True, env="MONITORING_ENABLE_PROMETHEUS")
    monitoring_enable_tracing: bool = Field(default=True, env="MONITORING_ENABLE_TRACING")
    monitoring_log_level: str = Field(default="INFO", env="MONITORING_LOG_LEVEL")
    monitoring_metrics_interval: int = Field(default=60, env="MONITORING_METRICS_INTERVAL")
    
    # Load Testing
    load_test_enabled: bool = Field(default=False, env="LOAD_TEST_ENABLED")
    load_test_vus: int = Field(default=50, env="LOAD_TEST_VUS")
    load_test_duration: str = Field(default="10m", env="LOAD_TEST_DURATION")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

def get_database_pool_config() -> DatabasePoolConfig:
    """Get database pool configuration from environment."""
    settings = PerformanceSettings()
    return DatabasePoolConfig(
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_recycle=settings.database_pool_recycle,
        pool_pre_ping=True,
        echo=False
    )

def get_redis_config() -> RedisConfig:
    """Get Redis configuration from environment."""
    settings = PerformanceSettings()
    return RedisConfig(
        url=settings.redis_url,
        max_connections=settings.redis_max_connections,
        retry_on_timeout=True,
        health_check_interval=settings.redis_health_check_interval,
        socket_keepalive=True,
        socket_keepalive_options={}
    )

def get_rate_limit_config() -> RateLimitConfig:
    """Get rate limiting configuration from environment."""
    settings = PerformanceSettings()
    return RateLimitConfig(
        requests_per_minute=settings.rate_limit_requests_per_minute,
        requests_per_second=settings.rate_limit_requests_per_second,
        burst_size=settings.rate_limit_burst_size,
        window_size=60,
        use_redis=settings.rate_limit_use_redis,
        redis_url=settings.redis_url if settings.rate_limit_use_redis else None,
        per_user_limits={},
        per_org_limits={}
    )

def get_cache_config() -> CacheConfig:
    """Get cache configuration from environment."""
    settings = PerformanceSettings()
    return CacheConfig(
        max_size=settings.cache_max_size,
        max_memory_bytes=100 * 1024 * 1024,  # 100MB
        default_ttl=settings.cache_default_ttl,
        compression_threshold=settings.cache_compression_threshold,
        compression_level=6,
        eviction_policy=settings.cache_eviction_policy,
        enable_compression=settings.cache_compression_enabled,
        enable_metrics=True,
        cleanup_interval=300,
        l1_cache_size=settings.cache_max_size // 2,
        l2_cache_enabled=True
    )

def get_circuit_breaker_config() -> CircuitBreakerConfig:
    """Get circuit breaker configuration from environment."""
    settings = PerformanceSettings()
    return CircuitBreakerConfig(
        failure_threshold=settings.circuit_breaker_failure_threshold,
        recovery_timeout=settings.circuit_breaker_recovery_timeout,
        half_open_max_calls=settings.circuit_breaker_half_open_max_calls,
        enable_metrics=True,
        per_service_config={
            "hue": {"failure_threshold": 3, "recovery_timeout": 30},
            "smartthings": {"failure_threshold": 5, "recovery_timeout": 60},
            "tuya": {"failure_threshold": 4, "recovery_timeout": 45},
        }
    )

def get_connection_pool_config() -> ConnectionPoolConfig:
    """Get connection pool configuration from environment."""
    settings = PerformanceSettings()
    return ConnectionPoolConfig(
        max_connections=settings.connection_pool_max_connections,
        max_keepalive_connections=settings.connection_pool_max_connections // 2,
        keepalive_timeout=30,
        connection_timeout=settings.connection_pool_connection_timeout,
        retry_attempts=settings.connection_pool_retry_attempts,
        retry_delay=1.0,
        enable_metrics=True
    )

def get_async_config() -> AsyncConfig:
    """Get async processing configuration from environment."""
    settings = PerformanceSettings()
    return AsyncConfig(
        max_workers=settings.async_max_workers,
        max_concurrent_tasks=settings.async_max_concurrent_tasks,
        task_timeout=settings.async_task_timeout,
        enable_background_tasks=True,
        background_task_interval=60,
        enable_task_queuing=True,
        queue_size=1000
    )

def get_monitoring_config() -> MonitoringConfig:
    """Get monitoring configuration from environment."""
    settings = PerformanceSettings()
    return MonitoringConfig(
        enable_prometheus=settings.monitoring_enable_prometheus,
        enable_tracing=settings.monitoring_enable_tracing,
        enable_logging=True,
        log_level=settings.monitoring_log_level,
        metrics_interval=settings.monitoring_metrics_interval,
        health_check_interval=30,
        enable_alerting=False,
        alert_thresholds={
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "response_time_p95": 500.0,
            "error_rate": 0.05,
        }
    )

def get_load_balancer_config() -> LoadBalancerConfig:
    """Get load balancer configuration."""
    return LoadBalancerConfig(
        algorithm="round_robin",
        health_check_interval=30,
        health_check_timeout=5,
        max_failures=3,
        enable_sticky_sessions=False,
        session_timeout=3600
    )

# Environment-specific configurations
def get_production_config() -> Dict[str, Any]:
    """Get production-optimized configuration."""
    return {
        "database": {
            "pool_size": 20,
            "max_overflow": 40,
            "pool_timeout": 30,
            "pool_recycle": 1800,
        },
        "redis": {
            "max_connections": 50,
            "health_check_interval": 15,
        },
        "rate_limiting": {
            "requests_per_minute": 300,
            "requests_per_second": 5.0,
            "burst_size": 20,
        },
        "caching": {
            "max_size": 50000,
            "default_ttl": 7200,
            "compression_enabled": True,
        },
        "async": {
            "max_workers": 20,
            "max_concurrent_tasks": 200,
            "task_timeout": 600,
        },
        "monitoring": {
            "enable_alerting": True,
            "metrics_interval": 30,
        }
    }

def get_development_config() -> Dict[str, Any]:
    """Get development-optimized configuration."""
    return {
        "database": {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 1800,
        },
        "redis": {
            "max_connections": 10,
            "health_check_interval": 60,
        },
        "rate_limiting": {
            "requests_per_minute": 60,
            "requests_per_second": 1.0,
            "burst_size": 5,
        },
        "caching": {
            "max_size": 1000,
            "default_ttl": 300,
            "compression_enabled": False,
        },
        "async": {
            "max_workers": 5,
            "max_concurrent_tasks": 50,
            "task_timeout": 300,
        },
        "monitoring": {
            "enable_alerting": False,
            "metrics_interval": 120,
        }
    }

def get_testing_config() -> Dict[str, Any]:
    """Get testing-optimized configuration."""
    return {
        "database": {
            "pool_size": 2,
            "max_overflow": 5,
            "pool_timeout": 10,
            "pool_recycle": 300,
        },
        "redis": {
            "max_connections": 5,
            "health_check_interval": 120,
        },
        "rate_limiting": {
            "requests_per_minute": 1000,
            "requests_per_second": 10.0,
            "burst_size": 50,
        },
        "caching": {
            "max_size": 100,
            "default_ttl": 60,
            "compression_enabled": False,
        },
        "async": {
            "max_workers": 2,
            "max_concurrent_tasks": 20,
            "task_timeout": 60,
        },
        "monitoring": {
            "enable_alerting": False,
            "metrics_interval": 300,
        }
    }

# Global settings instance
performance_settings = PerformanceSettings()
