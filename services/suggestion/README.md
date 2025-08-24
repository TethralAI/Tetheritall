# Tethral Suggestion Engine

A comprehensive suggestion engine that discovers meaningful device and service combinations, evaluates them for feasibility and value, and provides intelligent recommendations for smart home automation.

## Overview

The Tethral Suggestion Engine implements the complete pipeline from device ingestion to recommendation generation and execution. It takes a user's current devices and services, discovers all meaningful combinations, evaluates them for feasibility and value, recommends the best options, executes what the user selects through the orchestration system, and learns from the user's follow-up behavior to refine future suggestions.

## Architecture

The system is built around a modular architecture with the following core components:

### Core Pipeline Components

1. **SuggestionEngine** (`engine.py`) - Main orchestrator that coordinates the entire pipeline
2. **DeviceIngestionService** (`ingestion.py`) - Normalizes devices and services into canonical capabilities
3. **PowersetGenerator** (`powerset.py`) - Generates combinations with intelligent pruning and optimization
4. **CombinationEvaluator** (`evaluation.py`) - Evaluates combinations for feasibility and value
5. **RecommendationPackager** (`recommendation.py`) - Creates user-friendly recommendation cards
6. **OrchestrationAdapter** (`orchestration.py`) - Converts recommendations into executable plans
7. **FeedbackService** (`feedback.py`) - Records user feedback and updates learning overlays
8. **LLMBridge** (`llm_bridge.py`) - Provides clarifying suggestions when needed

### Data Models

- **SuggestionRequest/SuggestionResponse** - API request/response structures
- **DeviceCapability/ServiceCapability** - Normalized capability representations
- **CombinationCandidate** - Candidate device/service combinations
- **RecommendationCard** - User-facing recommendation cards
- **ExecutionPlan** - Plans for executing recommendations
- **UserOverlay** - User-specific learning and preferences
- **ContextSnapshot** - Current context for suggestion generation

## Key Features

### 1. Intelligent Device Ingestion (B1)
- Normalizes devices and services into canonical capabilities
- Attaches room and zone hints for role binding
- Validates reachability and marks temporarily unavailable items
- Builds capability graph and service readiness map

### 2. Powerset Generation with Pruning (B2)
- Generates combinations from size 1 up to configurable limit
- Applies early pruning to remove infeasible combinations
- Collapses equivalent combinations by capability signature
- Respects strict time budget and always yields candidates

### 3. Comprehensive Evaluation (B3)
- **Feasibility checks**: Safety constraints, contextual constraints, device reachability
- **Value scoring**: Context fit, utility, preference fit, novelty, effort, risk
- **Outcome matching**: Matches combinations against known outcome templates
- **User overlay integration**: Applies learned preferences and patterns

### 4. User-Friendly Recommendations (B4)
- Selects top unique outcomes after clustering similar ones
- Builds home-specific plans for each selected outcome
- Produces user-friendly suggestion cards with rationale
- Generates what-if analysis for missing capabilities

### 5. Orchestration Integration (B5)
- Converts recommendations into orchestration tasks
- Registers triggers and schedules with orchestration layer
- Emits clear activation summaries for users
- Monitors execution and collects success signals

### 6. Continuous Learning (B6)
- Records user feedback (accept, reject, snooze, edit, execute)
- Updates user overlay with preference drifts
- Boosts accepted patterns and penalizes rejected ones
- Narrows or widens suggestion sets based on behavior

### 7. LLM Fallback (F1-F3)
- Calls LLM when insufficient combinations are found
- Sends compact brief with targeted questions
- Processes LLM responses into actionable suggestions
- Records calls for analysis and improvement

## Usage

### Basic Usage

```python
from services.suggestion import SuggestionEngine, SuggestionRequest

# Initialize engine
engine = SuggestionEngine()
await engine.start()

# Create request
request = SuggestionRequest(
    user_id="user123",
    session_id="session456",
    context_hints={"location": "home", "time_of_day": "evening"},
    preferences={"energy_vs_comfort_bias": 0.7}
)

# Generate suggestions
response = await engine.generate_suggestions(request)

# Process recommendations
for recommendation in response.recommendations:
    print(f"Title: {recommendation.title}")
    print(f"Description: {recommendation.description}")
    print(f"Confidence: {recommendation.confidence}")
    print(f"Effort: {recommendation.effort_rating}")
    print("---")

# Record feedback
await engine.record_feedback(
    user_id="user123",
    recommendation_id=recommendation.recommendation_id,
    feedback_type="accept"
)

# Execute recommendation
result = await engine.execute_suggestion(
    request_id=response.request_id,
    recommendation_id=recommendation.recommendation_id,
    user_id="user123"
)
```

### API Usage

The system provides REST API endpoints for integration:

```bash
# Generate suggestions
curl -X POST "http://localhost:8000/suggestions/generate" \
  -H "X-User-ID: user123" \
  -H "Content-Type: application/json" \
  -d '{
    "context_hints": {"location": "home"},
    "preferences": {"energy_vs_comfort_bias": 0.7},
    "max_recommendations": 5
  }'

# Record feedback
curl -X POST "http://localhost:8000/suggestions/feedback" \
  -H "X-User-ID: user123" \
  -H "Content-Type: application/json" \
  -d '{
    "recommendation_id": "rec_123",
    "feedback_type": "accept",
    "feedback_data": {"reason": "useful"}
  }'

# Execute suggestion
curl -X POST "http://localhost:8000/suggestions/execute" \
  -H "X-User-ID: user123" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req_456",
    "recommendation_id": "rec_123"
  }'
```

## Configuration

The system can be configured through the `SuggestionConfig` class:

```python
from services.suggestion import SuggestionConfig

config = SuggestionConfig(
    max_combinations=1000,           # Maximum combinations to generate
    max_candidates_per_request=10,   # Maximum recommendations per request
    time_budget_ms=5000,             # Time budget for generation
    enable_llm_fallback=True,        # Enable LLM fallback
    local_learning_default=True,     # Default to local learning
    cloud_sync_optional=True,        # Enable optional cloud sync
    quiet_hours_start="22:00",       # Quiet hours start
    quiet_hours_end="07:00"          # Quiet hours end
)

engine = SuggestionEngine(config)
```

## Safety and Privacy

The system includes comprehensive safety and privacy features:

### Safety Features
- **Hard safety rules**: Never auto-unlock doors, no remote security control when away
- **Contextual constraints**: No disruptive audio during quiet hours (unless safety-related)
- **Safety levels**: SAFE, CAUTION, DANGEROUS, RESTRICTED
- **Execution guardrails**: Dry run paths, quiet hour suppression, recovery messages

### Privacy Features
- **Privacy levels**: PUBLIC, PERSONAL, PRIVATE, SENSITIVE
- **Local by default**: All learning happens locally unless cloud sync is enabled
- **Encrypted cloud mirror**: Optional encrypted cloud sync for preferences
- **Privacy annotations**: Each step and suggestion includes privacy level
- **Clear consent**: Transparent toggles for learning and cloud mirror

## Performance and Scalability

### Performance Optimizations
- **Time budget enforcement**: Strict compute windows with progressive results
- **Early pruning**: Removes infeasible combinations early in the pipeline
- **Signature reduction**: Collapses equivalent combinations to reduce search space
- **Caching**: Caches user overlays and frequently accessed data

### Scalability Features
- **Async/await**: Full async implementation for high concurrency
- **Modular design**: Components can be scaled independently
- **Database integration**: Uses existing database models and sessions
- **API-first**: REST API for easy integration with frontend and other services

## Integration Points

### Existing System Integration
- **Database**: Uses existing `Device` and `ApiEndpoint` models
- **Orchestration**: Integrates with existing orchestration system
- **Authentication**: Integrates with existing user authentication
- **Configuration**: Uses existing settings and configuration system

### External Service Integration
- **Weather services**: For weather-responsive automation
- **Calendar services**: For schedule-based automation
- **Presence services**: For presence-aware automation
- **LLM services**: For clarifying suggestions when needed

## Monitoring and Observability

### Metrics
- **Performance metrics**: Processing time, combination counts, success rates
- **Quality metrics**: User acceptance rates, feedback patterns
- **LLM metrics**: Call frequency, success rates, suggestion quality
- **System metrics**: Component health, error rates, resource usage

### Logging
- **Structured logging**: All components use structured logging
- **Privacy-aware**: No personal content in logs
- **Traceability**: Request IDs for end-to-end tracing
- **Audit trails**: Complete audit trails for debugging and compliance

## Development and Testing

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run linting
flake8 services/suggestion/
black services/suggestion/

# Run type checking
mypy services/suggestion/
```

### Testing Strategy
- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test component interactions
- **End-to-end tests**: Test complete pipeline
- **Performance tests**: Test time budget and scalability
- **Acceptance tests**: Test against behavioral requirements

## Future Enhancements

### Planned Features
- **Advanced ML models**: More sophisticated learning algorithms
- **Multi-user households**: Support for multiple users in same home
- **Advanced scheduling**: More sophisticated scheduling capabilities
- **Voice integration**: Voice-based suggestion interaction
- **Mobile app**: Dedicated mobile app for suggestion management

### Research Areas
- **Federated learning**: Privacy-preserving collaborative learning
- **Explainable AI**: Better explanations for why suggestions fit
- **Predictive suggestions**: Proactive suggestions based on patterns
- **Cross-device learning**: Learning across multiple homes and devices

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the test examples
- Contact the development team
