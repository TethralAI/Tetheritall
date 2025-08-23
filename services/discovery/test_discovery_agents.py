"""
Test script for the refined IoT discovery agents.

This script demonstrates the functionality of the Resource Lookup Agent (RLA)
and Connection Opportunity Agent (COA) through the Unified Discovery Coordinator.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from resource_lookup_agent import (
    ResourceLookupAgent, DeviceHint, AccountHint, EnvironmentContext, 
    UserPreferences, PrivacyTier
)
from connection_opportunity_agent import (
    ConnectionOpportunityAgent, NetworkDiscovery, UserConstraints,
    DiscoveryType, CapabilityType
)
from unified_discovery_coordinator import (
    UnifiedDiscoveryCoordinator, CoordinatorConfig
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_resource_lookup_agent():
    """Test the Resource Lookup Agent (RLA)."""
    logger.info("=== Testing Resource Lookup Agent ===")
    
    # Initialize RLA
    rla = ResourceLookupAgent()
    
    # Test device hint processing
    device_hint = DeviceHint(
        brand="Philips",
        model="Hue Bulb",
        qr_code="matter:123456789",
        ble_advertisement={"name": "Philips Hue", "services": ["1800", "1801"]}
    )
    
    account_hint = AccountHint(
        provider="philips",
        region="US",
        auth_capability="oauth"
    )
    
    env_context = EnvironmentContext(
        ssid="HomeNetwork",
        band="5GHz",
        bluetooth_available=True,
        wifi_6_available=True,
        matter_commissioning_available=True
    )
    
    user_prefs = UserPreferences(
        privacy_tier=PrivacyTier.STANDARD,
        approval_threshold="manual",
        quiet_hours=(22, 7),
        noise_sensitivity=False
    )
    
    # Process device hint
    result = await rla.process_device_hint(
        device_hint, account_hint, env_context, user_prefs
    )
    
    logger.info("RLA Results:")
    logger.info(f"Entity Profile: {result['entity_profile']}")
    logger.info(f"Connection Flow: {len(result['connection_flow'].steps)} steps")
    logger.info(f"Scores: {result['scores']}")
    logger.info(f"Recommendations: {result['recommendations']}")
    
    # Test troubleshooting
    error_message = "Connection timeout - device not responding"
    context = {"network_scan_failed": True, "auth_attempted": False}
    
    troubleshoot_result = await rla.troubleshoot_failure(error_message, context)
    logger.info(f"Troubleshoot Result: {troubleshoot_result}")
    
    return result


async def test_connection_opportunity_agent():
    """Test the Connection Opportunity Agent (COA)."""
    logger.info("=== Testing Connection Opportunity Agent ===")
    
    # Initialize COA
    coa = ConnectionOpportunityAgent()
    
    # Create mock discoveries
    discoveries = [
        NetworkDiscovery(
            discovery_id="discovery_1",
            discovery_type=DiscoveryType.BLE,
            device_info={
                "name": "Philips Hue Bulb",
                "manufacturer": "Philips",
                "model": "LCT001",
                "port": 80
            },
            protocol_candidates=["bluetooth", "zigbee"],
            confidence_score=0.9,
            timestamp=datetime.now(),
            location_hint="living_room"
        ),
        NetworkDiscovery(
            discovery_id="discovery_2",
            discovery_type=DiscoveryType.MDNS,
            device_info={
                "name": "IKEA Tradfri Gateway",
                "manufacturer": "IKEA",
                "model": "E1526",
                "port": 80
            },
            protocol_candidates=["zigbee", "thread"],
            confidence_score=0.8,
            timestamp=datetime.now(),
            location_hint="office"
        ),
        NetworkDiscovery(
            discovery_id="discovery_3",
            discovery_type=DiscoveryType.SSDP,
            device_info={
                "name": "Samsung SmartThings Hub",
                "manufacturer": "Samsung",
                "model": "GP-U999SJVLAAA",
                "port": 8080
            },
            protocol_candidates=["wifi", "zigbee", "thread"],
            confidence_score=0.7,
            timestamp=datetime.now(),
            location_hint="basement"
        )
    ]
    
    user_constraints = UserConstraints(
        privacy_tier="standard",
        time_budget_minutes=30,
        noise_sensitivity=False,
        quiet_hours=(22, 7),
        preferred_protocols=["matter", "thread"]
    )
    
    env_context = {
        "bluetooth_available": True,
        "wifi_6_available": True,
        "thread_available": True,
        "network_quality": "good"
    }
    
    # Process discoveries
    result = await coa.process_discoveries(discoveries, user_constraints, env_context)
    
    logger.info("COA Results:")
    logger.info(f"Discoveries Processed: {result['discoveries_processed']}")
    logger.info(f"Opportunities Generated: {result['opportunities_generated']}")
    logger.info(f"Selected Opportunities: {len(result['selected_opportunities'])}")
    logger.info(f"Coverage Gaps: {len(result['coverage_gaps'])}")
    logger.info(f"Recommendations: {len(result['recommendations'])}")
    
    # Show selected opportunities
    for i, opp in enumerate(result['selected_opportunities']):
        logger.info(f"Opportunity {i+1}:")
        logger.info(f"  Device Type: {opp.device_type}")
        logger.info(f"  Value Score: {opp.value_score:.2f}")
        logger.info(f"  Friction Score: {opp.friction_score:.2f}")
        logger.info(f"  Privacy Cost: {opp.privacy_cost:.2f}")
        logger.info(f"  Rationale: {opp.rationale}")
    
    # Test coverage summary
    coverage_summary = await coa.get_coverage_summary()
    logger.info(f"Coverage Summary: {coverage_summary}")
    
    return result


async def test_unified_coordinator():
    """Test the Unified Discovery Coordinator."""
    logger.info("=== Testing Unified Discovery Coordinator ===")
    
    # Initialize coordinator
    config = CoordinatorConfig(
        learning_enabled=True,
        privacy_by_default=True,
        gdpr_compliant=True
    )
    
    coordinator = UnifiedDiscoveryCoordinator(config)
    await coordinator.start()
    
    # Test first-time setup
    logger.info("Starting first-time setup workflow...")
    setup_workflow_id = await coordinator.start_first_time_setup(
        user_id="test_user_1",
        session_id="session_1",
        initial_preferences={
            "privacy_tier": "standard",
            "quiet_hours": [22, 7]
        }
    )
    
    # Wait for workflow to complete
    await asyncio.sleep(2)
    
    setup_status = await coordinator.get_workflow_status(setup_workflow_id)
    logger.info(f"First-time setup status: {setup_status['current_state']}")
    
    # Test device addition
    logger.info("Starting device addition workflow...")
    device_hint = DeviceHint(
        brand="Philips",
        model="Hue Bulb",
        qr_code="matter:123456789"
    )
    
    device_workflow_id = await coordinator.add_device(
        user_id="test_user_1",
        session_id="session_1",
        device_hint=device_hint
    )
    
    # Wait for workflow to complete
    await asyncio.sleep(2)
    
    device_status = await coordinator.get_workflow_status(device_workflow_id)
    logger.info(f"Device addition status: {device_status['current_state']}")
    
    # Test opportunity discovery
    logger.info("Starting opportunity discovery workflow...")
    user_constraints = UserConstraints(
        privacy_tier="standard",
        time_budget_minutes=15
    )
    
    env_context = {
        "bluetooth_available": True,
        "wifi_6_available": True
    }
    
    opp_workflow_id = await coordinator.start_opportunity_discovery(
        user_id="test_user_1",
        session_id="session_1",
        user_constraints=user_constraints,
        env_context=env_context
    )
    
    # Wait for workflow to complete
    await asyncio.sleep(2)
    
    opp_status = await coordinator.get_workflow_status(opp_workflow_id)
    logger.info(f"Opportunity discovery status: {opp_status['current_state']}")
    
    # Test troubleshooting
    logger.info("Starting troubleshooting workflow...")
    troubleshoot_workflow_id = await coordinator.troubleshoot_connection(
        user_id="test_user_1",
        session_id="session_1",
        error_message="Device not found during scan",
        context={"network_scan_failed": True}
    )
    
    # Wait for workflow to complete
    await asyncio.sleep(2)
    
    troubleshoot_status = await coordinator.get_workflow_status(troubleshoot_workflow_id)
    logger.info(f"Troubleshooting status: {troubleshoot_status['current_state']}")
    
    # Get user summary
    user_summary = await coordinator.get_user_summary("test_user_1")
    logger.info(f"User Summary: {user_summary}")
    
    # Record some user actions
    await coordinator.record_user_action(device_workflow_id, "accept", {"feedback": "Great experience!"})
    await coordinator.record_user_action(opp_workflow_id, "complete", {"time_taken": 120})
    
    # Stop coordinator
    await coordinator.stop()
    
    return {
        "setup_workflow": setup_status,
        "device_workflow": device_status,
        "opportunity_workflow": opp_status,
        "troubleshoot_workflow": troubleshoot_status,
        "user_summary": user_summary
    }


async def test_api_interface():
    """Test the API interface (if available)."""
    logger.info("=== Testing API Interface ===")
    
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            response = await client.get("http://localhost:8000/health")
            logger.info(f"Health check: {response.json()}")
            
            # Test metrics endpoint
            response = await client.get("http://localhost:8000/metrics")
            logger.info(f"Metrics: {response.json()}")
            
            # Test examples endpoint
            response = await client.get("http://localhost:8000/examples")
            logger.info(f"Examples: {response.json()}")
            
    except ImportError:
        logger.warning("httpx not available, skipping API tests")
    except Exception as e:
        logger.warning(f"API tests failed: {e}")


async def main():
    """Run all tests."""
    logger.info("Starting IoT Discovery Agents Test Suite")
    logger.info("=" * 50)
    
    try:
        # Test individual agents
        rla_result = await test_resource_lookup_agent()
        logger.info("✓ Resource Lookup Agent test completed")
        
        coa_result = await test_connection_opportunity_agent()
        logger.info("✓ Connection Opportunity Agent test completed")
        
        # Test unified coordinator
        coordinator_result = await test_unified_coordinator()
        logger.info("✓ Unified Discovery Coordinator test completed")
        
        # Test API interface (if server is running)
        await test_api_interface()
        logger.info("✓ API Interface test completed")
        
        logger.info("=" * 50)
        logger.info("All tests completed successfully!")
        
        # Print summary
        logger.info("\nTest Summary:")
        logger.info(f"- RLA processed device: {rla_result['entity_profile'].canonical_device_id}")
        logger.info(f"- COA found opportunities: {coa_result['opportunities_generated']}")
        logger.info(f"- Coordinator workflows: {len(coordinator_result)}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    # Run the test suite
    asyncio.run(main())
