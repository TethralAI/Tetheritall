"""
Monitoring and Support System

This module provides comprehensive monitoring, health checks, user support,
and diagnostic capabilities for the consumer-ready orchestration platform.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from pathlib import Path

from .models import *

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


class IssueSeverity(Enum):
    """Issue severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SupportTicketStatus(Enum):
    """Support ticket status."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_USER = "waiting_for_user"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class HealthMetric:
    """Health metric data."""
    metric_id: str
    name: str
    value: float
    unit: str
    threshold_min: Optional[float] = None
    threshold_max: Optional[float] = None
    status: HealthStatus = HealthStatus.HEALTHY
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceHealthStatus:
    """Device health status."""
    device_id: str
    name: str
    online: bool = True
    battery_level: Optional[float] = None
    signal_strength: Optional[float] = None
    last_seen: datetime = field(default_factory=datetime.utcnow)
    error_count: int = 0
    firmware_version: Optional[str] = None
    needs_calibration: bool = False
    maintenance_due: Optional[datetime] = None
    health_score: float = 1.0
    issues: List[str] = field(default_factory=list)


@dataclass
class NetworkHealthStatus:
    """Network health status."""
    network_id: str
    name: str
    connection_type: str
    bandwidth_mbps: float = 0.0
    latency_ms: float = 0.0
    packet_loss_percent: float = 0.0
    signal_strength: Optional[float] = None
    uptime_percent: float = 100.0
    last_check: datetime = field(default_factory=datetime.utcnow)
    issues: List[str] = field(default_factory=list)


@dataclass
class SystemIssue:
    """System issue tracking."""
    issue_id: str
    title: str
    description: str
    severity: IssueSeverity
    category: str
    affected_components: List[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    status: str = "open"
    resolution_steps: List[str] = field(default_factory=list)
    user_impact: str = "none"
    auto_resolvable: bool = False


@dataclass
class SupportTicket:
    """User support ticket."""
    ticket_id: str
    user_id: str
    title: str
    description: str
    category: str
    priority: str
    status: SupportTicketStatus = SupportTicketStatus.OPEN
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    attachments: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class DiagnosticReport:
    """System diagnostic report."""
    report_id: str
    user_id: str
    generated_at: datetime = field(default_factory=datetime.utcnow)
    system_health: Dict[str, Any] = field(default_factory=dict)
    device_health: List[DeviceHealthStatus] = field(default_factory=list)
    network_health: NetworkHealthStatus = field(default_factory=lambda: NetworkHealthStatus("", ""))
    issues: List[SystemIssue] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)


class HealthMonitor:
    """Monitors system and device health."""
    
    def __init__(self):
        self.metrics: Dict[str, HealthMetric] = {}
        self.device_health: Dict[str, DeviceHealthStatus] = {}
        self.network_health: Dict[str, NetworkHealthStatus] = {}
        self.issues: List[SystemIssue] = []
        self.monitoring_interval = 60  # seconds
        self._monitoring_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self):
        """Start health monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            return
        
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """Stop health monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while True:
            try:
                await self._collect_health_metrics()
                await self._check_device_health()
                await self._check_network_health()
                await self._detect_issues()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)  # Brief pause before retry
    
    async def _collect_health_metrics(self):
        """Collect system health metrics."""
        # CPU usage
        cpu_usage = await self._get_cpu_usage()
        self.metrics["cpu_usage"] = HealthMetric(
            metric_id="cpu_usage",
            name="CPU Usage",
            value=cpu_usage,
            unit="percent",
            threshold_max=80.0,
            status=HealthStatus.HEALTHY if cpu_usage < 80 else HealthStatus.DEGRADED
        )
        
        # Memory usage
        memory_usage = await self._get_memory_usage()
        self.metrics["memory_usage"] = HealthMetric(
            metric_id="memory_usage",
            name="Memory Usage",
            value=memory_usage,
            unit="percent",
            threshold_max=85.0,
            status=HealthStatus.HEALTHY if memory_usage < 85 else HealthStatus.DEGRADED
        )
        
        # Disk usage
        disk_usage = await self._get_disk_usage()
        self.metrics["disk_usage"] = HealthMetric(
            metric_id="disk_usage",
            name="Disk Usage",
            value=disk_usage,
            unit="percent",
            threshold_max=90.0,
            status=HealthStatus.HEALTHY if disk_usage < 90 else HealthStatus.DEGRADED
        )
        
        # Network latency
        network_latency = await self._get_network_latency()
        self.metrics["network_latency"] = HealthMetric(
            metric_id="network_latency",
            name="Network Latency",
            value=network_latency,
            unit="ms",
            threshold_max=100.0,
            status=HealthStatus.HEALTHY if network_latency < 100 else HealthStatus.DEGRADED
        )
    
    async def _check_device_health(self):
        """Check health of all devices."""
        # Placeholder implementation - in reality this would query actual devices
        for device_id in self.device_health:
            device = self.device_health[device_id]
            
            # Simulate device health checks
            device.online = True  # Simulate online status
            device.last_seen = datetime.utcnow()
            
            # Simulate battery level
            if device.battery_level is not None:
                device.battery_level = max(0, device.battery_level - 0.1)  # Simulate battery drain
            
            # Calculate health score
            device.health_score = self._calculate_device_health_score(device)
    
    async def _check_network_health(self):
        """Check network health."""
        for network_id in self.network_health:
            network = self.network_health[network_id]
            
            # Simulate network health checks
            network.latency_ms = 25.0  # Simulate latency
            network.packet_loss_percent = 0.1  # Simulate packet loss
            network.last_check = datetime.utcnow()
    
    async def _detect_issues(self):
        """Detect system issues."""
        # Check for critical metrics
        for metric_id, metric in self.metrics.items():
            if metric.status == HealthStatus.CRITICAL:
                await self._create_issue(
                    title=f"Critical {metric.name}",
                    description=f"{metric.name} is at critical level: {metric.value}{metric.unit}",
                    severity=IssueSeverity.CRITICAL,
                    category="system_metric",
                    affected_components=[metric_id]
                )
        
        # Check for offline devices
        for device_id, device in self.device_health.items():
            if not device.online:
                await self._create_issue(
                    title=f"Device {device.name} offline",
                    description=f"Device {device.name} has been offline since {device.last_seen}",
                    severity=IssueSeverity.MEDIUM,
                    category="device_offline",
                    affected_components=[device_id]
                )
    
    async def _create_issue(self, title: str, description: str, severity: IssueSeverity,
                           category: str, affected_components: List[str]):
        """Create a new system issue."""
        # Check if issue already exists
        existing_issue = next((issue for issue in self.issues 
                             if issue.title == title and issue.status == "open"), None)
        
        if existing_issue:
            return
        
        issue = SystemIssue(
            issue_id=str(uuid.uuid4()),
            title=title,
            description=description,
            severity=severity,
            category=category,
            affected_components=affected_components,
            auto_resolvable=severity in [IssueSeverity.LOW, IssueSeverity.MEDIUM]
        )
        
        self.issues.append(issue)
        logger.warning(f"New issue detected: {title}")
    
    def _calculate_device_health_score(self, device: DeviceHealthStatus) -> float:
        """Calculate device health score."""
        score = 1.0
        
        # Reduce score for offline devices
        if not device.online:
            score -= 0.5
        
        # Reduce score for low battery
        if device.battery_level is not None and device.battery_level < 0.2:
            score -= 0.2
        
        # Reduce score for errors
        if device.error_count > 0:
            score -= min(0.3, device.error_count * 0.1)
        
        return max(0.0, score)
    
    async def _get_cpu_usage(self) -> float:
        """Get CPU usage percentage."""
        # Placeholder implementation
        import random
        return random.uniform(20.0, 60.0)
    
    async def _get_memory_usage(self) -> float:
        """Get memory usage percentage."""
        # Placeholder implementation
        import random
        return random.uniform(30.0, 70.0)
    
    async def _get_disk_usage(self) -> float:
        """Get disk usage percentage."""
        # Placeholder implementation
        import random
        return random.uniform(40.0, 80.0)
    
    async def _get_network_latency(self) -> float:
        """Get network latency in milliseconds."""
        # Placeholder implementation
        import random
        return random.uniform(10.0, 50.0)
    
    async def get_system_health_summary(self) -> Dict[str, Any]:
        """Get system health summary."""
        total_devices = len(self.device_health)
        online_devices = len([d for d in self.device_health.values() if d.online])
        critical_issues = len([i for i in self.issues if i.severity == IssueSeverity.CRITICAL])
        
        return {
            "overall_status": self._get_overall_status(),
            "total_devices": total_devices,
            "online_devices": online_devices,
            "device_uptime_percent": (online_devices / total_devices * 100) if total_devices > 0 else 100,
            "critical_issues": critical_issues,
            "total_issues": len(self.issues),
            "last_check": datetime.utcnow().isoformat()
        }
    
    def _get_overall_status(self) -> HealthStatus:
        """Get overall system health status."""
        critical_issues = len([i for i in self.issues if i.severity == IssueSeverity.CRITICAL])
        degraded_metrics = len([m for m in self.metrics.values() if m.status == HealthStatus.DEGRADED])
        
        if critical_issues > 0:
            return HealthStatus.CRITICAL
        elif degraded_metrics > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY


class UserSupport:
    """Provides user support and troubleshooting."""
    
    def __init__(self):
        self.support_tickets: Dict[str, SupportTicket] = {}
        self.knowledge_base = KnowledgeBase()
        self.troubleshooter = Troubleshooter()
        self.remote_diagnostics = RemoteDiagnostics()
    
    async def create_support_ticket(self, user_id: str, title: str, description: str,
                                   category: str, priority: str = "medium") -> SupportTicket:
        """Create a new support ticket."""
        ticket = SupportTicket(
            ticket_id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            description=description,
            category=category,
            priority=priority
        )
        
        self.support_tickets[ticket.ticket_id] = ticket
        
        # Try to auto-resolve if possible
        await self._attempt_auto_resolution(ticket)
        
        return ticket
    
    async def update_ticket(self, ticket_id: str, updates: Dict[str, Any]) -> Optional[SupportTicket]:
        """Update a support ticket."""
        if ticket_id not in self.support_tickets:
            return None
        
        ticket = self.support_tickets[ticket_id]
        
        for key, value in updates.items():
            if hasattr(ticket, key):
                setattr(ticket, key, value)
        
        ticket.updated_at = datetime.utcnow()
        return ticket
    
    async def get_ticket(self, ticket_id: str) -> Optional[SupportTicket]:
        """Get a support ticket by ID."""
        return self.support_tickets.get(ticket_id)
    
    async def get_user_tickets(self, user_id: str) -> List[SupportTicket]:
        """Get all tickets for a user."""
        return [ticket for ticket in self.support_tickets.values() if ticket.user_id == user_id]
    
    async def search_knowledge_base(self, query: str) -> List[Dict[str, Any]]:
        """Search the knowledge base for solutions."""
        return await self.knowledge_base.search(query)
    
    async def run_troubleshooter(self, issue_type: str, user_id: str) -> Dict[str, Any]:
        """Run automated troubleshooting."""
        return await self.troubleshooter.run_diagnostic(issue_type, user_id)
    
    async def start_remote_diagnostics(self, user_id: str) -> str:
        """Start remote diagnostics session."""
        return await self.remote_diagnostics.start_session(user_id)
    
    async def _attempt_auto_resolution(self, ticket: SupportTicket):
        """Attempt to auto-resolve a support ticket."""
        # Check if this is a common issue that can be auto-resolved
        common_issues = {
            "device_offline": "Try restarting the device and checking the network connection.",
            "connection_problem": "Check your internet connection and restart the router if needed.",
            "battery_low": "Replace or recharge the device battery.",
            "firmware_update": "The device firmware will be updated automatically."
        }
        
        for issue_type, resolution in common_issues.items():
            if issue_type in ticket.description.lower():
                ticket.resolution = resolution
                ticket.status = SupportTicketStatus.RESOLVED
                ticket.updated_at = datetime.utcnow()
                logger.info(f"Auto-resolved ticket {ticket.ticket_id}")
                break


class KnowledgeBase:
    """Knowledge base for common issues and solutions."""
    
    def __init__(self):
        self.articles = self._load_knowledge_base()
    
    def _load_knowledge_base(self) -> List[Dict[str, Any]]:
        """Load knowledge base articles."""
        return [
            {
                "id": "kb_001",
                "title": "Device Not Responding",
                "content": "If your device is not responding, try these steps: 1. Check if the device is powered on 2. Restart the device 3. Check network connection 4. Contact support if the issue persists",
                "category": "troubleshooting",
                "tags": ["device", "offline", "unresponsive"],
                "views": 1250
            },
            {
                "id": "kb_002",
                "title": "Network Connection Issues",
                "content": "Network connection problems can be resolved by: 1. Checking your internet connection 2. Restarting your router 3. Moving devices closer to the router 4. Checking for interference",
                "category": "network",
                "tags": ["network", "connection", "wifi"],
                "views": 890
            },
            {
                "id": "kb_003",
                "title": "Battery Life Optimization",
                "content": "To optimize battery life: 1. Reduce polling frequency 2. Use low-power modes when possible 3. Keep devices updated 4. Check for background processes",
                "category": "optimization",
                "tags": ["battery", "power", "optimization"],
                "views": 567
            },
            {
                "id": "kb_004",
                "title": "Automation Not Working",
                "content": "If automations aren't working: 1. Check device status 2. Verify automation rules 3. Check time schedules 4. Review device permissions",
                "category": "automation",
                "tags": ["automation", "rules", "schedules"],
                "views": 432
            }
        ]
    
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Search knowledge base articles."""
        query_lower = query.lower()
        results = []
        
        for article in self.articles:
            # Simple keyword matching
            if (query_lower in article["title"].lower() or 
                query_lower in article["content"].lower() or
                any(query_lower in tag.lower() for tag in article["tags"])):
                results.append(article)
        
        # Sort by relevance (simple implementation)
        results.sort(key=lambda x: x["views"], reverse=True)
        return results[:5]  # Return top 5 results


class Troubleshooter:
    """Automated troubleshooting system."""
    
    def __init__(self):
        self.diagnostic_rules = self._load_diagnostic_rules()
    
    def _load_diagnostic_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load diagnostic rules."""
        return {
            "device_offline": [
                {
                    "step": 1,
                    "action": "check_power",
                    "description": "Check if device is powered on",
                    "expected_result": "device_powered"
                },
                {
                    "step": 2,
                    "action": "check_network",
                    "description": "Check network connectivity",
                    "expected_result": "network_connected"
                },
                {
                    "step": 3,
                    "action": "restart_device",
                    "description": "Restart the device",
                    "expected_result": "device_online"
                }
            ],
            "connection_problem": [
                {
                    "step": 1,
                    "action": "check_internet",
                    "description": "Check internet connection",
                    "expected_result": "internet_available"
                },
                {
                    "step": 2,
                    "action": "check_router",
                    "description": "Check router status",
                    "expected_result": "router_online"
                },
                {
                    "step": 3,
                    "action": "restart_router",
                    "description": "Restart router if needed",
                    "expected_result": "connection_restored"
                }
            ],
            "automation_issue": [
                {
                    "step": 1,
                    "action": "check_devices",
                    "description": "Check if all devices are online",
                    "expected_result": "all_devices_online"
                },
                {
                    "step": 2,
                    "action": "check_rules",
                    "description": "Verify automation rules",
                    "expected_result": "rules_valid"
                },
                {
                    "step": 3,
                    "action": "test_automation",
                    "description": "Test automation manually",
                    "expected_result": "automation_works"
                }
            ]
        }
    
    async def run_diagnostic(self, issue_type: str, user_id: str) -> Dict[str, Any]:
        """Run diagnostic for a specific issue type."""
        if issue_type not in self.diagnostic_rules:
            return {"error": f"Unknown issue type: {issue_type}"}
        
        rules = self.diagnostic_rules[issue_type]
        results = []
        
        for rule in rules:
            step_result = await self._execute_diagnostic_step(rule, user_id)
            results.append(step_result)
            
            if step_result["status"] == "failed":
                break
        
        return {
            "issue_type": issue_type,
            "user_id": user_id,
            "steps_completed": len(results),
            "results": results,
            "overall_status": "passed" if all(r["status"] == "passed" for r in results) else "failed",
            "recommendations": self._generate_recommendations(results)
        }
    
    async def _execute_diagnostic_step(self, rule: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Execute a diagnostic step."""
        # Simulate diagnostic execution
        await asyncio.sleep(1.0)
        
        # Simulate success/failure
        import random
        success = random.random() > 0.3  # 70% success rate
        
        return {
            "step": rule["step"],
            "action": rule["action"],
            "description": rule["description"],
            "status": "passed" if success else "failed",
            "result": rule["expected_result"] if success else "step_failed",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _generate_recommendations(self, results: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on diagnostic results."""
        recommendations = []
        
        for result in results:
            if result["status"] == "failed":
                if result["action"] == "check_power":
                    recommendations.append("Make sure the device is plugged in and powered on")
                elif result["action"] == "check_network":
                    recommendations.append("Check your WiFi connection and try moving the device closer to the router")
                elif result["action"] == "check_internet":
                    recommendations.append("Check your internet connection and contact your ISP if needed")
        
        if not recommendations:
            recommendations.append("All diagnostic steps passed. If you're still experiencing issues, contact support.")
        
        return recommendations


class RemoteDiagnostics:
    """Remote diagnostics capabilities."""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def start_session(self, user_id: str) -> str:
        """Start a remote diagnostics session."""
        session_id = str(uuid.uuid4())
        
        self.active_sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "started_at": datetime.utcnow(),
            "status": "active",
            "diagnostics": []
        }
        
        logger.info(f"Started remote diagnostics session {session_id} for user {user_id}")
        return session_id
    
    async def end_session(self, session_id: str) -> bool:
        """End a remote diagnostics session."""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        session["status"] = "ended"
        session["ended_at"] = datetime.utcnow()
        
        logger.info(f"Ended remote diagnostics session {session_id}")
        return True
    
    async def collect_diagnostics(self, session_id: str) -> Dict[str, Any]:
        """Collect diagnostics data."""
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        # Collect system diagnostics
        diagnostics = {
            "session_id": session_id,
            "user_id": session["user_id"],
            "timestamp": datetime.utcnow().isoformat(),
            "system_info": await self._collect_system_info(),
            "device_status": await self._collect_device_status(session["user_id"]),
            "network_status": await self._collect_network_status(),
            "logs": await self._collect_recent_logs()
        }
        
        session["diagnostics"].append(diagnostics)
        return diagnostics
    
    async def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information."""
        return {
            "platform": "linux",
            "version": "1.0.0",
            "uptime": "72:30:15",
            "cpu_usage": 45.2,
            "memory_usage": 67.8,
            "disk_usage": 52.1
        }
    
    async def _collect_device_status(self, user_id: str) -> List[Dict[str, Any]]:
        """Collect device status information."""
        # Placeholder implementation
        return [
            {
                "device_id": "device_001",
                "name": "Living Room Light",
                "online": True,
                "battery_level": 85.0,
                "last_seen": datetime.utcnow().isoformat()
            }
        ]
    
    async def _collect_network_status(self) -> Dict[str, Any]:
        """Collect network status information."""
        return {
            "connection_type": "wifi",
            "ssid": "HomeNetwork",
            "signal_strength": -45,
            "latency_ms": 25.0,
            "bandwidth_mbps": 100.0
        }
    
    async def _collect_recent_logs(self) -> List[str]:
        """Collect recent system logs."""
        # Placeholder implementation
        return [
            "2024-01-15 10:30:15 INFO: System started successfully",
            "2024-01-15 10:30:20 INFO: Device discovery completed",
            "2024-01-15 10:35:12 WARNING: Device device_002 battery low"
        ]


class MonitoringSupportSystem:
    """Main monitoring and support system."""
    
    def __init__(self):
        self.health_monitor = HealthMonitor()
        self.user_support = UserSupport()
        self._running = False
    
    async def start(self):
        """Start the monitoring and support system."""
        if self._running:
            return
        
        logger.info("Starting Monitoring and Support System...")
        
        # Start health monitoring
        await self.health_monitor.start_monitoring()
        
        self._running = True
        logger.info("Monitoring and Support System started successfully")
    
    async def stop(self):
        """Stop the monitoring and support system."""
        if not self._running:
            return
        
        logger.info("Stopping Monitoring and Support System...")
        
        # Stop health monitoring
        await self.health_monitor.stop_monitoring()
        
        self._running = False
        logger.info("Monitoring and Support System stopped")
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health."""
        return await self.health_monitor.get_system_health_summary()
    
    async def create_support_ticket(self, user_id: str, title: str, description: str,
                                   category: str, priority: str = "medium") -> SupportTicket:
        """Create a support ticket."""
        return await self.user_support.create_support_ticket(user_id, title, description, category, priority)
    
    async def run_diagnostics(self, issue_type: str, user_id: str) -> Dict[str, Any]:
        """Run automated diagnostics."""
        return await self.user_support.run_troubleshooter(issue_type, user_id)
    
    async def search_help(self, query: str) -> List[Dict[str, Any]]:
        """Search help articles."""
        return await self.user_support.search_knowledge_base(query)
    
    async def start_remote_diagnostics(self, user_id: str) -> str:
        """Start remote diagnostics session."""
        return await self.user_support.start_remote_diagnostics(user_id)


# Global monitoring and support system instance
monitoring_support_system = MonitoringSupportSystem()

async def get_monitoring_support_system() -> MonitoringSupportSystem:
    """Get the global monitoring and support system instance."""
    return monitoring_support_system
