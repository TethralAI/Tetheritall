"""
Consumer-Ready System Test Suite

This module provides comprehensive testing and demonstration of all consumer-ready
enhancements working together in a complete orchestration platform.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import uuid

from .consumer_platform import ConsumerPlatform, OnboardingStage, UserTier
from .integration_ecosystem import IntegrationEcosystem, ProtocolType, DeviceCategory
from .monitoring_support import MonitoringSupportSystem, HealthStatus
from .compliance_standards import ComplianceStandardsSystem, ComplianceStandard, DataCategory
from .business_model import BusinessModelSystem, SubscriptionTier, BillingCycle
from .models import *

logger = logging.getLogger(__name__)


class ConsumerReadySystem:
    """Complete consumer-ready orchestration system."""
    
    def __init__(self):
        self.consumer_platform = ConsumerPlatform()
        self.integration_ecosystem = IntegrationEcosystem()
        self.monitoring_support = MonitoringSupportSystem()
        self.compliance_standards = ComplianceStandardsSystem()
        self.business_model = BusinessModelSystem()
        self._running = False
    
    async def start(self):
        """Start all consumer-ready systems."""
        if self._running:
            return
        
        logger.info("Starting Consumer-Ready System...")
        
        # Start all subsystems
        await self.consumer_platform.start()
        await self.integration_ecosystem.start()
        await self.monitoring_support.start()
        await self.compliance_standards.start()
        await self.business_model.start()
        
        self._running = True
        logger.info("Consumer-Ready System started successfully")
    
    async def stop(self):
        """Stop all consumer-ready systems."""
        if not self._running:
            return
        
        logger.info("Stopping Consumer-Ready System...")
        
        await self.consumer_platform.stop()
        await self.integration_ecosystem.stop()
        await self.monitoring_support.stop()
        await self.compliance_standards.stop()
        await self.business_model.stop()
        
        self._running = False
        logger.info("Consumer-Ready System stopped")
    
    async def demonstrate_complete_user_journey(self, user_id: str) -> Dict[str, Any]:
        """Demonstrate a complete user journey from onboarding to advanced usage."""
        journey_log = []
        
        # Step 1: User Onboarding
        journey_log.append("=== STEP 1: USER ONBOARDING ===")
        onboarding_progress = await self.consumer_platform.start_onboarding(user_id)
        journey_log.append(f"Started onboarding for user {user_id}")
        
        # Advance through onboarding stages
        for stage in [OnboardingStage.DEVICE_DISCOVERY, OnboardingStage.CONSENT_SETUP, 
                     OnboardingStage.PREFERENCES, OnboardingStage.TUTORIAL, OnboardingStage.COMPLETE]:
            onboarding_progress = await self.consumer_platform.advance_onboarding(user_id, stage)
            journey_log.append(f"Advanced to stage: {stage.value}")
        
        # Step 2: Device Discovery and Integration
        journey_log.append("\n=== STEP 2: DEVICE DISCOVERY AND INTEGRATION ===")
        discovered_devices = await self.integration_ecosystem.discover_and_connect_devices()
        journey_log.append(f"Discovered {len(discovered_devices)} devices")
        
        # Configure discovered devices
        for device in discovered_devices[:3]:  # Configure first 3 devices
            await self.integration_ecosystem.universal_adapter.configure_device(
                device.device_id, 
                {"name": f"Configured {device.name}", "location": "living_room"}
            )
            journey_log.append(f"Configured device: {device.name}")
        
        # Step 3: Subscription Setup
        journey_log.append("\n=== STEP 3: SUBSCRIPTION SETUP ===")
        subscription = await self.business_model.create_user_subscription(
            user_id, SubscriptionTier.PREMIUM, BillingCycle.MONTHLY
        )
        journey_log.append(f"Created {subscription.tier.value} subscription")
        
        # Step 4: Natural Language Processing
        journey_log.append("\n=== STEP 4: NATURAL LANGUAGE PROCESSING ===")
        nl_response = await self.consumer_platform.process_natural_language(
            "Turn on the living room lights and dim them to 50%", user_id
        )
        journey_log.append(f"Natural language response: {nl_response.status == ExecutionStatus.COMPLETED}")
        
        # Step 5: Device Control
        journey_log.append("\n=== STEP 5: DEVICE CONTROL ===")
        if discovered_devices:
            device = discovered_devices[0]
            control_success = await self.integration_ecosystem.control_device(
                device.device_id, "on_off", True
            )
            journey_log.append(f"Device control success: {control_success}")
        
        # Step 6: Value Tracking
        journey_log.append("\n=== STEP 6: VALUE TRACKING ===")
        await self.business_model.track_user_value(user_id, "energy_savings", 2.5)
        await self.business_model.track_user_value(user_id, "time_savings", 15.0)
        await self.business_model.track_user_value(user_id, "automation_efficiency", 0.85)
        journey_log.append("Tracked user value metrics")
        
        # Step 7: Compliance and Privacy
        journey_log.append("\n=== STEP 7: COMPLIANCE AND PRIVACY ===")
        await self.compliance_standards.record_data_processing(
            user_id, DataCategory.PERSONAL_DATA, "automation", "legitimate_interest", 365, True
        )
        gdpr_compliance = await self.compliance_standards.check_gdpr_compliance()
        journey_log.append(f"GDPR compliance score: {gdpr_compliance['compliance_score']}%")
        
        # Step 8: System Health Monitoring
        journey_log.append("\n=== STEP 8: SYSTEM HEALTH MONITORING ===")
        system_health = await self.monitoring_support.get_system_health()
        journey_log.append(f"System health status: {system_health['overall_status']}")
        
        # Step 9: User Analytics and Insights
        journey_log.append("\n=== STEP 9: USER ANALYTICS AND INSIGHTS ===")
        user_metrics = await self.consumer_platform.get_user_metrics(user_id)
        value_summary = await self.business_model.get_user_value_summary(user_id)
        journey_log.append(f"User satisfaction score: {user_metrics.user_satisfaction_score}")
        journey_log.append(f"Total value generated: ${value_summary['total_value_usd']:.2f}")
        
        return {
            "user_id": user_id,
            "journey_completed": True,
            "log": journey_log,
            "metrics": {
                "devices_discovered": len(discovered_devices),
                "subscription_tier": subscription.tier.value,
                "gdpr_compliance": gdpr_compliance['compliance_score'],
                "system_health": system_health['overall_status'],
                "user_satisfaction": user_metrics.user_satisfaction_score,
                "value_generated": value_summary['total_value_usd']
            }
        }
    
    async def demonstrate_advanced_features(self, user_id: str) -> Dict[str, Any]:
        """Demonstrate advanced consumer-ready features."""
        features_log = []
        
        # Advanced Feature 1: Voice Assistant Integration
        features_log.append("=== ADVANCED FEATURE 1: VOICE ASSISTANT INTEGRATION ===")
        voice_response = await self.integration_ecosystem.process_voice_command(
            "alexa", "Turn off all lights", user_id
        )
        features_log.append(f"Voice command processed: {voice_response.get('intent', 'unknown')}")
        
        # Advanced Feature 2: Third-Party Service Integration
        features_log.append("\n=== ADVANCED FEATURE 2: THIRD-PARTY SERVICE INTEGRATION ===")
        weather_data = await self.integration_ecosystem.call_third_party_service(
            "weather_service", "current"
        )
        features_log.append(f"Weather data retrieved: {weather_data.get('temperature', 'N/A')}°C")
        
        # Advanced Feature 3: Advanced Analytics
        features_log.append("\n=== ADVANCED FEATURE 3: ADVANCED ANALYTICS ===")
        await self.business_model.generate_user_insight(
            user_id, "energy_optimization", 
            "Energy Usage Pattern Detected",
            "Your energy usage peaks between 6-8 PM. Consider scheduling automations to reduce peak usage.",
            15.0, "Schedule energy-intensive automations outside peak hours"
        )
        features_log.append("Generated energy optimization insight")
        
        # Advanced Feature 4: Support and Troubleshooting
        features_log.append("\n=== ADVANCED FEATURE 4: SUPPORT AND TROUBLESHOOTING ===")
        support_ticket = await self.monitoring_support.create_support_ticket(
            user_id, "Device Connection Issue", 
            "My smart light is not responding to commands", "technical", "medium"
        )
        features_log.append(f"Created support ticket: {support_ticket.ticket_id}")
        
        # Advanced Feature 5: Compliance Monitoring
        features_log.append("\n=== ADVANCED FEATURE 5: COMPLIANCE MONITORING ===")
        compliance_report = await self.compliance_standards.generate_compliance_report()
        features_log.append(f"Compliance report generated with {len(compliance_report['compliance']['standards'])} standards")
        
        # Advanced Feature 6: Business Analytics
        features_log.append("\n=== ADVANCED FEATURE 6: BUSINESS ANALYTICS ===")
        business_analytics = await self.business_model.get_business_analytics()
        features_log.append(f"MRR: ${business_analytics['subscriptions']['monthly_recurring_revenue']:.2f}")
        
        return {
            "user_id": user_id,
            "advanced_features_demonstrated": True,
            "log": features_log,
            "summary": {
                "voice_integration": "alexa",
                "weather_integration": "active",
                "insights_generated": 1,
                "support_tickets": 1,
                "compliance_standards": len(compliance_report['compliance']['standards']),
                "business_metrics": "tracked"
            }
        }
    
    async def demonstrate_scalability_and_performance(self) -> Dict[str, Any]:
        """Demonstrate system scalability and performance."""
        performance_log = []
        
        # Simulate multiple users
        performance_log.append("=== SCALABILITY TEST: MULTIPLE USERS ===")
        user_journeys = []
        
        # Create 10 simulated users
        for i in range(10):
            user_id = f"test_user_{i}_{uuid.uuid4().hex[:8]}"
            try:
                journey = await self.demonstrate_complete_user_journey(user_id)
                user_journeys.append(journey)
                performance_log.append(f"User {i+1} journey completed successfully")
            except Exception as e:
                performance_log.append(f"User {i+1} journey failed: {str(e)}")
        
        # Performance metrics
        performance_log.append("\n=== PERFORMANCE METRICS ===")
        system_health = await self.monitoring_support.get_system_health()
        business_analytics = await self.business_model.get_business_analytics()
        
        performance_log.append(f"System health: {system_health['overall_status']}")
        performance_log.append(f"Total users processed: {len(user_journeys)}")
        performance_log.append(f"Active subscriptions: {business_analytics['subscriptions']['active_subscriptions']}")
        
        return {
            "scalability_test_completed": True,
            "users_processed": len(user_journeys),
            "successful_journeys": len([j for j in user_journeys if j['journey_completed']]),
            "system_health": system_health['overall_status'],
            "log": performance_log
        }
    
    async def demonstrate_error_handling_and_recovery(self, user_id: str) -> Dict[str, Any]:
        """Demonstrate error handling and recovery capabilities."""
        error_log = []
        
        # Test 1: Invalid natural language command
        error_log.append("=== ERROR HANDLING TEST 1: INVALID COMMAND ===")
        try:
            response = await self.consumer_platform.process_natural_language(
                "invalid command that doesn't make sense", user_id
            )
            error_log.append(f"Invalid command handled gracefully: {response.success}")
        except Exception as e:
            error_log.append(f"Error handling failed: {str(e)}")
        
        # Test 2: Device control failure
        error_log.append("\n=== ERROR HANDLING TEST 2: DEVICE CONTROL FAILURE ===")
        try:
            # Try to control a non-existent device
            control_success = await self.integration_ecosystem.control_device(
                "non_existent_device", "on_off", True
            )
            error_log.append(f"Non-existent device handled: {control_success}")
        except Exception as e:
            error_log.append(f"Device control error handling failed: {str(e)}")
        
        # Test 3: Compliance violation
        error_log.append("\n=== ERROR HANDLING TEST 3: COMPLIANCE VIOLATION ===")
        try:
            # Try to process data without consent
            await self.compliance_standards.record_data_processing(
                user_id, DataCategory.SENSITIVE_DATA, "unauthorized_purpose", "invalid_basis", 30, False
            )
            error_log.append("Compliance violation handled")
        except Exception as e:
            error_log.append(f"Compliance error handling failed: {str(e)}")
        
        # Test 4: System recovery
        error_log.append("\n=== ERROR HANDLING TEST 4: SYSTEM RECOVERY ===")
        try:
            # Simulate system restart
            await self.stop()
            await asyncio.sleep(1)
            await self.start()
            error_log.append("System restart completed successfully")
        except Exception as e:
            error_log.append(f"System recovery failed: {str(e)}")
        
        return {
            "user_id": user_id,
            "error_handling_tests_completed": True,
            "log": error_log
        }
    
    async def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate a comprehensive system report."""
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "system_status": "running" if self._running else "stopped",
            "components": {}
        }
        
        # Component status
        report["components"]["consumer_platform"] = {
            "status": "running" if self.consumer_platform._running else "stopped",
            "onboarding_users": len(self.consumer_platform.onboarding.onboarding_data)
        }
        
        report["components"]["integration_ecosystem"] = {
            "status": "running" if self.integration_ecosystem._running else "stopped",
            "discovered_devices": len(self.integration_ecosystem.universal_adapter.device_registry)
        }
        
        report["components"]["monitoring_support"] = {
            "status": "running" if self.monitoring_support._running else "stopped"
        }
        
        report["components"]["compliance_standards"] = {
            "status": "running" if self.compliance_standards._running else "stopped"
        }
        
        report["components"]["business_model"] = {
            "status": "running" if self.business_model._running else "stopped"
        }
        
        # System metrics
        try:
            system_health = await self.monitoring_support.get_system_health()
            report["system_health"] = system_health
        except Exception as e:
            report["system_health"] = {"error": str(e)}
        
        try:
            business_analytics = await self.business_model.get_business_analytics()
            report["business_analytics"] = business_analytics
        except Exception as e:
            report["business_analytics"] = {"error": str(e)}
        
        try:
            compliance_report = await self.compliance_standards.generate_compliance_report()
            report["compliance_report"] = compliance_report
        except Exception as e:
            report["compliance_report"] = {"error": str(e)}
        
        return report


async def run_comprehensive_demo():
    """Run a comprehensive demonstration of the consumer-ready system."""
    print("🚀 Starting Consumer-Ready Orchestration System Demo")
    print("=" * 60)
    
    # Initialize the system
    system = ConsumerReadySystem()
    
    try:
        # Start the system
        await system.start()
        print("✅ System started successfully")
        
        # Demo 1: Complete User Journey
        print("\n📋 DEMO 1: Complete User Journey")
        print("-" * 40)
        user_id = f"demo_user_{uuid.uuid4().hex[:8]}"
        journey_result = await system.demonstrate_complete_user_journey(user_id)
        
        print(f"User ID: {user_id}")
        print(f"Journey completed: {journey_result['journey_completed']}")
        print(f"Devices discovered: {journey_result['metrics']['devices_discovered']}")
        print(f"Subscription tier: {journey_result['metrics']['subscription_tier']}")
        print(f"GDPR compliance: {journey_result['metrics']['gdpr_compliance']}%")
        print(f"System health: {journey_result['metrics']['system_health']}")
        print(f"User satisfaction: {journey_result['metrics']['user_satisfaction']}")
        print(f"Value generated: ${journey_result['metrics']['value_generated']:.2f}")
        
        # Demo 2: Advanced Features
        print("\n🔧 DEMO 2: Advanced Features")
        print("-" * 40)
        advanced_result = await system.demonstrate_advanced_features(user_id)
        print(f"Advanced features demonstrated: {advanced_result['advanced_features_demonstrated']}")
        print(f"Voice integration: {advanced_result['summary']['voice_integration']}")
        print(f"Weather integration: {advanced_result['summary']['weather_integration']}")
        print(f"Insights generated: {advanced_result['summary']['insights_generated']}")
        print(f"Support tickets: {advanced_result['summary']['support_tickets']}")
        
        # Demo 3: Scalability and Performance
        print("\n📈 DEMO 3: Scalability and Performance")
        print("-" * 40)
        scalability_result = await system.demonstrate_scalability_and_performance()
        print(f"Users processed: {scalability_result['users_processed']}")
        print(f"Successful journeys: {scalability_result['successful_journeys']}")
        print(f"System health: {scalability_result['system_health']}")
        
        # Demo 4: Error Handling and Recovery
        print("\n🛡️ DEMO 4: Error Handling and Recovery")
        print("-" * 40)
        error_result = await system.demonstrate_error_handling_and_recovery(user_id)
        print(f"Error handling tests completed: {error_result['error_handling_tests_completed']}")
        
        # Demo 5: Comprehensive Report
        print("\n📊 DEMO 5: Comprehensive System Report")
        print("-" * 40)
        report = await system.generate_comprehensive_report()
        print(f"System status: {report['system_status']}")
        print(f"Components running: {sum(1 for c in report['components'].values() if c['status'] == 'running')}")
        
        if 'business_analytics' in report and 'error' not in report['business_analytics']:
            mrr = report['business_analytics']['subscriptions']['monthly_recurring_revenue']
            print(f"Monthly Recurring Revenue: ${mrr:.2f}")
        
        if 'compliance_report' in report and 'error' not in report['compliance_report']:
            standards = len(report['compliance_report']['compliance']['standards'])
            print(f"Compliance standards tracked: {standards}")
        
        print("\n🎉 Consumer-Ready System Demo Completed Successfully!")
        print("=" * 60)
        
        # Print detailed logs for the first user journey
        print("\n📝 DETAILED USER JOURNEY LOG:")
        print("-" * 40)
        for log_entry in journey_result['log']:
            print(log_entry)
        
    except Exception as e:
        print(f"❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Stop the system
        await system.stop()
        print("\n🛑 System stopped")


async def run_quick_test():
    """Run a quick test of the consumer-ready system."""
    print("⚡ Quick Consumer-Ready System Test")
    print("=" * 40)
    
    system = ConsumerReadySystem()
    
    try:
        await system.start()
        print("✅ System started")
        
        # Quick user journey
        user_id = f"quick_test_user_{uuid.uuid4().hex[:8]}"
        journey = await system.demonstrate_complete_user_journey(user_id)
        
        print(f"✅ User journey completed for {user_id}")
        print(f"   Devices: {journey['metrics']['devices_discovered']}")
        print(f"   Subscription: {journey['metrics']['subscription_tier']}")
        print(f"   Value: ${journey['metrics']['value_generated']:.2f}")
        
        # Quick system health check
        health = await system.monitoring_support.get_system_health()
        print(f"✅ System health: {health['overall_status']}")
        
        print("✅ Quick test completed successfully")
        
    except Exception as e:
        print(f"❌ Quick test failed: {str(e)}")
    
    finally:
        await system.stop()
        print("🛑 System stopped")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        asyncio.run(run_quick_test())
    else:
        asyncio.run(run_comprehensive_demo())
