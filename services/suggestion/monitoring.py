"""
Monitoring and Observability Service for the Suggestion Engine

Provides comprehensive monitoring, metrics collection, alerting, and observability
for the Tethral Suggestion Engine, including performance tracking, error monitoring,
and business metrics.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager

import aiohttp
from prometheus_client import Counter, Histogram, Gauge, Summary, generate_latest

logger = logging.getLogger(__name__)


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class Alert:
    alert_id: str
    severity: AlertSeverity
    title: str
    description: str
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class PerformanceMetrics:
    request_count: int = 0
    error_count: int = 0
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    active_requests: int = 0
    suggestion_generation_time: float = 0.0
    combination_count: int = 0
    evaluation_time: float = 0.0
    llm_calls: int = 0
    llm_response_time: float = 0.0


class MonitoringService:
    """
    Comprehensive monitoring service for the Suggestion Engine.
    """
    
    def __init__(self):
        # Prometheus metrics
        self.request_counter = Counter(
            'suggestion_requests_total',
            'Total number of suggestion requests',
            ['user_id', 'status', 'device_type']
        )
        
        self.response_time_histogram = Histogram(
            'suggestion_response_time_seconds',
            'Suggestion response time in seconds',
            ['user_id', 'device_type'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
        )
        
        self.active_requests_gauge = Gauge(
            'suggestion_active_requests',
            'Number of active suggestion requests'
        )
        
        self.error_counter = Counter(
            'suggestion_errors_total',
            'Total number of suggestion errors',
            ['error_type', 'component']
        )
        
        self.combination_counter = Counter(
            'suggestion_combinations_generated',
            'Number of combinations generated',
            ['user_id', 'combination_size']
        )
        
        self.evaluation_time_histogram = Histogram(
            'suggestion_evaluation_time_seconds',
            'Combination evaluation time in seconds',
            ['user_id'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
        )
        
        self.llm_calls_counter = Counter(
            'suggestion_llm_calls_total',
            'Total number of LLM calls',
            ['user_id', 'status']
        )
        
        self.llm_response_time_histogram = Histogram(
            'suggestion_llm_response_time_seconds',
            'LLM response time in seconds',
            ['user_id'],
            buckets=[1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )
        
        self.recommendation_confidence_gauge = Gauge(
            'suggestion_recommendation_confidence',
            'Average recommendation confidence',
            ['user_id', 'category']
        )
        
        self.feedback_counter = Counter(
            'suggestion_feedback_total',
            'Total number of feedback events',
            ['user_id', 'feedback_type', 'recommendation_category']
        )
        
        # Business metrics
        self.user_engagement_gauge = Gauge(
            'suggestion_user_engagement',
            'User engagement metrics',
            ['user_id', 'metric_type']
        )
        
        self.suggestion_acceptance_rate = Gauge(
            'suggestion_acceptance_rate',
            'Suggestion acceptance rate',
            ['user_id', 'category']
        )
        
        # Internal state
        self._metrics_buffer: List[MetricPoint] = []
        self._alerts: List[Alert] = []
        self._performance_metrics = PerformanceMetrics()
        self._start_time = datetime.utcnow()
        self._last_cleanup = datetime.utcnow()
        
        # Configuration
        self.metrics_retention_days = 30
        self.alert_retention_days = 90
        self.cleanup_interval_hours = 24
        
    async def start(self):
        """Initialize the monitoring service."""
        logger.info("Monitoring service started")
        
    async def stop(self):
        """Cleanup the monitoring service."""
        logger.info("Monitoring service stopped")
    
    @asynccontextmanager
    async def track_request(self, user_id: str, device_type: str = "unknown"):
        """Context manager to track request performance and errors."""
        start_time = time.time()
        self.active_requests_gauge.inc()
        
        try:
            yield
            # Success
            duration = time.time() - start_time
            self.request_counter.labels(user_id=user_id, status="success", device_type=device_type).inc()
            self.response_time_histogram.labels(user_id=user_id, device_type=device_type).observe(duration)
            
        except Exception as e:
            # Error
            duration = time.time() - start_time
            error_type = type(e).__name__
            self.request_counter.labels(user_id=user_id, status="error", device_type=device_type).inc()
            self.error_counter.labels(error_type=error_type, component="suggestion_engine").inc()
            self.response_time_histogram.labels(user_id=user_id, device_type=device_type).observe(duration)
            raise
        finally:
            self.active_requests_gauge.dec()
    
    def record_combination_generation(self, user_id: str, combination_count: int, combination_size: int):
        """Record combination generation metrics."""
        self.combination_counter.labels(user_id=user_id, combination_size=str(combination_size)).inc(combination_count)
        self._performance_metrics.combination_count += combination_count
    
    def record_evaluation_time(self, user_id: str, evaluation_time: float):
        """Record evaluation time metrics."""
        self.evaluation_time_histogram.labels(user_id=user_id).observe(evaluation_time)
        self._performance_metrics.evaluation_time = evaluation_time
    
    def record_llm_call(self, user_id: str, response_time: float, success: bool = True):
        """Record LLM call metrics."""
        status = "success" if success else "error"
        self.llm_calls_counter.labels(user_id=user_id, status=status).inc()
        self.llm_response_time_histogram.labels(user_id=user_id).observe(response_time)
        self._performance_metrics.llm_calls += 1
        self._performance_metrics.llm_response_time = response_time
    
    def record_recommendation_confidence(self, user_id: str, category: str, confidence: float):
        """Record recommendation confidence metrics."""
        self.recommendation_confidence_gauge.labels(user_id=user_id, category=category).set(confidence)
    
    def record_feedback(self, user_id: str, feedback_type: str, category: str):
        """Record feedback metrics."""
        self.feedback_counter.labels(
            user_id=user_id,
            feedback_type=feedback_type,
            recommendation_category=category
        ).inc()
    
    def record_user_engagement(self, user_id: str, metric_type: str, value: float):
        """Record user engagement metrics."""
        self.user_engagement_gauge.labels(user_id=user_id, metric_type=metric_type).set(value)
    
    def record_suggestion_acceptance(self, user_id: str, category: str, accepted: bool):
        """Record suggestion acceptance metrics."""
        # This would typically be calculated over time, but for now we'll track individual events
        acceptance_rate = 1.0 if accepted else 0.0
        self.suggestion_acceptance_rate.labels(user_id=user_id, category=category).set(acceptance_rate)
    
    async def create_alert(
        self,
        severity: AlertSeverity,
        title: str,
        description: str,
        labels: Optional[Dict[str, str]] = None
    ) -> str:
        """Create a new alert."""
        alert_id = f"alert_{int(time.time())}_{len(self._alerts)}"
        alert = Alert(
            alert_id=alert_id,
            severity=severity,
            title=title,
            description=description,
            timestamp=datetime.utcnow(),
            labels=labels or {}
        )
        
        self._alerts.append(alert)
        logger.warning(f"Alert created: {title} (Severity: {severity.value})")
        
        # Send alert to external systems if configured
        await self._send_alert_notification(alert)
        
        return alert_id
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                logger.info(f"Alert resolved: {alert.title}")
                return True
        return False
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        return self._performance_metrics
    
    def get_alerts(self, severity: Optional[AlertSeverity] = None, resolved: Optional[bool] = None) -> List[Alert]:
        """Get alerts with optional filtering."""
        alerts = self._alerts
        
        if severity is not None:
            alerts = [a for a in alerts if a.severity == severity]
        
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]
        
        return alerts
    
    def get_uptime(self) -> float:
        """Get service uptime in seconds."""
        return (datetime.utcnow() - self._start_time).total_seconds()
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        return {
            "uptime_seconds": self.get_uptime(),
            "performance_metrics": {
                "request_count": self._performance_metrics.request_count,
                "error_count": self._performance_metrics.error_count,
                "avg_response_time": self._performance_metrics.avg_response_time,
                "active_requests": self._performance_metrics.active_requests,
                "combination_count": self._performance_metrics.combination_count,
                "llm_calls": self._performance_metrics.llm_calls
            },
            "alerts": {
                "total": len(self._alerts),
                "active": len([a for a in self._alerts if not a.resolved]),
                "by_severity": {
                    severity.value: len([a for a in self._alerts if a.severity == severity])
                    for severity in AlertSeverity
                }
            }
        }
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus-formatted metrics."""
        return generate_latest()
    
    async def cleanup_old_data(self):
        """Clean up old metrics and alerts."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=self.metrics_retention_days)
            
            # Clean up old metrics
            self._metrics_buffer = [
                metric for metric in self._metrics_buffer
                if metric.timestamp > cutoff_time
            ]
            
            # Clean up old alerts
            alert_cutoff = datetime.utcnow() - timedelta(days=self.alert_retention_days)
            self._alerts = [
                alert for alert in self._alerts
                if alert.timestamp > alert_cutoff or not alert.resolved
            ]
            
            logger.info("Cleaned up old monitoring data")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    async def _send_alert_notification(self, alert: Alert):
        """Send alert notification to external systems."""
        # This would integrate with alerting systems like PagerDuty, Slack, etc.
        # For now, we'll just log the alert
        logger.warning(f"ALERT: {alert.severity.value.upper()} - {alert.title}: {alert.description}")
    
    async def check_health(self) -> Dict[str, Any]:
        """Check the health of the monitoring service."""
        try:
            # Check if we can generate metrics
            metrics = self.get_prometheus_metrics()
            
            # Check alert system
            active_alerts = len([a for a in self._alerts if not a.resolved])
            
            return {
                "status": "healthy",
                "uptime_seconds": self.get_uptime(),
                "active_alerts": active_alerts,
                "metrics_generated": len(metrics) > 0
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }


class PerformanceTracker:
    """
    Utility class for tracking performance of specific operations.
    """
    
    def __init__(self, monitoring_service: MonitoringService):
        self.monitoring_service = monitoring_service
    
    @asynccontextmanager
    async def track_operation(self, operation_name: str, user_id: str = "unknown"):
        """Track the performance of a specific operation."""
        start_time = time.time()
        
        try:
            yield
            duration = time.time() - start_time
            
            # Record custom metric
            metric = MetricPoint(
                name=f"operation_{operation_name}_duration",
                value=duration,
                timestamp=datetime.utcnow(),
                labels={"user_id": user_id, "operation": operation_name},
                metric_type=MetricType.HISTOGRAM
            )
            self.monitoring_service._metrics_buffer.append(metric)
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record error metric
            error_metric = MetricPoint(
                name=f"operation_{operation_name}_error",
                value=1.0,
                timestamp=datetime.utcnow(),
                labels={"user_id": user_id, "operation": operation_name, "error": type(e).__name__},
                metric_type=MetricType.COUNTER
            )
            self.monitoring_service._metrics_buffer.append(error_metric)
            raise


# Global monitoring service instance
_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    """Get the global monitoring service instance."""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service


async def initialize_monitoring():
    """Initialize the global monitoring service."""
    global _monitoring_service
    _monitoring_service = MonitoringService()
    await _monitoring_service.start()


async def cleanup_monitoring():
    """Cleanup the global monitoring service."""
    global _monitoring_service
    if _monitoring_service:
        await _monitoring_service.stop()
