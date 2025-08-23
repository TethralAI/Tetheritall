"""
Test script for the orchestration system.
Demonstrates the complete orchestration workflow.
"""

import asyncio
import logging
from datetime import datetime

from .engine import OrchestrationEngine
from .models import OrchestrationRequest, TriggerType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_basic_orchestration():
    """Test basic orchestration functionality."""
    logger.info("Starting orchestration test...")
    
    # Initialize the orchestration engine
    engine = OrchestrationEngine()
    await engine.start()
    
    try:
        # Test 1: Energy optimization request
        logger.info("\n=== Test 1: Energy Optimization ===")
        energy_request = OrchestrationRequest(
            trigger_type=TriggerType.USER_REQUEST,
            intent="optimize energy usage in the living room",
            user_id="user_123",
            context_hints={"location": "living_room"},
            preferences={"privacy_first": True}
        )
        
        response = await engine.create_execution_plan(energy_request)
        logger.info(f"Energy optimization plan created: {response.plan_id}")
        logger.info(f"Status: {response.status.value}")
        logger.info(f"Approval required: {response.approval_required}")
        if response.plan:
            logger.info(f"Plan has {len(response.plan.steps)} steps")
            logger.info(f"Rationale: {response.rationale[:200]}...")
        
        # Test 2: Comfort control request
        logger.info("\n=== Test 2: Comfort Control ===")
        comfort_request = OrchestrationRequest(
            trigger_type=TriggerType.USER_REQUEST,
            intent="set comfortable temperature and lighting for evening",
            user_id="user_123",
            context_hints={"time": "evening", "activity": "relaxing"},
            preferences={"comfort_optimized": True}
        )
        
        response = await engine.create_execution_plan(comfort_request)
        logger.info(f"Comfort control plan created: {response.plan_id}")
        logger.info(f"Status: {response.status.value}")
        if response.plan:
            logger.info(f"Plan has {len(response.plan.steps)} steps")
        
        # Test 3: Security monitoring request
        logger.info("\n=== Test 3: Security Monitoring ===")
        security_request = OrchestrationRequest(
            trigger_type=TriggerType.USER_REQUEST,
            intent="monitor security and send alerts for any suspicious activity",
            user_id="user_123",
            context_hints={"security_level": "high"},
            preferences={"privacy_first": True, "real_time": True}
        )
        
        response = await engine.create_execution_plan(security_request)
        logger.info(f"Security monitoring plan created: {response.plan_id}")
        logger.info(f"Status: {response.status.value}")
        if response.plan:
            logger.info(f"Plan has {len(response.plan.steps)} steps")
        
        # Test 4: Preview mode request
        logger.info("\n=== Test 4: Preview Mode ===")
        preview_request = OrchestrationRequest(
            trigger_type=TriggerType.PREVIEW_REQUEST,
            intent="what would happen if I automate the morning routine",
            user_id="user_123",
            context_hints={"time": "morning"},
            preview_mode=True
        )
        
        response = await engine.create_execution_plan(preview_request)
        logger.info(f"Preview plan created: {response.plan_id}")
        logger.info(f"Status: {response.status.value}")
        if response.plan:
            logger.info(f"Preview plan has {len(response.plan.steps)} steps")
            logger.info(f"Preview rationale: {response.rationale[:300]}...")
        
        # Test 5: Get system metrics
        logger.info("\n=== Test 5: System Metrics ===")
        metrics = await engine.get_system_metrics()
        logger.info(f"System metrics: {metrics}")
        
        # Test 6: Get plan status
        logger.info("\n=== Test 6: Plan Status ===")
        if response.plan_id:
            status = await engine.get_plan_status(response.plan_id)
            logger.info(f"Plan status: {status}")
        
        # Wait a bit for any background processing
        await asyncio.sleep(2)
        
        logger.info("\n=== Test completed successfully! ===")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        await engine.stop()


async def test_plan_execution():
    """Test plan execution and monitoring."""
    logger.info("\nStarting plan execution test...")
    
    engine = OrchestrationEngine()
    await engine.start()
    
    try:
        # Create a plan that will be executed
        request = OrchestrationRequest(
            trigger_type=TriggerType.USER_REQUEST,
            intent="turn on living room lights and set thermostat to 22 degrees",
            user_id="user_456",
            preview_mode=False
        )
        
        response = await engine.create_execution_plan(request)
        plan_id = response.plan_id
        
        logger.info(f"Created executable plan: {plan_id}")
        
        # Monitor the plan execution
        for i in range(5):
            status = await engine.get_plan_status(plan_id)
            if status:
                logger.info(f"Plan status at {i}s: {status['status']}")
            
            if status and status['status'] in ['completed', 'failed']:
                break
                
            await asyncio.sleep(1)
        
        # Get final metrics
        metrics = await engine.get_plan_metrics(plan_id)
        if metrics:
            logger.info(f"Final plan metrics: {metrics}")
        
    except Exception as e:
        logger.error(f"Execution test failed: {e}")
        raise
    finally:
        await engine.stop()


async def test_error_handling():
    """Test error handling and edge cases."""
    logger.info("\nStarting error handling test...")
    
    engine = OrchestrationEngine()
    await engine.start()
    
    try:
        # Test 1: Invalid request
        logger.info("Testing invalid request...")
        invalid_request = OrchestrationRequest(
            trigger_type=TriggerType.USER_REQUEST,
            intent="",  # Empty intent
            user_id="user_789"
        )
        
        response = await engine.create_execution_plan(invalid_request)
        logger.info(f"Invalid request response: {response.status.value}")
        if response.errors:
            logger.info(f"Errors: {response.errors}")
        
        # Test 2: Request with conflicting goals
        logger.info("Testing conflicting goals...")
        conflicting_request = OrchestrationRequest(
            trigger_type=TriggerType.USER_REQUEST,
            intent="maximize performance while minimizing energy usage",
            user_id="user_789"
        )
        
        response = await engine.create_execution_plan(conflicting_request)
        logger.info(f"Conflicting goals response: {response.status.value}")
        if response.warnings:
            logger.info(f"Warnings: {response.warnings}")
        
        # Test 3: Cancel non-existent plan
        logger.info("Testing cancel non-existent plan...")
        cancelled = await engine.cancel_plan("non_existent_plan")
        logger.info(f"Cancel result: {cancelled}")
        
    except Exception as e:
        logger.error(f"Error handling test failed: {e}")
        raise
    finally:
        await engine.stop()


async def main():
    """Run all orchestration tests."""
    logger.info("=== Orchestration System Test Suite ===")
    logger.info(f"Test started at: {datetime.utcnow()}")
    
    try:
        await test_basic_orchestration()
        await test_plan_execution()
        await test_error_handling()
        
        logger.info("\n=== All tests completed successfully! ===")
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
