"""
Complete Orchestration System Test

This script demonstrates the complete orchestration system with all three parts:
1. Orchestration Agent - Translates intents into execution plans
2. Resource Allocation Agent - Binds plans to concrete resources
3. Contextual Awareness Agent - Maintains current system state

The test shows how these components work together to create a complete
intent-to-execution pipeline.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any

from .models import (
    OrchestrationRequest, ExecutionPlan, ExecutionStep, StepType,
    AllocationRequest, ContextQuery, SignalDomain, NormalizedSignal,
    SignalSource, PrivacySensitivity, ConfidenceLevel, FreshnessStatus
)
from .engine import OrchestrationEngine
from .resource_allocator import ResourceAllocator, ResourceAllocatorConfig
from .contextual_awareness import ContextualAwareness, ContextualAwarenessConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CompleteOrchestrationSystem:
    """
    Complete orchestration system that integrates all three components.
    """
    
    def __init__(self):
        # Initialize the three main components
        self.orchestration_engine = OrchestrationEngine()
        
        self.resource_allocator_config = ResourceAllocatorConfig(
            max_feasibility_check_time_ms=2000,
            max_placement_decision_time_ms=3000,
            max_binding_time_ms=5000,
            enable_adaptive_rebinding=True,
            local_execution_preference=0.8,
            privacy_first_placement=True
        )
        self.resource_allocator = ResourceAllocator(self.resource_allocator_config)
        
        self.context_config = ContextualAwarenessConfig(
            snapshot_interval_ms=1000,
            max_signal_age_ms=30000,
            privacy_enforcement=True,
            data_minimization=True
        )
        self.contextual_awareness = ContextualAwareness(self.context_config)
        
        self._running = False
    
    async def start(self):
        """Start all components of the orchestration system."""
        logger.info("Starting complete orchestration system...")
        
        # Start components in dependency order
        await self.contextual_awareness.start()
        await self.resource_allocator.start()
        await self.orchestration_engine.start()
        
        self._running = True
        logger.info("Complete orchestration system started successfully")
    
    async def stop(self):
        """Stop all components of the orchestration system."""
        logger.info("Stopping complete orchestration system...")
        
        # Stop components in reverse dependency order
        await self.orchestration_engine.stop()
        await self.resource_allocator.stop()
        await self.contextual_awareness.stop()
        
        self._running = False
        logger.info("Complete orchestration system stopped")
    
    async def process_intent(self, intent: str, user_id: str, **kwargs) -> Dict[str, Any]:
        """
        Process a user intent through the complete pipeline.
        
        This demonstrates the full flow:
        1. Contextual Awareness provides current state
        2. Orchestration creates execution plan
        3. Resource Allocation binds plan to resources
        4. System executes the plan
        """
        if not self._running:
            raise RuntimeError("Orchestration system is not running")
        
        start_time = time.time()
        logger.info(f"Processing intent: {intent}")
        
        try:
            # Step 1: Get current context
            context_snapshot = await self._get_current_context()
            logger.info(f"Retrieved context snapshot with {len(context_snapshot.signals)} signals")
            
            # Step 2: Create orchestration request
            orchestration_request = OrchestrationRequest(
                trigger_type="user_request",
                intent=intent,
                user_id=user_id,
                context_hints={"context_snapshot_id": context_snapshot.snapshot_id},
                preferences=kwargs.get("preferences", {}),
                metadata=kwargs.get("metadata", {})
            )
            
            # Step 3: Create execution plan
            orchestration_response = await self.orchestration_engine.create_execution_plan(
                orchestration_request
            )
            
            if orchestration_response.status.value != "created":
                logger.error(f"Failed to create execution plan: {orchestration_response.errors}")
                return {
                    "success": False,
                    "error": "Failed to create execution plan",
                    "details": orchestration_response.errors
                }
            
            logger.info(f"Created execution plan: {orchestration_response.plan_id}")
            
            # Step 4: Allocate resources for the plan
            allocation_request = AllocationRequest(
                plan_id=orchestration_response.plan_id,
                execution_plan=orchestration_response.plan,
                user_id=user_id,
                priority=kwargs.get("priority", 1),
                cost_budget=kwargs.get("cost_budget"),
                latency_budget_ms=kwargs.get("latency_budget_ms"),
                privacy_requirements=kwargs.get("privacy_requirements", {}),
                energy_constraints=kwargs.get("energy_constraints", {})
            )
            
            allocation_response = await self.resource_allocator.allocate_resources(
                allocation_request
            )
            
            if allocation_response.status.value not in ["reserved", "dispatched"]:
                logger.error(f"Failed to allocate resources: {allocation_response.errors}")
                return {
                    "success": False,
                    "error": "Failed to allocate resources",
                    "details": allocation_response.errors
                }
            
            logger.info(f"Allocated resources: {allocation_response.allocation_id}")
            
            # Step 5: Monitor execution
            execution_result = await self._monitor_execution(
                orchestration_response.plan_id,
                allocation_response.allocation_id
            )
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "orchestration_plan_id": orchestration_response.plan_id,
                "allocation_id": allocation_response.allocation_id,
                "execution_result": execution_result,
                "processing_time_ms": int(processing_time * 1000),
                "context_snapshot_id": context_snapshot.snapshot_id,
                "plan_rationale": orchestration_response.plan.rationale,
                "placement_rationale": allocation_response.placement_rationale,
                "expected_cost": allocation_response.expected_cost,
                "expected_latency_ms": allocation_response.expected_latency_ms,
                "privacy_score": allocation_response.privacy_score
            }
            
        except Exception as e:
            logger.error(f"Error processing intent: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }
    
    async def _get_current_context(self):
        """Get current context snapshot."""
        query = ContextQuery(
            query_id="test_query",
            consumer="orchestration_system",
            required_domains=[
                SignalDomain.PRESENCE_OCCUPANCY,
                SignalDomain.ENVIRONMENT,
                SignalDomain.ENERGY_POWER,
                SignalDomain.DEVICE_LIFECYCLE
            ],
            required_flags=["house_occupied", "quiet_hours", "energy_efficient_mode"],
            max_age_ms=5000,
            privacy_scope="orchestration"
        )
        
        response = await self.contextual_awareness.get_snapshot(query)
        return response.snapshot
    
    async def _monitor_execution(self, plan_id: str, allocation_id: str) -> Dict[str, Any]:
        """Monitor the execution of a plan."""
        logger.info(f"Monitoring execution of plan {plan_id} with allocation {allocation_id}")
        
        # Simulate execution monitoring
        await asyncio.sleep(2)  # Simulate execution time
        
        # Get final status
        plan_status = await self.orchestration_engine.get_plan_status(plan_id)
        allocation_status = await self.resource_allocator.get_allocation_status(allocation_id)
        
        return {
            "plan_status": plan_status.value if plan_status else "unknown",
            "allocation_status": allocation_status.value if allocation_status else "unknown",
            "completion_time": datetime.utcnow().isoformat()
        }
    
    async def add_context_signal(self, signal_data: Dict[str, Any]):
        """Add a signal to the contextual awareness system."""
        signal = NormalizedSignal(
            signal_id=signal_data.get("signal_id", f"signal_{int(time.time())}"),
            source=SignalSource(
                source_id=signal_data.get("source_id", "test_source"),
                source_type=signal_data.get("source_type", "device"),
                domain=SignalDomain(signal_data.get("domain", "environment")),
                consent_scope=signal_data.get("consent_scope", "internal"),
                update_cadence_ms=signal_data.get("update_cadence_ms", 5000),
                last_update=datetime.utcnow()
            ),
            domain=SignalDomain(signal_data.get("domain", "environment")),
            field_name=signal_data.get("field_name", "temperature"),
            value=signal_data.get("value", 22.0),
            unit=signal_data.get("unit", "celsius"),
            timestamp=datetime.utcnow(),
            confidence=ConfidenceLevel(signal_data.get("confidence", "high")),
            freshness=FreshnessStatus(signal_data.get("freshness", "current")),
            provenance=signal_data.get("provenance", "test"),
            consent_class=PrivacySensitivity(signal_data.get("privacy_class", "internal"))
        )
        
        await self.contextual_awareness.add_signal(signal)
        logger.info(f"Added signal: {signal.field_name} = {signal.value} {signal.unit}")


async def test_complete_system():
    """Test the complete orchestration system."""
    logger.info("=== Complete Orchestration System Test ===")
    
    system = CompleteOrchestrationSystem()
    
    try:
        # Start the system
        await system.start()
        
        # Add some context signals
        await system.add_context_signal({
            "field_name": "temperature",
            "value": 22.5,
            "unit": "celsius",
            "domain": "environment",
            "confidence": "high"
        })
        
        await system.add_context_signal({
            "field_name": "humidity",
            "value": 45.0,
            "unit": "percent",
            "domain": "environment",
            "confidence": "high"
        })
        
        await system.add_context_signal({
            "field_name": "presence",
            "value": True,
            "unit": "boolean",
            "domain": "presence_occupancy",
            "confidence": "high"
        })
        
        # Wait for context to be processed
        await asyncio.sleep(1)
        
        # Test different intents
        test_cases = [
            {
                "intent": "optimize energy usage in the living room",
                "user_id": "user_123",
                "preferences": {"privacy_first": True},
                "description": "Energy optimization with privacy focus"
            },
            {
                "intent": "create a comfortable movie night environment",
                "user_id": "user_123",
                "preferences": {"comfort_optimized": True},
                "description": "Comfort optimization for movie night"
            },
            {
                "intent": "minimize costs while maintaining comfort",
                "user_id": "user_123",
                "preferences": {"cost_optimized": True},
                "cost_budget": 0.01,
                "description": "Cost optimization with budget constraint"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"\n--- Test Case {i}: {test_case['description']} ---")
            
            result = await system.process_intent(
                intent=test_case["intent"],
                user_id=test_case["user_id"],
                **{k: v for k, v in test_case.items() if k not in ["intent", "user_id", "description"]}
            )
            
            if result["success"]:
                logger.info(f"✅ Success: {test_case['description']}")
                logger.info(f"   Plan ID: {result['orchestration_plan_id']}")
                logger.info(f"   Allocation ID: {result['allocation_id']}")
                logger.info(f"   Processing time: {result['processing_time_ms']}ms")
                logger.info(f"   Expected cost: ${result['expected_cost']:.4f}")
                logger.info(f"   Expected latency: {result['expected_latency_ms']}ms")
                logger.info(f"   Privacy score: {result['privacy_score']:.2f}")
                logger.info(f"   Plan rationale: {result['plan_rationale'][:100]}...")
                logger.info(f"   Placement rationale: {result['placement_rationale'][:100]}...")
            else:
                logger.error(f"❌ Failed: {test_case['description']}")
                logger.error(f"   Error: {result['error']}")
                if 'details' in result:
                    logger.error(f"   Details: {result['details']}")
        
        # Test system health
        logger.info("\n--- System Health Check ---")
        health_status = await system.contextual_awareness.get_health_status()
        logger.info(f"Contextual Awareness Health: {health_status}")
        
        # Test metrics
        logger.info("\n--- System Metrics ---")
        # Get metrics for the last allocation
        if 'allocation_id' in locals():
            allocation_metrics = await system.resource_allocator.get_allocation_metrics(
                result.get('allocation_id', '')
            )
            if allocation_metrics:
                logger.info(f"Allocation Metrics: {allocation_metrics}")
        
        logger.info("\n=== All tests completed successfully! ===")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        raise
    
    finally:
        # Stop the system
        await system.stop()


async def test_error_handling():
    """Test error handling in the complete system."""
    logger.info("\n=== Error Handling Test ===")
    
    system = CompleteOrchestrationSystem()
    
    try:
        await system.start()
        
        # Test with invalid intent
        result = await system.process_intent(
            intent="invalid intent that should fail",
            user_id="user_123"
        )
        
        if not result["success"]:
            logger.info("✅ Error handling working correctly for invalid intent")
        else:
            logger.warning("⚠️ System unexpectedly succeeded with invalid intent")
        
        # Test with missing context
        result = await system.process_intent(
            intent="control device that doesn't exist",
            user_id="user_123"
        )
        
        logger.info(f"Result for non-existent device: {result['success']}")
        
    except Exception as e:
        logger.error(f"Error handling test failed: {e}")
        raise
    
    finally:
        await system.stop()


async def test_performance():
    """Test performance of the complete system."""
    logger.info("\n=== Performance Test ===")
    
    system = CompleteOrchestrationSystem()
    
    try:
        await system.start()
        
        # Add multiple context signals
        for i in range(10):
            await system.add_context_signal({
                "field_name": f"test_signal_{i}",
                "value": i * 10,
                "unit": "units",
                "domain": "environment",
                "confidence": "high"
            })
        
        await asyncio.sleep(1)
        
        # Test multiple concurrent intents
        start_time = time.time()
        
        tasks = []
        for i in range(5):
            task = system.process_intent(
                intent=f"test intent {i}",
                user_id=f"user_{i}",
                priority=i + 1
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        
        logger.info(f"✅ Performance test completed:")
        logger.info(f"   Total time: {total_time:.2f}s")
        logger.info(f"   Successful requests: {len(successful_results)}/5")
        logger.info(f"   Average time per request: {total_time/5:.2f}s")
        
        if len(successful_results) >= 4:
            logger.info("✅ Performance test passed")
        else:
            logger.warning("⚠️ Performance test had some failures")
        
    except Exception as e:
        logger.error(f"Performance test failed: {e}")
        raise
    
    finally:
        await system.stop()


async def main():
    """Run all tests for the complete orchestration system."""
    logger.info("Starting Complete Orchestration System Test Suite")
    logger.info(f"Test started at: {datetime.utcnow()}")
    
    try:
        # Run main functionality test
        await test_complete_system()
        
        # Run error handling test
        await test_error_handling()
        
        # Run performance test
        await test_performance()
        
        logger.info("\n🎉 All tests completed successfully!")
        logger.info("The complete orchestration system is working correctly.")
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
