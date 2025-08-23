# Orchestration System

The Orchestration System is the core component responsible for translating user intents into safe, efficient, and explainable execution plans. It implements the mission of converting any trigger into a TaskSpec with goals, constraints, and privacy class, then producing an Execution Plan (DAG) with steps, ordering, fallbacks, and guardrails.

## Mission

**Translate an intent into a safe, efficient, explainable Execution Plan.**

### When it runs:
- On user request, scheduled routine, or insight recommendation
- On replan events: state drift, device failure, consent change
- On preview: user taps "what will happen" before approving

### What it does:
1. **Intake and Normalization** - Converts any trigger into a TaskSpec with goals, constraints, and privacy class
2. **Policy and Consent Gate** - Evaluates required scopes and trust tier
3. **Context Pull** - Queries current device graph, environment, occupancy, tariffs, and quiet hours
4. **Planning** - Produces an Execution Plan (DAG): steps, ordering, fallbacks, guardrails
5. **Explainability** - Attaches "why this plan" summary and consent references
6. **Handover** - Emits the plan to Allocation with constraints and policy hash

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestration Engine                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Agent     │  │   Engine    │  │   Legacy    │        │
│  │             │  │             │  │ Workflows   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Core Components                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Intent    │  │   Policy    │  │   Context   │        │
│  │ Translator  │  │    Gate     │  │   Puller    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐                         │
│  │ Execution   │  │   Plan      │                         │
│  │  Planner    │  │ Explainer   │                         │
│  └─────────────┘  └─────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Orchestration Agent (`agent.py`)
The main agent that orchestrates the complete workflow:
- **Intake and Normalization**: Converts requests into TaskSpecs
- **Policy and Consent Gate**: Evaluates permissions and trust
- **Context Pull**: Gathers current system state
- **Planning**: Creates execution plans with optimization strategies
- **Explainability**: Generates human-readable explanations
- **Handover**: Prepares plans for allocation

### 2. Intent Translator (`intent_translator.py`)
Converts natural language intents into structured goals and constraints:
- Pattern matching for common IoT operations
- Entity extraction (devices, actions, locations, constraints)
- Goal and constraint generation
- Confidence scoring and validation

### 3. Policy Gate (`policy_gate.py`)
Evaluates required scopes and trust tier for task execution:
- Privacy class and trust tier compatibility
- Operation-specific requirements
- Consent reference generation
- Approval requirement determination
- Redaction and routing decisions

### 4. Context Puller (`context_puller.py`)
Queries current system context:
- Device graph with capabilities
- Environment data (temperature, humidity, etc.)
- Occupancy and presence information
- Energy tariffs and pricing
- Quiet hours configuration

### 5. Execution Planner (`planner.py`)
Creates execution plans with optimization strategies:
- **Privacy-first**: Local processing priority
- **Cost-optimized**: Minimize operational costs
- **Latency-optimized**: Fast execution paths
- **Comfort-optimized**: User comfort focus
- **Balanced**: Multi-objective optimization

### 6. Plan Explainer (`explainer.py`)
Generates human-readable explanations:
- Plan summaries and rationale
- Step-by-step explanations
- Privacy and security aspects
- Consent requirements
- Performance and cost analysis
- Safety guardrails

### 7. Models (`models.py`)
Core data structures:
- `TaskSpec`: Task specification with goals and constraints
- `ExecutionPlan`: Complete execution plan with steps
- `ExecutionStep`: Individual plan steps
- `ContextSnapshot`: Current system state
- `ConsentReference`: Permission and consent information

## Usage

### Basic Usage

```python
from services.orchestration.engine import OrchestrationEngine
from services.orchestration.models import OrchestrationRequest, TriggerType

# Initialize the engine
engine = OrchestrationEngine()
await engine.start()

# Create an execution plan
request = OrchestrationRequest(
    trigger_type=TriggerType.USER_REQUEST,
    intent="optimize energy usage in the living room",
    user_id="user_123",
    context_hints={"location": "living_room"},
    preferences={"privacy_first": True}
)

response = await engine.create_execution_plan(request)
print(f"Plan created: {response.plan_id}")
print(f"Status: {response.status.value}")
print(f"Rationale: {response.rationale}")

# Get plan status
status = await engine.get_plan_status(response.plan_id)
print(f"Plan status: {status}")

# Get system metrics
metrics = await engine.get_system_metrics()
print(f"System metrics: {metrics}")

await engine.stop()
```

### Advanced Usage

```python
# Preview mode - see what would happen without executing
preview_request = OrchestrationRequest(
    trigger_type=TriggerType.PREVIEW_REQUEST,
    intent="what would happen if I automate the morning routine",
    user_id="user_123",
    preview_mode=True
)

response = await engine.create_execution_plan(preview_request)
print(f"Preview plan: {response.rationale}")

# Cancel a running plan
cancelled = await engine.cancel_plan(plan_id)
print(f"Plan cancelled: {cancelled}")
```

## Configuration

The orchestration system can be configured through the `OrchestrationConfig`:

```python
from services.orchestration.agent import OrchestrationConfig

config = OrchestrationConfig(
    max_planning_time_ms=5000,        # Maximum time to create a plan
    max_plan_alternatives=3,          # Number of alternative plans to generate
    enable_preview_mode=True,         # Enable preview functionality
    enable_replanning=True,           # Enable automatic replanning
    privacy_first=True,               # Prioritize privacy by default
    local_execution_preference=0.8,   # Prefer local execution (0.0-1.0)
    cost_budget_default=1.0,          # Default cost budget in dollars
    latency_budget_default_ms=5000    # Default latency budget in milliseconds
)
```

## Privacy and Security

The orchestration system implements comprehensive privacy and security measures:

### Privacy Classes
- **PUBLIC**: No sensitive data, can be processed anywhere
- **INTERNAL**: System data, local processing preferred
- **CONFIDENTIAL**: User data, local processing required
- **RESTRICTED**: Highly sensitive data, strict local processing

### Trust Tiers
- **UNTRUSTED**: Limited access, sandboxed execution
- **BASIC**: Standard access with monitoring
- **VERIFIED**: Enhanced access for verified users
- **TRUSTED**: Full access for trusted users
- **PRIVILEGED**: Administrative access

### Guardrails
- **Privacy Guardrails**: Ensure local processing for sensitive data
- **Trust Guardrails**: Sandbox execution for low-trust operations
- **Safety Guardrails**: Validate critical device operations

## Metrics and Monitoring

The system tracks comprehensive metrics:

### Plan Metrics
- Success rate and time to plan
- Approval rate and user overrides
- Privacy score (percentage of steps kept local)
- Replan frequency due to drift
- Total executions and failures
- Average execution time and cost

### System Metrics
- Total plans and active plans
- Completed and failed plans
- Average planning time
- System health indicators

## Testing

Run the test suite to verify functionality:

```bash
cd services/orchestration
python -m pytest test_orchestration.py -v
```

Or run the demonstration script:

```bash
python test_orchestration.py
```

## Integration

The orchestration system integrates with:

- **Device Registry**: For device capabilities and status
- **Environment Services**: For sensor data and conditions
- **Occupancy Services**: For presence and activity data
- **Tariff Services**: For energy pricing information
- **ML Orchestrator**: For machine learning inference
- **Notification Services**: For user alerts and messages
- **Security Services**: For consent and policy management

## Failure and Recovery

The system handles various failure scenarios:

### Missing Consent
- Pause execution and request approval
- Provide clear explanation of required permissions
- Offer alternative plans with lower permission requirements

### Infeasible Plans
- Propose alternative approaches
- Degrade gracefully with reduced functionality
- Provide detailed explanation of limitations

### Conflicting Routines
- Resolve with user-defined priorities
- Apply policy-based conflict resolution
- Notify user of conflicts and proposed solutions

## Future Enhancements

Planned improvements include:

1. **ML-Powered Planning**: Use machine learning to optimize plan generation
2. **Dynamic Replanning**: Automatic plan adjustment based on changing conditions
3. **Federated Learning**: Privacy-preserving learning across devices
4. **Quantum Optimization**: Quantum algorithms for complex optimization problems
5. **Advanced Explainability**: More detailed and personalized explanations
6. **Real-time Adaptation**: Continuous plan optimization during execution

## Contributing

When contributing to the orchestration system:

1. Follow the existing code structure and patterns
2. Add comprehensive tests for new functionality
3. Update documentation for any API changes
4. Ensure privacy and security considerations are addressed
5. Add appropriate logging and monitoring

## License

This orchestration system is part of the Tetheritall project and follows the project's licensing terms.
