"""
Edge Computing
Distributed edge computing system for local processing and intelligence.
Includes quantum computing capabilities and quantum-enhanced edge processing.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import json
import uuid
from enum import Enum
from dataclasses import dataclass
import psutil
import platform

from shared.config.settings import settings
from shared.database.api_database import get_session_factory, session_scope

logger = logging.getLogger(__name__)


class EdgeNodeStatus(Enum):
    """Edge node status states."""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class WorkloadType(Enum):
    """Workload type definitions."""
    INFERENCE = "inference"
    TRAINING = "training"
    DATA_PROCESSING = "data_processing"
    STREAMING = "streaming"
    BATCH = "batch"
    QUANTUM_INFERENCE = "quantum_inference"
    QUANTUM_OPTIMIZATION = "quantum_optimization"
    QUANTUM_SIMULATION = "quantum_simulation"
    HYBRID_QUANTUM_CLASSICAL = "hybrid_quantum_classical"


class WorkloadPriority(Enum):
    """Workload priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    QUANTUM_CRITICAL = "quantum_critical"


@dataclass
class EdgeNode:
    """Edge node information."""
    node_id: str
    name: str
    location: str
    capabilities: List[str]
    quantum_capabilities: List[str]
    resources: Dict[str, Any]
    quantum_resources: Dict[str, Any]
    status: EdgeNodeStatus
    last_heartbeat: datetime
    created_at: datetime
    updated_at: datetime


@dataclass
class Workload:
    """Workload definition."""
    workload_id: str
    name: str
    workload_type: WorkloadType
    priority: WorkloadPriority
    requirements: Dict[str, Any]
    quantum_requirements: Dict[str, Any]
    code: str
    data: Dict[str, Any]
    target_nodes: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None


@dataclass
class WorkloadResult:
    """Workload execution result."""
    workload_id: str
    node_id: str
    status: str
    result: Dict[str, Any]
    execution_time: float
    quantum_execution_time: Optional[float]
    quantum_qubits_used: Optional[int]
    error_message: Optional[str]
    timestamp: datetime


class EdgeComputing:
    """Distributed edge computing system."""
    
    def __init__(self):
        self._running = False
        self._session_factory = get_session_factory(settings.database_url)
        self._edge_nodes: Dict[str, EdgeNode] = {}
        self._workloads: Dict[str, Workload] = {}
        self._workload_results: Dict[str, WorkloadResult] = {}
        self._node_workloads: Dict[str, List[str]] = {}
        self._callbacks: Dict[str, List[Callable]] = {
            'node_registered': [],
            'node_offline': [],
            'workload_started': [],
            'workload_completed': [],
            'workload_failed': [],
            'resource_update': []
        }
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._workload_scheduler_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Edge computing configuration
        self._max_workloads_per_node = 5
        self._heartbeat_interval = 30  # seconds
        self._workload_timeout = 300  # seconds
        self._auto_scaling_enabled = True
        
        # Quantum edge computing configuration
        self._quantum_enabled = True
        self._quantum_backends = {
            'ibm_quantum': 'IBM Quantum Experience',
            'rigetti': 'Rigetti Forest',
            'ionq': 'IonQ',
            'dwave': 'D-Wave Systems',
            'simulator': 'Quantum Simulator'
        }
        self._quantum_workload_types = [
            'quantum_inference',
            'quantum_optimization',
            'quantum_simulation',
            'hybrid_quantum_classical'
        ]
        
    async def start(self):
        """Start the edge computing system."""
        self._running = True
        
        # Register local node
        await self._register_local_node()
        
        # Start background tasks
        self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
        self._workload_scheduler_task = asyncio.create_task(self._workload_scheduler())
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_workloads())
        
        logger.info("Edge Computing system started")
        
    async def stop(self):
        """Stop the edge computing system."""
        self._running = False
        
        # Cancel background tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._workload_scheduler_task:
            self._workload_scheduler_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
            
        # Stop all workloads
        await self._stop_all_workloads()
        
        logger.info("Edge Computing system stopped")
        
    def is_running(self) -> bool:
        """Check if the edge computing system is running."""
        return self._running
        
    async def register_edge_node(self, node_info: Dict[str, Any]) -> str:
        """Register a new edge node."""
        try:
            node_id = str(uuid.uuid4())
            
            # Get system resources
            resources = await self._get_system_resources()
            quantum_resources = await self._get_quantum_resources()
            
            node = EdgeNode(
                node_id=node_id,
                name=node_info.get("name", f"edge-node-{node_id[:8]}"),
                location=node_info.get("location", "unknown"),
                capabilities=node_info.get("capabilities", []),
                quantum_capabilities=node_info.get("quantum_capabilities", []),
                resources=resources,
                quantum_resources=quantum_resources,
                status=EdgeNodeStatus.ONLINE,
                last_heartbeat=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self._edge_nodes[node_id] = node
            self._node_workloads[node_id] = []
            
            # Notify callbacks
            await self._notify_callbacks('node_registered', node)
            
            logger.info(f"Registered edge node: {node.name} ({node_id})")
            return node_id
            
        except Exception as e:
            logger.error(f"Error registering edge node: {e}")
            raise
            
    async def unregister_edge_node(self, node_id: str) -> bool:
        """Unregister an edge node."""
        try:
            if node_id not in self._edge_nodes:
                logger.warning(f"Edge node {node_id} not found")
                return False
                
            # Stop all workloads on this node
            if node_id in self._node_workloads:
                for workload_id in self._node_workloads[node_id]:
                    await self.stop_workload(workload_id)
                    
            # Remove node
            del self._edge_nodes[node_id]
            if node_id in self._node_workloads:
                del self._node_workloads[node_id]
                
            logger.info(f"Unregistered edge node: {node_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error unregistering edge node {node_id}: {e}")
            return False
            
    async def submit_workload(self, workload_info: Dict[str, Any]) -> str:
        """Submit a workload for execution."""
        try:
            workload_id = str(uuid.uuid4())
            
            workload = Workload(
                workload_id=workload_id,
                name=workload_info.get("name", f"workload-{workload_id[:8]}"),
                workload_type=WorkloadType(workload_info.get("type", "inference")),
                priority=WorkloadPriority(workload_info.get("priority", "normal")),
                requirements=workload_info.get("requirements", {}),
                quantum_requirements=workload_info.get("quantum_requirements", {}),
                code=workload_info.get("code", ""),
                data=workload_info.get("data", {}),
                target_nodes=workload_info.get("target_nodes", []),
                created_at=datetime.utcnow(),
                expires_at=workload_info.get("expires_at")
            )
            
            self._workloads[workload_id] = workload
            
            logger.info(f"Submitted workload: {workload.name} ({workload_id})")
            return workload_id
            
        except Exception as e:
            logger.error(f"Error submitting workload: {e}")
            raise
            
    async def get_workload_status(self, workload_id: str) -> Optional[Dict[str, Any]]:
        """Get workload status."""
        try:
            if workload_id not in self._workloads:
                return None
                
            workload = self._workloads[workload_id]
            
            # Find which nodes are executing this workload
            executing_nodes = []
            for node_id, node_workloads in self._node_workloads.items():
                if workload_id in node_workloads:
                    executing_nodes.append(node_id)
                    
            # Get results
            results = []
            for result in self._workload_results.values():
                if result.workload_id == workload_id:
                    results.append({
                        "node_id": result.node_id,
                        "status": result.status,
                        "result": result.result,
                        "execution_time": result.execution_time,
                        "error_message": result.error_message,
                        "timestamp": result.timestamp.isoformat()
                    })
                    
            return {
                "workload_id": workload_id,
                "name": workload.name,
                "type": workload.workload_type.value,
                "priority": workload.priority.value,
                "status": "executing" if executing_nodes else "pending",
                "executing_nodes": executing_nodes,
                "results": results,
                "created_at": workload.created_at.isoformat(),
                "expires_at": workload.expires_at.isoformat() if workload.expires_at else None
            }
            
        except Exception as e:
            logger.error(f"Error getting workload status {workload_id}: {e}")
            return None
            
    async def stop_workload(self, workload_id: str) -> bool:
        """Stop a workload."""
        try:
            if workload_id not in self._workloads:
                logger.warning(f"Workload {workload_id} not found")
                return False
                
            # Remove from node workloads
            for node_id, node_workloads in self._node_workloads.items():
                if workload_id in node_workloads:
                    node_workloads.remove(workload_id)
                    
            # Remove workload
            del self._workloads[workload_id]
            
            logger.info(f"Stopped workload: {workload_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping workload {workload_id}: {e}")
            return False
            
    async def list_edge_nodes(self) -> List[EdgeNode]:
        """List all edge nodes."""
        return list(self._edge_nodes.values())
        
    async def get_edge_node_info(self, node_id: str) -> Optional[EdgeNode]:
        """Get edge node information."""
        return self._edge_nodes.get(node_id)
        
    async def get_edge_computing_statistics(self) -> Dict[str, Any]:
        """Get edge computing statistics."""
        total_nodes = len(self._edge_nodes)
        online_nodes = len([node for node in self._edge_nodes.values() if node.status == EdgeNodeStatus.ONLINE])
        total_workloads = len(self._workloads)
        completed_workloads = len([result for result in self._workload_results.values() if result.status == "completed"])
        
        # Node status distribution
        status_counts = {}
        for node in self._edge_nodes.values():
            status = node.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
        # Workload type distribution
        type_counts = {}
        for workload in self._workloads.values():
            workload_type = workload.workload_type.value
            type_counts[workload_type] = type_counts.get(workload_type, 0) + 1
            
        # Resource utilization
        total_cpu = 0
        total_memory = 0
        total_qubits = 0
        quantum_nodes = 0
        
        for node in self._edge_nodes.values():
            if "cpu_percent" in node.resources:
                total_cpu += node.resources["cpu_percent"]
            if "memory_percent" in node.resources:
                total_memory += node.resources["memory_percent"]
            if "available_qubits" in node.quantum_resources:
                total_qubits += node.quantum_resources["available_qubits"]
                quantum_nodes += 1
                
        avg_cpu = total_cpu / total_nodes if total_nodes > 0 else 0
        avg_memory = total_memory / total_nodes if total_nodes > 0 else 0
        avg_qubits = total_qubits / quantum_nodes if quantum_nodes > 0 else 0
        
        return {
            'total_nodes': total_nodes,
            'online_nodes': online_nodes,
            'total_workloads': total_workloads,
            'completed_workloads': completed_workloads,
            'node_status_distribution': status_counts,
            'workload_type_distribution': type_counts,
            'average_cpu_utilization': avg_cpu,
            'average_memory_utilization': avg_memory,
            'quantum_nodes': quantum_nodes,
            'total_available_qubits': total_qubits,
            'average_qubits_per_quantum_node': avg_qubits,
            'auto_scaling_enabled': self._auto_scaling_enabled,
            'quantum_enabled': self._quantum_enabled,
            'available_quantum_backends': len(self._quantum_backends)
        }
        
    def add_callback(self, event: str, callback: Callable):
        """Add a callback for edge computing events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
            logger.debug(f"Added callback for event: {event}")
        else:
            logger.warning(f"Unknown event type: {event}")
            
    def remove_callback(self, event: str, callback: Callable):
        """Remove a callback for edge computing events."""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
            logger.debug(f"Removed callback for event: {event}")
            
    async def _register_local_node(self):
        """Register the local node."""
        try:
            node_info = {
                "name": f"local-node-{platform.node()}",
                "location": "local",
                "capabilities": ["inference", "data_processing", "streaming"]
            }
            
            await self.register_edge_node(node_info)
            
        except Exception as e:
            logger.error(f"Error registering local node: {e}")
            
    async def _get_system_resources(self) -> Dict[str, Any]:
        """Get current system resources."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": memory.available,
                "memory_total": memory.total,
                "disk_percent": disk.percent,
                "disk_free": disk.free,
                "disk_total": disk.total
            }
            
        except Exception as e:
            logger.error(f"Error getting system resources: {e}")
            return {}
            
    async def _get_quantum_resources(self) -> Dict[str, Any]:
        """Get quantum computing resources."""
        try:
            # Simulate quantum resource detection
            # In a real implementation, this would detect actual quantum hardware
            
            # Simulate quantum backend availability
            available_qubits = 50  # Simulate 50 qubits available
            quantum_backends = ['simulator', 'ibm_quantum']
            coherence_time = 100  # microseconds
            error_rate = 0.01  # 1% error rate
            
            return {
                "available_qubits": available_qubits,
                "quantum_backends": quantum_backends,
                "coherence_time": coherence_time,
                "error_rate": error_rate,
                "quantum_enabled": self._quantum_enabled
            }
            
        except Exception as e:
            logger.error(f"Error getting quantum resources: {e}")
            return {
                "available_qubits": 0,
                "quantum_backends": [],
                "coherence_time": 0,
                "error_rate": 1.0,
                "quantum_enabled": False
            }
            
    async def _heartbeat_monitor(self):
        """Monitor node heartbeats."""
        while self._running:
            try:
                current_time = datetime.utcnow()
                offline_threshold = timedelta(seconds=self._heartbeat_interval * 3)
                
                for node_id, node in self._edge_nodes.items():
                    if current_time - node.last_heartbeat > offline_threshold:
                        if node.status != EdgeNodeStatus.OFFLINE:
                            node.status = EdgeNodeStatus.OFFLINE
                            node.updated_at = current_time
                            
                            # Notify callbacks
                            await self._notify_callbacks('node_offline', node)
                            
                            logger.warning(f"Edge node {node.name} went offline")
                            
                await asyncio.sleep(self._heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(self._heartbeat_interval)
                
    async def _workload_scheduler(self):
        """Schedule workloads to available nodes."""
        while self._running:
            try:
                # Get available nodes
                available_nodes = [
                    node for node in self._edge_nodes.values()
                    if node.status == EdgeNodeStatus.ONLINE and
                    len(self._node_workloads.get(node.node_id, [])) < self._max_workloads_per_node
                ]
                
                # Get pending workloads
                pending_workloads = [
                    workload for workload in self._workloads.values()
                    if not any(workload.workload_id in node_workloads 
                             for node_workloads in self._node_workloads.values())
                ]
                
                # Schedule workloads
                for workload in pending_workloads:
                    if available_nodes:
                        # Find best node based on requirements and resources
                        best_node = await self._find_best_node(workload, available_nodes)
                        
                        if best_node:
                            # Assign workload to node
                            if best_node.node_id not in self._node_workloads:
                                self._node_workloads[best_node.node_id] = []
                            self._node_workloads[best_node.node_id].append(workload.workload_id)
                            
                            # Execute workload
                            asyncio.create_task(self._execute_workload(workload, best_node))
                            
                            # Notify callbacks
                            await self._notify_callbacks('workload_started', {
                                "workload_id": workload.workload_id,
                                "node_id": best_node.node_id
                            })
                            
                            logger.info(f"Scheduled workload {workload.workload_id} on node {best_node.node_id}")
                            
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in workload scheduler: {e}")
                await asyncio.sleep(5)
                
    async def _find_best_node(self, workload: Workload, available_nodes: List[EdgeNode]) -> Optional[EdgeNode]:
        """Find the best node for a workload."""
        try:
            if not available_nodes:
                return None
                
            # Simple selection: choose node with least workloads
            best_node = min(available_nodes, 
                          key=lambda node: len(self._node_workloads.get(node.node_id, [])))
            
            return best_node
            
        except Exception as e:
            logger.error(f"Error finding best node: {e}")
            return None
            
    async def _execute_workload(self, workload: Workload, node: EdgeNode):
        """Execute a workload on a node."""
        try:
            start_time = datetime.utcnow()
            
            # Check if this is a quantum workload
            is_quantum_workload = workload.workload_type.value in self._quantum_workload_types
            quantum_execution_time = None
            quantum_qubits_used = None
            
            if is_quantum_workload and self._quantum_enabled:
                # Simulate quantum workload execution
                await asyncio.sleep(3)  # Quantum processing takes longer
                quantum_execution_time = (datetime.utcnow() - start_time).total_seconds()
                quantum_qubits_used = workload.quantum_requirements.get("qubits_required", 10)
                logger.info(f"Executing quantum workload {workload.workload_id} with {quantum_qubits_used} qubits")
            else:
                # Simulate classical workload execution
                await asyncio.sleep(2)  # Simulate processing time
                
            # Generate result
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            result = WorkloadResult(
                workload_id=workload.workload_id,
                node_id=node.node_id,
                status="completed",
                result={
                    "output": "mock_result",
                    "processing_time": execution_time,
                    "node_name": node.name,
                    "quantum_enhanced": is_quantum_workload
                },
                execution_time=execution_time,
                quantum_execution_time=quantum_execution_time,
                quantum_qubits_used=quantum_qubits_used,
                error_message=None,
                timestamp=datetime.utcnow()
            )
            
            self._workload_results[workload.workload_id] = result
            
            # Remove from node workloads
            if node.node_id in self._node_workloads:
                if workload.workload_id in self._node_workloads[node.node_id]:
                    self._node_workloads[node.node_id].remove(workload.workload_id)
                    
            # Notify callbacks
            await self._notify_callbacks('workload_completed', result)
            
            logger.info(f"Completed workload {workload.workload_id} on node {node.node_id}")
            
        except Exception as e:
            logger.error(f"Error executing workload {workload.workload_id}: {e}")
            
            # Create error result
            result = WorkloadResult(
                workload_id=workload.workload_id,
                node_id=node.node_id,
                status="failed",
                result={},
                execution_time=0,
                quantum_execution_time=None,
                quantum_qubits_used=None,
                error_message=str(e),
                timestamp=datetime.utcnow()
            )
            
            self._workload_results[workload.workload_id] = result
            
            # Remove from node workloads
            if node.node_id in self._node_workloads:
                if workload.workload_id in self._node_workloads[node.node_id]:
                    self._node_workloads[node.node_id].remove(workload.workload_id)
                    
            # Notify callbacks
            await self._notify_callbacks('workload_failed', result)
            
    async def _stop_all_workloads(self):
        """Stop all running workloads."""
        try:
            for workload_id in list(self._workloads.keys()):
                await self.stop_workload(workload_id)
                
        except Exception as e:
            logger.error(f"Error stopping all workloads: {e}")
            
    async def _cleanup_expired_workloads(self):
        """Clean up expired workloads."""
        while self._running:
            try:
                current_time = datetime.utcnow()
                
                expired_workloads = []
                for workload_id, workload in self._workloads.items():
                    if workload.expires_at and current_time > workload.expires_at:
                        expired_workloads.append(workload_id)
                        
                for workload_id in expired_workloads:
                    await self.stop_workload(workload_id)
                    
                if expired_workloads:
                    logger.info(f"Cleaned up {len(expired_workloads)} expired workloads")
                    
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)
                
    async def _notify_callbacks(self, event: str, data: Any, **kwargs):
        """Notify all callbacks for an event."""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data, **kwargs)
                    else:
                        callback(data, **kwargs)
                except Exception as e:
                    logger.error(f"Error in callback for event {event}: {e}")
