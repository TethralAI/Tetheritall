# IoT Discovery Agents - Refined ML-Focused Architecture

This directory contains the refined IoT discovery agents that implement a granular, ML-focused approach to device discovery and connection. The system is designed to maximize user success while minimizing effort and respecting privacy preferences.

## Architecture Overview

The system consists of two main agents working in coordination:

### 1. Resource Lookup Agent (RLA)
**Goal**: Get the user from "I own X" to "X is ready to connect" with the fewest steps and highest success rate.

**Core Capabilities**:
- **Entity Linking & Normalization**: Converts device hints into canonical device profiles
- **Documentation RAG**: Retrieves and distills actionable steps from manuals and community fixes
- **Flow Planning**: Creates personalized connection workflows based on environment and preferences
- **Troubleshooting**: Classifies errors and provides targeted fixes
- **Consent Reasoning**: Determines minimal required scopes with privacy explanations

### 2. Connection Opportunity Agent (COA)
**Goal**: Maximize connected capability coverage and routine flexibility quickly, with low user effort and high privacy.

**Core Capabilities**:
- **Discovery Classification**: ML-powered device type classification from network discoveries
- **Opportunity Value Estimation**: Submodular coverage estimation for routine flexibility
- **Friction Forecasting**: Predicts connection steps, time, and success probability
- **Sequencing Policy**: Contextual bandit for optimal opportunity ordering
- **Coverage Gap Analysis**: Identifies missing capabilities and their routine impact

## Key Features

### Privacy-First Design
- **GDPR Compliant**: All operations respect user privacy preferences
- **Local-First**: Discovery and processing happen on-device when possible
- **Consent Management**: Granular scope control with least-privilege alternatives
- **Audit Logging**: Complete privacy event tracking

### ML-Powered Intelligence
- **Entity Linking**: Normalizes device brands and models across variations
- **Documentation RAG**: Semantic search over manuals and community knowledge
- **Error Classification**: Multi-label classification for targeted troubleshooting
- **Opportunity Scoring**: Submodular optimization for capability coverage
- **Friction Prediction**: Learned models for connection effort estimation

### Context-Aware Operation
- **Environment Assessment**: Network, protocol, and device capability detection
- **User Preference Learning**: Adapts to individual user patterns and constraints
- **Quiet Hours**: Respects user-defined quiet periods
- **Noise Sensitivity**: Adjusts discovery methods based on user preferences

## File Structure

```
services/discovery/
├── resource_lookup_agent.py      # RLA implementation
├── connection_opportunity_agent.py # COA implementation
├── unified_discovery_coordinator.py # Workflow coordination
├── api_interface.py              # REST API interface
├── agent.py                      # Legacy discovery agent
└── README.md                     # This file
```

## Quick Start

### 1. Basic Usage

```python
from services.discovery.unified_discovery_coordinator import (
    UnifiedDiscoveryCoordinator, CoordinatorConfig
)
from services.discovery.resource_lookup_agent import DeviceHint

# Initialize coordinator
config = CoordinatorConfig(
    learning_enabled=True,
    privacy_by_default=True,
    gdpr_compliant=True
)
coordinator = UnifiedDiscoveryCoordinator(config)
await coordinator.start()

# Add a device
device_hint = DeviceHint(
    brand="Philips",
    model="Hue Bulb",
    qr_code="matter:123456789"
)

workflow_id = await coordinator.add_device(
    user_id="user123",
    session_id="session456",
    device_hint=device_hint
)

# Check status
status = await coordinator.get_workflow_status(workflow_id)
print(f"Workflow status: {status['current_state']}")
```

### 2. API Usage

Start the API server:

```bash
cd services/discovery
python api_interface.py
```

Example API calls:

```bash
# First-time setup
curl -X POST "http://localhost:8000/workflows/first-time-setup" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "session_id": "session456",
    "initial_preferences": {
      "privacy_tier": "standard",
      "quiet_hours": [22, 7]
    }
  }'

# Add device
curl -X POST "http://localhost:8000/workflows/device-addition" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "session_id": "session456",
    "device_hint": {
      "brand": "Philips",
      "model": "Hue Bulb",
      "qr_code": "matter:123456789"
    }
  }'

# Check workflow status
curl "http://localhost:8000/workflows/{workflow_id}/status"
```

## Detailed Agent Specifications

### Resource Lookup Agent (RLA)

#### Triggers
- First-run onboarding
- User declares or scans a device/brand
- Failed connection flow requiring troubleshooting

#### Inputs
- **Device Hints**: brand, model, QR, MAC, BLE advert, Matter code
- **Account Hints**: provider, region, auth capability
- **Environment**: SSID, band, DHCP, NAT type, IPv6, Thread border router
- **User Preferences**: privacy tier, approval thresholds, quiet hours

#### Core Models

**Entity Linker**
```python
# Normalizes device hints into canonical profiles
entity_profile = entity_linker.normalize_entity(device_hint)
# Returns: canonical_device_id, brand_normalized, capability_class, protocols
```

**Documentation RAG**
```python
# Extracts actionable steps from documentation
steps = documentation_rag.extract_steps("how to connect Philips Hue bulb")
# Returns: step list with relevance scores and sources
```

**Flow Planner**
```python
# Creates personalized connection workflows
flow = flow_planner.plan_flow(entity_profile, env_context, user_prefs)
# Returns: step-by-step flow with effort, privacy, and success scores
```

**Troubleshoot Classifier**
```python
# Classifies errors and provides fixes
causes = troubleshoot_classifier.classify_error(error_message, context)
fixes = troubleshoot_classifier.get_fixes(error_type)
# Returns: ranked error causes and targeted fixes
```

#### Outputs
- Step-by-step connection checklist
- Consent scope requirements with privacy notes
- Effort, readiness, and success probability scores
- Alternative paths for failed prerequisites

### Connection Opportunity Agent (COA)

#### Triggers
- After first successful connection
- Context changes suggesting new opportunities
- User opt-in for account linking sweeps
- Scheduled discovery scans

#### Inputs
- **Network Discoveries**: mDNS, SSDP, BLE, Thread, Zigbee, Wi-Fi beacons
- **User Constraints**: privacy tier, time budget, noise sensitivity
- **Environment Context**: network health, protocol availability
- **Current Coverage**: existing device capabilities

#### Core Models

**Discovery Classifier**
```python
# Classifies discovered devices using ML
device_type, confidence = discovery_classifier.classify_device(discovery)
# Returns: device type and classification confidence
```

**Opportunity Value Estimator**
```python
# Estimates marginal value of connecting devices
value = value_estimator.estimate_value(opportunity, current_coverage)
# Returns: capability coverage gain and routine flexibility score
```

**Friction Forecaster**
```python
# Predicts connection effort and success probability
friction = friction_forecaster.forecast_friction(opportunity, env_context)
# Returns: steps, time, success probability, friction score
```

**Sequencing Policy**
```python
# Selects optimal opportunity batch
selected = sequencing_policy.select_opportunities(opportunities, constraints)
# Returns: ranked opportunities respecting diversity and constraints
```

#### Outputs
- Ranked connection opportunities with value explanations
- Coverage gap analysis and recommendations
- Next scan scheduling suggestions
- Privacy and effort estimates

## Privacy and Security

### GDPR Compliance
- **Data Minimization**: Only collects necessary information
- **Consent Management**: Granular scope control with explanations
- **Right to Deletion**: Complete data removal capabilities
- **Audit Logging**: All privacy events are logged and accessible

### Privacy Tiers
- **Minimal**: Local-only operation, no cloud data
- **Standard**: Basic cloud features with user control
- **Enhanced**: Full cloud integration with advanced features

### Security Features
- **Edge-First Processing**: Sensitive operations happen locally
- **Encrypted Communication**: All network traffic is encrypted
- **Scope Validation**: Runtime verification of consent scopes
- **Intrusion Prevention**: Safe discovery methods that don't modify devices

## Learning and Adaptation

### User Preference Learning
- **Action Tracking**: Records user decisions and outcomes
- **Pattern Recognition**: Learns user preferences over time
- **Personalization**: Adapts recommendations to individual users
- **Feedback Integration**: Incorporates user feedback for improvement

### Model Training
- **Offline Training**: Models trained on aggregated, anonymized data
- **Federated Learning**: Distributed training without data sharing
- **A/B Testing**: Continuous experimentation with recommendation policies
- **Performance Monitoring**: Tracks success rates and user satisfaction

## Performance Metrics

### RLA KPIs
- **First-attempt success rate**: Target >85%
- **Median time to first device connection**: Target <5 minutes
- **Steps per successful connection**: Target <8 steps
- **Consent minimized score**: Target >0.8 (80% of connections use minimal scopes)
- **Troubleshoot resolution rate**: Target >90% without human support

### COA KPIs
- **Capability coverage increase**: Target >40% within first week
- **Routine flexibility score growth**: Target >50% per household
- **Suggestion acceptance rate**: Target >60%
- **Average consent cost per opportunity**: Target <0.3
- **Time to first delightful routine**: Target <24 hours

## Integration Examples

### Mobile App Integration
```python
# Initialize discovery system
coordinator = UnifiedDiscoveryCoordinator()

# Handle device scan
async def on_device_scanned(qr_code: str):
    device_hint = DeviceHint(qr_code=qr_code)
    workflow_id = await coordinator.add_device(
        user_id=current_user.id,
        session_id=session.id,
        device_hint=device_hint
    )
    
    # Subscribe to workflow updates
    status_queue = coordinator.subscribe_state()
    async for update in status_queue:
        if update["workflow_id"] == workflow_id:
            update_ui(update)

# Handle user actions
async def on_user_action(workflow_id: str, action: str):
    await coordinator.record_user_action(workflow_id, action)
```

### Smart Home Hub Integration
```python
# Periodic opportunity discovery
async def discover_opportunities():
    user_constraints = UserConstraints(
        privacy_tier="standard",
        time_budget_minutes=15,
        quiet_hours=(22, 7)
    )
    
    env_context = await assess_environment()
    workflow_id = await coordinator.start_opportunity_discovery(
        user_id=hub_user_id,
        session_id=session_id,
        user_constraints=user_constraints,
        env_context=env_context
    )
    
    # Process results
    status = await coordinator.get_workflow_status(workflow_id)
    opportunities = status["results"]["opportunities"]["selected_opportunities"]
    
    for opp in opportunities:
        if opp["value_score"] > 0.7 and opp["friction_score"] < 0.3:
            suggest_connection(opp)
```

## Troubleshooting

### Common Issues

**Device Not Found**
- Check network connectivity and device power
- Verify discovery protocols are enabled
- Ensure device is in pairing mode

**Connection Fails**
- Review troubleshooting recommendations from RLA
- Check environment prerequisites
- Verify consent scopes are granted

**High Privacy Cost**
- Switch to local-only discovery methods
- Review and minimize consent scopes
- Use privacy tier "minimal" for sensitive environments

### Debug Mode
Enable debug logging:
```python
import logging
logging.getLogger("services.discovery").setLevel(logging.DEBUG)
```

### Performance Tuning
```python
config = CoordinatorConfig(
    max_concurrent_workflows=5,  # Adjust based on system capacity
    learning_enabled=True,       # Disable for privacy-sensitive deployments
    edge_first=True,            # Force local processing
    cloud_fallback=False        # Disable cloud features
)
```

## Future Enhancements

### Planned Features
- **Multi-language Support**: Internationalization for global deployment
- **Advanced ML Models**: Transformer-based entity linking and classification
- **Federated Learning**: Distributed model training across devices
- **Blockchain Integration**: Decentralized consent and audit logging
- **AR/VR Support**: Visual device discovery and connection guidance

### Research Areas
- **Zero-shot Device Classification**: Identify unknown devices
- **Predictive Maintenance**: Anticipate device connection issues
- **Behavioral Modeling**: Learn user patterns for proactive suggestions
- **Cross-platform Compatibility**: Unified discovery across ecosystems

## Contributing

### Development Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Set up database: `python create_database.py`
3. Run tests: `pytest tests/`
4. Start development server: `python api_interface.py`

### Code Style
- Follow PEP 8 for Python code
- Use type hints throughout
- Document all public APIs
- Include unit tests for new features

### Testing
```bash
# Run all tests
pytest tests/

# Run specific agent tests
pytest tests/test_resource_lookup_agent.py
pytest tests/test_connection_opportunity_agent.py

# Run integration tests
pytest tests/test_integration.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions and support:
- Create an issue in the project repository
- Check the troubleshooting section above
- Review the API documentation at `/docs` when running the server
- Consult the example usage in `/examples` endpoint
