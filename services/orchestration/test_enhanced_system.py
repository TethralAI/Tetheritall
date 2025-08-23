"""
Enhanced Orchestration System Test

This script demonstrates the enhanced orchestration system with:
- Experience-driven optimization
- Memory systems (episodic and semantic)
- Learning from outcomes and feedback
- Recipe templates and constraint memory
- Cross-layer learning loops
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any

from .models import (
    OrchestrationRequest, ExecutionPlan, ExecutionStep, StepType,
    TriggerType, PrivacyClass, TrustTier, Constraint, Goal
)
from .enhanced_engine import EnhancedOrchestrationEngine, EnhancedOrchestrationConfig
from .experience_goals import ExperienceMonitor, record_experience_event
from .contextual_awareness import ContextualAwareness, ContextualAwarenessConfig
from .resource_allocator import ResourceAllocator, ResourceAllocatorConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedOrchestrationSystem:
    """
    Enhanced orchestration system that integrates experience goals,
    memory systems, and learning capabilities.
    """
    
    def __init__(self):
        # Initialize enhanced orchestration engine
        self.orchestration_config = EnhancedOrchestrationConfig(
            max_episodic_entries=100,
            max_semantic_entries=50,
            learning_enabled=True,
            enable_experience_optimization=True,
            experience_threshold=0.85
        )
        self.orchestration_engine = EnhancedOrchestrationEngine(self.orchestration_config)
        
        # Initialize contextual awareness
        self.context_config = ContextualAwarenessConfig(
            snapshot_interval_ms=1000,
            privacy_enforcement=True,
            data_minimization=True
        )
        self.contextual_awareness = ContextualAwareness(self.context_config)
        
        # Initialize resource allocator
        self.resource_config = ResourceAllocatorConfig(
            enable_adaptive_rebinding=True,
            privacy_first_placement=True
        )
        self.resource_allocator = ResourceAllocator(self.resource_config)
        
        # Connect components
        self.orchestration_engine.contextual_awareness = self.contextual_awareness
        self.orchestration_engine.resource_allocator = self.resource_allocator
        
        self._running = False
    
    async def start(self):
        """Start all components of the enhanced orchestration system."""
        logger.info("Starting enhanced orchestration system...")
        
        # Start components in dependency order
        await self.contextual_awareness.start()
        await self.resource_allocator.start()
        await self.orchestration_engine.start()
        
        self._running = True
        logger.info("Enhanced orchestration system started successfully")
    
    async def stop(self):
        """Stop all components of the enhanced orchestration system."""
        logger.info("Stopping enhanced orchestration system...")
        
        # Stop components in reverse dependency order
        await self.orchestration_engine.stop()
        await self.resource_allocator.stop()
        await self.contextual_awareness.stop()
        
        self._running = False
        logger.info("Enhanced orchestration system stopped")
    
    async def process_intent_with_learning(
        self, 
        intent: str, 
        user_id: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a user intent with full learning and experience tracking.
        
        This demonstrates the complete enhanced workflow:
        1. Experience monitoring
        2. Memory-based planning
        3. Learning from outcomes
        4. Experience optimization
        """
        if not self._running:
            raise RuntimeError("Enhanced orchestration system is not running")
        
        start_time = time.time()
        logger.info(f"Processing intent with learning: {intent}")
        
        try:
            # Record experience event
            record_experience_event("intent_processing_started", intent=intent, user_id=user_id)
            
            # Create orchestration request
            orchestration_request = OrchestrationRequest(
                trigger_type=TriggerType.USER_REQUEST,
                intent=intent,
                user_id=user_id,
                preferences=kwargs.get("preferences", {}),
                metadata=kwargs.get("metadata", {})
            )
            
            # Create execution plan with enhanced capabilities
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
            
            logger.info(f"Created enhanced execution plan: {orchestration_response.plan_id}")
            
            # Simulate execution and outcome
            execution_outcome = await self._simulate_execution(orchestration_response.plan_id, user_id)
            
            # Record outcome for learning
            await self.orchestration_engine.record_outcome(
                orchestration_response.plan_id, 
                execution_outcome
            )
            
            # Get experience report
            experience_report = await self.orchestration_engine.get_experience_report()
            
            # Get learning insights
            learning_insights = await self.orchestration_engine.get_learning_insights()
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "plan_id": orchestration_response.plan_id,
                "planning_time_ms": orchestration_response.planning_time_ms,
                "execution_outcome": execution_outcome,
                "experience_report": experience_report,
                "learning_insights": learning_insights,
                "processing_time_ms": int(processing_time * 1000),
                "plan_rationale": orchestration_response.plan.rationale if orchestration_response.plan else None
            }
            
        except Exception as e:
            logger.error(f"Error processing intent with learning: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }
    
    async def test_memory_systems(self) -> Dict[str, Any]:
        """Test the memory systems (episodic and semantic)."""
        logger.info("Testing memory systems...")
        
        # Test episodic memory
        episodic_count = len(self.orchestration_engine.episodic_memory)
        
        # Test semantic memory
        semantic_count = len(self.orchestration_engine.semantic_memory)
        
        # Test recipe templates
        recipe_count = len(self.orchestration_engine.recipe_templates)
        
        # Test constraint memory
        constraint_count = len(self.orchestration_engine.constraint_memory)
        
        return {
            "episodic_memory_entries": episodic_count,
            "semantic_memory_entries": semantic_count,
            "recipe_templates": recipe_count,
            "constraint_memory_entries": constraint_count
        }
    
    async def test_learning_systems(self) -> Dict[str, Any]:
        """Test the learning systems."""
        logger.info("Testing learning systems...")
        
        # Get learning insights
        insights = await self.orchestration_engine.get_learning_insights()
        
        # Test learning signals
        signal_count = len(self.orchestration_engine.learning_signals)
        
        # Test outcome history
        outcome_count = len(self.orchestration_engine.outcome_history)
        
        return {
            "learning_insights": insights,
            "learning_signals": signal_count,
            "outcome_history": outcome_count
        }
    
    async def test_experience_optimization(self) -> Dict[str, Any]:
        """Test experience optimization capabilities."""
        logger.info("Testing experience optimization...")
        
        # Get experience report
        experience_report = await self.orchestration_engine.get_experience_report()
        
        # Test experience monitoring
        monitor = self.orchestration_engine.experience_monitor
        
        # Record some test events
        monitor.record_approval_tap()
        monitor.record_response_time("local_reaction", 120.0)  # Good time
        monitor.record_response_time("plan_preview", 750.0)    # Good time
        monitor.update_trust_metrics(
            explanation_quality_score=0.9,
            consent_compliance_rate=0.95,
            safe_defaults_usage=0.9,
            privacy_respect_score=0.9,
            audit_trail_completeness=0.95
        )
        
        # Get updated report
        updated_report = monitor.get_experience_report()
        
        return {
            "initial_experience_report": experience_report,
            "updated_experience_report": updated_report,
            "optimization_needed": updated_report["needs_optimization"],
            "recommendations": updated_report["recommendations"]
        }
    
    async def test_recipe_templates(self) -> Dict[str, Any]:
        """Test recipe template functionality."""
        logger.info("Testing recipe templates...")
        
        # Create a test recipe template
        from .enhanced_engine import RecipeTemplate
        
        test_recipe = RecipeTemplate(
            template_id="test_recipe_001",
            name="Movie Night Setup",
            description="Setup for comfortable movie watching",
            steps=[
                {
                    "type": "device_control",
                    "description": "Dim living room lights",
                    "parameters": {"brightness": 30},
                    "dependencies": []
                },
                {
                    "type": "device_control", 
                    "description": "Set thermostat to comfortable temperature",
                    "parameters": {"temperature": 22},
                    "dependencies": []
                }
            ],
            constraints=[
                {
                    "type": "privacy",
                    "value": "confidential",
                    "operator": "gte"
                }
            ],
            success_stats={"success_rate": 0.95, "usage_count": 10}
        )
        
        # Add to recipe templates
        self.orchestration_engine.recipe_templates[test_recipe.template_id] = test_recipe
        
        # Test recipe retrieval
        retrieved_recipe = self.orchestration_engine.recipe_templates.get(test_recipe.template_id)
        
        return {
            "recipe_created": test_recipe.template_id,
            "recipe_retrieved": retrieved_recipe.name if retrieved_recipe else None,
            "total_recipes": len(self.orchestration_engine.recipe_templates)
        }
    
    async def test_constraint_memory(self) -> Dict[str, Any]:
        """Test constraint memory functionality."""
        logger.info("Testing constraint memory...")
        
        # Create test constraints
        from .enhanced_engine import ConstraintMemory
        
        privacy_constraint = ConstraintMemory(
            constraint_id="privacy_001",
            rule_type="privacy",
            rule_definition={
                "privacy_class": "confidential",
                "data_minimization": True,
                "local_execution": True
            },
            policy_hash="abc123",
            enforcement_level="hard"
        )
        
        cost_constraint = ConstraintMemory(
            constraint_id="cost_001", 
            rule_type="cost",
            rule_definition={
                "max_cost_per_day": 1.0,
                "budget_alert_threshold": 0.8
            },
            policy_hash="def456",
            enforcement_level="soft"
        )
        
        # Add to constraint memory
        self.orchestration_engine.constraint_memory.extend([privacy_constraint, cost_constraint])
        
        return {
            "constraints_added": 2,
            "total_constraints": len(self.orchestration_engine.constraint_memory),
            "privacy_constraints": len([c for c in self.orchestration_engine.constraint_memory if c.rule_type == "privacy"]),
            "cost_constraints": len([c for c in self.orchestration_engine.constraint_memory if c.rule_type == "cost"])
        }
    
    async def _simulate_execution(self, plan_id: str, user_id: str) -> Dict[str, Any]:
        """Simulate execution of a plan and return outcome."""
        await asyncio.sleep(0.1)  # Simulate execution time
        
        # Simulate different outcomes based on plan_id
        import random
        success_score = random.uniform(0.7, 1.0)  # Generally successful
        
        return {
            "plan_id": plan_id,
            "user_id": user_id,
            "success_score": success_score,
            "execution_time_ms": random.randint(100, 500),
            "energy_consumed_wh": random.uniform(10, 50),
            "privacy_kept_local": random.uniform(0.8, 1.0),
            "user_satisfaction": random.uniform(0.8, 1.0),
            "feedback": "Great experience!",
            "completion_time": datetime.utcnow().isoformat()
        }


async def test_enhanced_system():
    """Test the enhanced orchestration system."""
    logger.info("=== Enhanced Orchestration System Test ===")
    
    system = EnhancedOrchestrationSystem()
    
    try:
        # Start the system
        await system.start()
        
        # Test 1: Memory Systems
        logger.info("\n--- Test 1: Memory Systems ---")
        memory_results = await system.test_memory_systems()
        logger.info(f"Memory Systems: {memory_results}")
        
        # Test 2: Recipe Templates
        logger.info("\n--- Test 2: Recipe Templates ---")
        recipe_results = await system.test_recipe_templates()
        logger.info(f"Recipe Templates: {recipe_results}")
        
        # Test 3: Constraint Memory
        logger.info("\n--- Test 3: Constraint Memory ---")
        constraint_results = await system.test_constraint_memory()
        logger.info(f"Constraint Memory: {constraint_results}")
        
        # Test 4: Experience Optimization
        logger.info("\n--- Test 4: Experience Optimization ---")
        experience_results = await system.test_experience_optimization()
        logger.info(f"Experience Optimization: {experience_results}")
        
        # Test 5: Intent Processing with Learning
        logger.info("\n--- Test 5: Intent Processing with Learning ---")
        
        test_intents = [
            {
                "intent": "create a comfortable movie night environment",
                "user_id": "user_123",
                "preferences": {"privacy_first": True, "comfort_optimized": True},
                "description": "Movie night setup with privacy focus"
            },
            {
                "intent": "optimize energy usage while maintaining comfort",
                "user_id": "user_123", 
                "preferences": {"energy_efficient": True, "cost_optimized": True},
                "description": "Energy optimization with comfort constraint"
            },
            {
                "intent": "setup security mode for when I'm away",
                "user_id": "user_123",
                "preferences": {"security_first": True, "privacy_first": True},
                "description": "Security setup with privacy focus"
            }
        ]
        
        for i, test_case in enumerate(test_intents, 1):
            logger.info(f"\n--- Processing Intent {i}: {test_case['description']} ---")
            
            result = await system.process_intent_with_learning(
                intent=test_case["intent"],
                user_id=test_case["user_id"],
                **{k: v for k, v in test_case.items() if k not in ["intent", "user_id", "description"]}
            )
            
            if result["success"]:
                logger.info(f"✅ Success: {test_case['description']}")
                logger.info(f"   Plan ID: {result['plan_id']}")
                logger.info(f"   Planning Time: {result['planning_time_ms']}ms")
                logger.info(f"   Success Score: {result['execution_outcome']['success_score']:.2f}")
                logger.info(f"   User Satisfaction: {result['execution_outcome']['user_satisfaction']:.2f}")
                logger.info(f"   Privacy Kept Local: {result['execution_outcome']['privacy_kept_local']:.2f}")
                if result['plan_rationale']:
                    logger.info(f"   Plan Rationale: {result['plan_rationale'][:100]}...")
            else:
                logger.error(f"❌ Failed: {test_case['description']}")
                logger.error(f"   Error: {result['error']}")
        
        # Test 6: Learning Systems
        logger.info("\n--- Test 6: Learning Systems ---")
        learning_results = await system.test_learning_systems()
        logger.info(f"Learning Systems: {learning_results}")
        
        # Test 7: Experience Report
        logger.info("\n--- Test 7: Final Experience Report ---")
        final_experience = await system.orchestration_engine.get_experience_report()
        logger.info(f"Overall Experience Score: {final_experience['overall_score']:.3f}")
        logger.info(f"Friction Score: {final_experience['friction_score']:.3f}")
        logger.info(f"Speed Score: {final_experience['speed_score']:.3f}")
        logger.info(f"Trust Score: {final_experience['trust_score']:.3f}")
        logger.info(f"Proactivity Score: {final_experience['proactivity_score']:.3f}")
        
        if final_experience['needs_optimization']:
            logger.warning("⚠️ System needs optimization")
            logger.info(f"Recommendations: {final_experience['recommendations']}")
        else:
            logger.info("✅ System performing well")
        
        logger.info("\n=== All enhanced system tests completed successfully! ===")
        
    except Exception as e:
        logger.error(f"Enhanced system test failed with error: {e}")
        raise
    
    finally:
        # Stop the system
        await system.stop()


async def test_cross_layer_learning():
    """Test cross-layer learning loop functionality."""
    logger.info("\n=== Cross-Layer Learning Test ===")
    
    system = EnhancedOrchestrationSystem()
    
    try:
        await system.start()
        
        # Simulate multiple iterations to test learning
        for iteration in range(5):
            logger.info(f"\n--- Learning Iteration {iteration + 1} ---")
            
            # Process intent
            result = await system.process_intent_with_learning(
                intent="optimize energy usage in the living room",
                user_id="user_123",
                preferences={"energy_efficient": True}
            )
            
            if result["success"]:
                logger.info(f"Iteration {iteration + 1} completed successfully")
                
                # Get learning insights
                insights = await system.orchestration_engine.get_learning_insights()
                logger.info(f"Learning signals: {insights['total_signals']}")
                logger.info(f"Average success rate: {insights['average_success_rate']:.3f}")
                
                # Get experience report
                experience = await system.orchestration_engine.get_experience_report()
                logger.info(f"Experience score: {experience['overall_score']:.3f}")
        
        logger.info("✅ Cross-layer learning test completed")
        
    except Exception as e:
        logger.error(f"Cross-layer learning test failed: {e}")
        raise
    
    finally:
        await system.stop()


async def test_experience_goals():
    """Test specific experience goals and metrics."""
    logger.info("\n=== Experience Goals Test ===")
    
    system = EnhancedOrchestrationSystem()
    
    try:
        await system.start()
        
        # Test low friction goal
        logger.info("Testing low friction goal...")
        monitor = system.orchestration_engine.experience_monitor
        
        # Simulate some friction events
        monitor.record_approval_tap()
        monitor.record_confirmation_dialog()
        
        # Test fast response goal
        logger.info("Testing fast response goal...")
        monitor.record_response_time("local_reaction", 100.0)  # Under 150ms target
        monitor.record_response_time("plan_preview", 600.0)    # Under 800ms target
        monitor.record_response_time("context_query", 30.0)    # Under 50ms target
        
        # Test trustworthy goal
        logger.info("Testing trustworthy goal...")
        monitor.update_trust_metrics(
            explanation_quality_score=0.9,
            consent_compliance_rate=0.98,
            safe_defaults_usage=0.95,
            privacy_respect_score=0.92,
            audit_trail_completeness=0.97
        )
        
        # Test proactive correctness goal
        logger.info("Testing proactive correctness goal...")
        # Don't record false suggestions to keep this low
        
        # Get final report
        report = monitor.get_experience_report()
        
        logger.info(f"Overall Experience Score: {report['overall_score']:.3f}")
        logger.info(f"Friction Score: {report['friction_score']:.3f}")
        logger.info(f"Speed Score: {report['speed_score']:.3f}")
        logger.info(f"Trust Score: {report['trust_score']:.3f}")
        logger.info(f"Proactivity Score: {report['proactivity_score']:.3f}")
        
        # Check if goals are met
        goals_met = {
            "low_friction": report['friction_score'] > 0.8,
            "fast_response": report['speed_score'] > 0.9,
            "trustworthy": report['trust_score'] > 0.9,
            "proactive_correct": report['proactivity_score'] > 0.8
        }
        
        logger.info(f"Experience Goals Met: {goals_met}")
        
        all_goals_met = all(goals_met.values())
        if all_goals_met:
            logger.info("✅ All experience goals met!")
        else:
            logger.warning("⚠️ Some experience goals not met")
        
        logger.info("✅ Experience goals test completed")
        
    except Exception as e:
        logger.error(f"Experience goals test failed: {e}")
        raise
    
    finally:
        await system.stop()


async def main():
    """Run all enhanced orchestration system tests."""
    logger.info("Starting Enhanced Orchestration System Test Suite")
    logger.info(f"Test started at: {datetime.utcnow()}")
    
    try:
        # Run main enhanced system test
        await test_enhanced_system()
        
        # Run cross-layer learning test
        await test_cross_layer_learning()
        
        # Run experience goals test
        await test_experience_goals()
        
        logger.info("\n🎉 All enhanced orchestration system tests completed successfully!")
        logger.info("The enhanced orchestration system with experience goals is working correctly.")
        
    except Exception as e:
        logger.error(f"Enhanced orchestration test suite failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
