# Complete Orchestration System

A comprehensive orchestration system that translates user intents into safe, efficient, and explainable execution plans, binds them to concrete resources, and maintains an always-fresh picture of the current system state.

## Overview

The Complete Orchestration System consists of three main components that work together to create a seamless intent-to-execution pipeline:

1. **Orchestration Agent** - Translates intents into execution plans
2. **Resource Allocation Agent** - Binds plans to concrete resources
3. **Contextual Awareness Agent** - Maintains current system state

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Complete Orchestration System                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │   Orchestration │    │   Resource      │    │  Contextual  │ │
│  │     Agent       │    │  Allocation     │    │  Awareness   │ │
│  │                 │    │     Agent       │    │    Agent     │ │
│  │ • Intent        │    │ • Feasibility   │    │ • Signal     │ │
│  │   Translation   │    │   Scanning      │    │   Ingestion  │ │
│  │ • Policy &      │    │ • Placement     │    │ • Fusion &   │ │
│  │   Consent Gate  │    │   Decision      │    │   State      │ │
│  │ • Context Pull  │    │ • Binding &     │    │   Estimation │ │
│  │ • Planning      │    │   Reservation   │    │ • Capability │ │
│  │ • Explainability│    │ • Execution     │    │   Graph      │ │
│  │ • Handover      │    │   Prep          │    │ • Derived    │ │
│  │                 │    │ • Dispatch      │    │   Flags      │ │
│  │                 │    │ • Adaptive      │    │ • Privacy    │ │
│  │                 │    │   Rebinding     │    │   Guard      │ │
│  └─────────────────┘    └─────────────────┘    └──────────────┘ │
│           │                       │                       │     │
│           └───────────────────────┼───────────────────────┘     │
│                                   │                             │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Integration Layer                        │ │
│  │  • CompleteOrchestrationSystem                              │ │
│  │  • Intent Processing Pipeline                               │ │
│  │  • Error Handling & Recovery                                │ │
│  │  • Performance Monitoring                                   │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Orchestration Agent

**Mission**: Translate an intent into a safe, efficient, explainable Execution Plan.

**Key Features**:
- **Intent Translation**: Converts natural language into structured goals and constraints
- **Policy & Consent Gate**: Evaluates required scopes and trust tiers
- **Context Pull**: Queries current device graph, environment, occupancy, tariffs
- **Planning**: Produces execution plans with optimization strategies
- **Explainability**: Attaches rationale and consent references
- **Handover**: Emits plans to Resource Allocation

**When it runs**:
- On user request, scheduled routine, or insight recommendation
- On replan events: state drift, device failure, consent change
- On preview: user taps "what will happen" before approving

**Optimization Strategies**:
- Privacy-first: Prioritizes local execution and data minimization
- Cost-optimized: Minimizes resource costs while meeting requirements
- Latency-optimized: Prioritizes fast response times
- Comfort-optimized: Focuses on user comfort and experience
- Balanced: Combines multiple objectives

### 2. Resource Allocation Agent

**Mission**: Bind plan steps to the best concrete resources and decide where to run them.

**Key Features**:
- **Feasibility Scanning**: Checks device readiness, protocol support, energy estimates
- **Placement Decision**: Chooses edge, cloud, or hybrid placement per step
- **Binding & Reservation**: Locks device or compute slots, avoids conflicts
- **Execution Prep**: Generates step-level run configs with consent scope
- **Dispatch**: Hands bound steps to Scheduler and Executor
- **Adaptive Rebinding**: Reallocates on failure, jitter, or state drift

**When it runs**:
- Immediately after plan creation or change
- On schedule ticks for delayed or recurring steps
- On resource changes: device online/offline, power, network quality

**Placement Targets**:
- **Local Device**: Direct device control for privacy and low latency
- **Edge Gateway**: Local processing with some network communication
- **Edge Cluster**: Regional processing for complex operations
- **Cloud Region**: Scalable cloud processing for heavy workloads
- **Hybrid**: Combination of multiple targets

### 3. Contextual Awareness Agent

**Mission**: Maintain an always-fresh, privacy-safe picture of "what is true right now".

**Key Features**:
- **Signal Ingestion**: Pulls and subscribes to raw signals from devices, apps, services
- **Normalization**: Converts everything to canonical units and schemas
- **Entity Binding**: Maps signals to device entities, users, and zones
- **Fusion & State Estimation**: Combines multiple signals into higher-confidence states
- **Capability Graph**: Maintains live graph of device capabilities and dependencies
- **Derived Flags**: Computes higher-level context flags
- **Privacy Guard**: Classifies fields by sensitivity and enforces data minimization
- **Eventing**: Publishes deltas when thresholds are crossed

**Signal Domains**:
- **Presence & Occupancy**: Phone geofences, Wi-Fi association, motion sensors
- **Time & Schedules**: Clock time, quiet hours, calendar items, holidays
- **Space & Zones**: Rooms, floors, outdoor vs indoor, user-defined zones
- **Environment**: Temperature, humidity, light level, noise level, air quality
- **Energy & Power**: Breaker budgets, appliance draw, EV charging, solar generation
- **Water & Gas**: Flow rate, valve states, leak sensors, hot water recovery
- **Network Health**: WAN status, local mesh quality, device RSSI, latency
- **Device Lifecycle**: Online status, battery level, firmware version, errors
- **Security Posture**: Armed states, door/window states, cameras, intrusion signals
- **External Context**: Weather, severe alerts, grid events, local regulations

## Usage

### Basic Usage

```python
import asyncio
from services.orchestration.test_complete_system import CompleteOrchestrationSystem

async def main():
    # Initialize the complete system
    system = CompleteOrchestrationSystem()
    
    # Start all components
    await system.start()
    
    try:
        # Process a user intent
        result = await system.process_intent(
            intent="optimize energy usage in the living room",
            user_id="user_123",
            preferences={"privacy_first": True}
        )
        
        if result["success"]:
            print(f"✅ Plan created: {result['orchestration_plan_id']}")
            print(f"   Resources allocated: {result['allocation_id']}")
            print(f"   Expected cost: ${result['expected_cost']:.4f}")
            print(f"   Privacy score: {result['privacy_score']:.2f}")
        else:
            print(f"❌ Failed: {result['error']}")
    
    finally:
        # Stop all components
        await system.stop()

# Run the example
asyncio.run(main())
```

### Advanced Usage

```python
# Add context signals
await system.add_context_signal({
    "field_name": "temperature",
    "value": 22.5,
    "unit": "celsius",
    "domain": "environment",
    "confidence": "high"
})

# Process intent with specific constraints
result = await system.process_intent(
    intent="create a comfortable movie night environment",
    user_id="user_123",
    preferences={"comfort_optimized": True},
    cost_budget=0.05,
    latency_budget_ms=2000,
    privacy_requirements={"enhanced_privacy": True},
    energy_constraints={"energy_efficient": True}
)
```

## Configuration

### Orchestration Configuration

```python
from services.orchestration.engine import OrchestrationConfig

config = OrchestrationConfig(
    max_planning_time_ms=5000,
    max_plan_alternatives=3,
    enable_preview_mode=True,
    enable_replanning=True,
    privacy_first=True,
    local_execution_preference=0.8,
    cost_budget_default=1.0,
    latency_budget_default_ms=5000
)
```

### Resource Allocation Configuration

```python
from services.orchestration.resource_allocator import ResourceAllocatorConfig

config = ResourceAllocatorConfig(
    max_feasibility_check_time_ms=2000,
    max_placement_decision_time_ms=3000,
    max_binding_time_ms=5000,
    enable_adaptive_rebinding=True,
    rebinding_timeout_ms=10000,
    local_execution_preference=0.8,
    privacy_first_placement=True,
    cost_optimization_weight=0.3,
    latency_optimization_weight=0.3,
    energy_optimization_weight=0.2,
    reliability_optimization_weight=0.2,
    max_fallback_resources=3,
    reservation_timeout_minutes=30
)
```

### Contextual Awareness Configuration

```python
from services.orchestration.contextual_awareness import ContextualAwarenessConfig

config = ContextualAwarenessConfig(
    snapshot_interval_ms=1000,
    max_signal_age_ms=30000,
    confidence_decay_rate=0.1,
    fusion_window_ms=5000,
    derived_flag_expiry_ms=300000,
    privacy_enforcement=True,
    data_minimization=True,
    retention_window_hours=24,
    health_check_interval_ms=60000,
    max_entities_per_snapshot=1000,
    max_signals_per_snapshot=10000
)
```

## Testing

Run the complete system test suite:

```bash
python -m services.orchestration.test_complete_system
```

The test suite includes:
- **Complete System Test**: Tests the full intent-to-execution pipeline
- **Error Handling Test**: Tests system behavior with invalid inputs
- **Performance Test**: Tests system performance under load

## Key Features

### Privacy & Security
- **Consent Management**: All operations respect user consent and privacy preferences
- **Data Minimization**: Only necessary data is shared between components
- **Privacy Classification**: All data is classified by sensitivity level
- **Secure Communication**: All inter-component communication is secured

### Reliability & Resilience
- **Adaptive Rebinding**: Automatically reallocates resources on failures
- **Fallback Strategies**: Multiple fallback options for each operation
- **Health Monitoring**: Continuous monitoring of system health
- **Error Recovery**: Graceful handling of errors and failures

### Performance & Efficiency
- **Optimization Strategies**: Multiple optimization strategies for different goals
- **Resource Efficiency**: Efficient use of available resources
- **Latency Optimization**: Minimizes response times where possible
- **Cost Optimization**: Minimizes resource costs while meeting requirements

### Explainability & Transparency
- **Plan Rationale**: Every execution plan includes detailed rationale
- **Placement Explanation**: Resource allocation decisions are explained
- **Context Explanation**: Derived flags include explanation of inputs
- **Audit Trail**: Complete audit trail of all decisions and actions

## Integration Points

### External Services
- **Device Registry**: For device discovery and capabilities
- **Security & Consent Layer**: For privacy and security enforcement
- **Scheduler**: For task scheduling and execution
- **Executor**: For actual task execution
- **Observability Hub**: For monitoring and metrics

### Data Sources
- **Device Telemetry**: Real-time device status and sensor data
- **User Preferences**: User-defined preferences and policies
- **Environmental Data**: Weather, tariffs, schedules
- **Network Status**: Network health and connectivity information

## Metrics & Monitoring

### Orchestration Metrics
- Plan success rate and time to plan
- Approval rate and user overrides
- Privacy score (percent steps kept local)
- Replan frequency due to drift

### Resource Allocation Metrics
- Placement accuracy vs. SLA and cost targets
- Rebinding rate and time to recover
- Local execution ratio by privacy class
- Device utilization and clash rate

### Contextual Awareness Metrics
- Snapshot freshness percentile by domain
- Confidence distribution and time above target thresholds
- False positive and false negative rates for key flags
- Mean time to detect and broadcast critical context changes
- Data minimization score for each consumer

## Future Enhancements

### Planned Features
- **Machine Learning Integration**: Learn from user preferences and system behavior
- **Advanced Optimization**: More sophisticated optimization algorithms
- **Multi-User Support**: Support for multiple users with different preferences
- **Advanced Privacy**: More granular privacy controls and data handling
- **Edge Computing**: Enhanced edge computing capabilities
- **IoT Protocol Support**: Support for additional IoT protocols

### Extensibility
- **Plugin Architecture**: Support for custom components and strategies
- **API Extensions**: Extensible APIs for custom integrations
- **Configuration Management**: Advanced configuration management
- **Custom Metrics**: Support for custom metrics and monitoring

## Contributing

1. Follow the existing code structure and patterns
2. Add comprehensive tests for new features
3. Update documentation for any API changes
4. Ensure privacy and security considerations are addressed
5. Follow the established error handling patterns

## License

This project is part of the Tetheritall system and follows the same licensing terms.
