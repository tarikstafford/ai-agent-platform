# 🤖 Agent-to-Agent (A2A) Communication Protocol

The A2A Communication Protocol enables intelligent agents to discover, communicate, collaborate, and delegate tasks to each other autonomously. This creates a distributed network of specialized agents that can work together to solve complex problems.

## 🌟 Key Features

- **Agent Discovery**: Automatic discovery of agents and their capabilities
- **Task Delegation**: Delegate tasks to the most suitable agents
- **Multi-Agent Collaboration**: Coordinate complex workflows across multiple agents
- **Real-time Messaging**: Direct agent-to-agent communication
- **Load Balancing**: Intelligent task assignment based on agent capacity
- **Fault Tolerance**: Robust message delivery and retry mechanisms
- **Network Visualization**: Visual dashboard for monitoring agent communications
- **Message Tracing**: End-to-end message lifecycle debugging and monitoring

## 🏗️ Architecture Overview

### Core Components

#### 1. A2A Protocol (`src/a2a/protocol.py`)
- Message format definitions
- Task delegation structures
- Collaboration request formats
- Agent capability descriptions
- Error handling and status tracking

#### 2. A2A Communicator (`src/a2a/communicator.py`)
- Message routing and delivery
- Request/response handling
- Background message processing
- Communication statistics

#### 3. Agent Discovery (`src/a2a/discovery.py`)
- Agent capability announcement
- Discovery request/response handling
- Capability-based agent matching
- Network topology maintenance

#### 4. Task Management (`src/a2a/tasks.py`)
- Task delegation and execution
- Collaboration coordination
- Progress tracking and monitoring
- Task assignment strategies

#### 5. Message Routing (`src/a2a/routing.py`)
- Multi-transport message routing
- Delivery tracking and retry logic
- Network health monitoring
- Performance optimization

#### 6. Message Tracing (`src/a2a/traces.py`)
- Complete message lifecycle tracking
- Event-based trace recording (sent → routed → delivered → failed)
- SQLite-based trace storage with configurable retention
- Payload masking for sensitive data security
- Real-time trace visualization and debugging tools
- Export functionality for external analysis

## 📋 Message Types

### Discovery Messages
- `PING` / `PONG` - Basic connectivity check
- `DISCOVERY_REQUEST` / `DISCOVERY_RESPONSE` - Agent capability discovery
- `HEARTBEAT` - Periodic agent status updates

### Task Delegation
- `TASK_REQUEST` - Request another agent to execute a task
- `TASK_RESPONSE` - Response with task execution results
- `TASK_ACCEPT` / `TASK_REJECT` - Task acceptance/rejection
- `TASK_PROGRESS` / `TASK_COMPLETE` / `TASK_FAILED` - Execution status

### Collaboration
- `COLLABORATION_REQUEST` - Initiate multi-agent collaboration
- `COLLABORATION_ACCEPT` / `COLLABORATION_REJECT` - Join/decline collaboration
- `COLLABORATION_JOIN` / `COLLABORATION_LEAVE` - Manage participation

### Information Sharing
- `INFO_REQUEST` / `INFO_RESPONSE` - Request agent information
- `STATUS_REQUEST` / `STATUS_RESPONSE` - Check agent status
- `KNOWLEDGE_SHARE` - Share information between agents

## 🚀 Getting Started

### 1. Enable A2A for an Agent

```python
from agents import ConversationalAgent, AgentConfig

# Create agent with A2A enabled
config = AgentConfig(
    name="MyAgent",
    description="A helpful AI assistant",
    model="gpt-3.5-turbo",
    a2a_enabled=True,
    a2a_capabilities=["conversation", "analysis", "web_search"]
)

agent = ConversationalAgent(config, agent_id="my_agent_001")

# Start A2A communication
await agent.start_a2a_communication()
```

### 2. Discover Other Agents

```python
# Discover all available agents
all_agents = await agent.discover_agents()

# Discover agents with specific capabilities
math_agents = await agent.discover_agents(["calculation", "analysis"])

for agent_info in math_agents:
    print(f"Found: {agent_info['name']} - {agent_info['capabilities']}")
```

### 3. Delegate Tasks

```python
# Delegate a calculation task
success = await agent.delegate_task_to_agent(
    agent_id="math_specialist_001",
    task_type="calculation",
    task_data={"expression": "15 * 7 + 25"}
)

if success:
    print("Task delegated successfully!")
```

### 4. Handle Incoming Tasks

```python
# Register task handler
async def handle_analysis(task_data):
    data = task_data.get("data", [])
    # Perform analysis
    result = analyze_data(data)
    return {"analysis": result, "confidence": 0.95}

agent.register_task_handler("analysis", handle_analysis)
```

### 5. Start Collaborations

```python
# Initiate multi-agent collaboration
collaboration_id = await agent.collaborate_with_agents(
    agent_ids=["agent_001", "agent_002", "agent_003"],
    collaboration_title="Research Project",
    collaboration_description="Collaborative research on AI trends"
)
```

## 🎛️ Dashboard and Monitoring

### Access A2A Dashboard
```bash
# Start the platform
python run_server.py

# Open A2A dashboard
http://127.0.0.1:8000/api/dashboard/a2a
```

### Dashboard Features
- **Network Visualization**: Interactive graph of agent connections
- **Real-time Statistics**: Live metrics on messages, tasks, and collaborations
- **Agent Details**: Detailed view of individual agent capabilities and status
- **Task Management**: Monitor active tasks and their progress
- **Collaboration Tracking**: Overview of ongoing multi-agent collaborations
- **Message Log**: Real-time message flow monitoring

## 🔧 REST API Endpoints

### Agent Discovery
```bash
# Discover agents with capabilities
POST /api/a2a/agents/discover
{
  "requester_id": "agent_001",
  "required_capabilities": ["calculation", "analysis"],
  "timeout": 30
}

# Ping agent for connectivity
POST /api/a2a/agents/{agent_id}/ping
{
  "sender_id": "agent_001",
  "timeout": 10
}
```

### Task Management
```bash
# Delegate task
POST /api/a2a/tasks/delegate
{
  "requester_id": "agent_001",
  "task_type": "calculation",
  "task_data": {"expression": "15 * 7"},
  "description": "Mathematical calculation",
  "required_capabilities": ["calculation"]
}

# Check task status
GET /api/a2a/tasks/status/{task_id}

# List active tasks
GET /api/a2a/tasks/active?agent_id=agent_001
```

### Collaboration Management
```bash
# Initiate collaboration
POST /api/a2a/collaborations/initiate
{
  "coordinator_id": "agent_001",
  "title": "Research Project",
  "description": "Multi-agent research collaboration",
  "participant_ids": ["agent_002", "agent_003"],
  "required_capabilities": ["research", "analysis"]
}

# Join collaboration
POST /api/a2a/collaborations/{collaboration_id}/join
{
  "agent_id": "agent_004"
}

# List active collaborations
GET /api/a2a/collaborations/active
```

### Network Overview
```bash
# Get complete network overview
GET /api/a2a/network/overview

# Get agent A2A statistics
GET /api/a2a/agents/{agent_id}/stats

# Get A2A system status
GET /api/a2a/status
```

## 🎯 Use Cases

### 1. Distributed Problem Solving
```python
# Complex research workflow
coordinator = await create_coordinator_agent()
research_agent = await create_research_agent()
analysis_agent = await create_analysis_agent()

# Step 1: Research
await coordinator.delegate_task_to_agent(
    agent_id=research_agent.agent_id,
    task_type="research",
    task_data={"topic": "AI trends 2024"}
)

# Step 2: Analysis
await coordinator.delegate_task_to_agent(
    agent_id=analysis_agent.agent_id,
    task_type="analysis",
    task_data={"research_results": "..."}
)
```

### 2. Specialized Agent Network
```python
# Create specialized agents
math_bot = await create_math_specialist()
web_bot = await create_web_researcher()
writer_bot = await create_content_writer()

# User query gets routed to appropriate specialist
user_query = "What's the statistical significance of recent AI performance improvements?"

# Discovery finds the right agent
suitable_agents = await coordinator.discover_agents(["statistics", "research"])
```

### 3. Load Balancing
```python
# Multiple identical agents for high throughput
processors = [
    await create_data_processor(f"processor_{i}")
    for i in range(5)
]

# Tasks automatically distributed based on load
for data_batch in large_dataset:
    await coordinator.delegate_task_to_agent(
        agent_id=None,  # Auto-select least loaded agent
        task_type="process_data",
        task_data={"batch": data_batch}
    )
```

### 4. Fault-Tolerant Workflows
```python
# Task automatically retries on failure
await coordinator.delegate_task_to_agent(
    agent_id="primary_processor",
    task_type="critical_analysis",
    task_data={"data": sensitive_data},
    max_attempts=3,  # Auto-retry on failure
    fallback_capabilities=["backup_analysis"]  # Use backup agent if needed
)
```

## ⚙️ Configuration

### Agent Configuration
```python
config = AgentConfig(
    name="SpecializedAgent",
    description="Agent specialized in data analysis",
    model="gpt-4",
    a2a_enabled=True,
    a2a_capabilities=[
        "data_analysis",
        "statistical_modeling", 
        "report_generation"
    ],
    # A2A specific settings
    max_concurrent_tasks=3,
    task_timeout_minutes=30,
    collaboration_timeout_minutes=60
)
```

### Network Configuration
```python
# Transport configuration
communicator.register_transport_handler("http", http_transport_handler)
communicator.register_transport_handler("websocket", websocket_transport_handler)

# Routing configuration
router.add_route("agent_001", "http", "http://localhost:8001/a2a/receive")
router.add_route("agent_002", "websocket", "ws://localhost:8002/a2a/ws")

# Discovery configuration
discovery.discovery_interval = 300  # 5 minutes
discovery.agent_ttl = 600          # 10 minutes
```

## 🔒 Security Considerations

### Message Authentication
- All messages include sender verification
- Message integrity through checksums
- Optional message encryption for sensitive data

### Agent Verification
- Agent identity verification before task delegation
- Capability verification before assignment
- Rate limiting to prevent abuse

### Network Security
- Transport-level security (HTTPS/WSS)
- Agent whitelist/blacklist support
- Message sanitization and validation

## 📊 Performance and Monitoring

### Key Metrics
- **Message Throughput**: Messages per second across the network
- **Task Success Rate**: Percentage of successfully completed tasks
- **Discovery Latency**: Time to find suitable agents
- **Network Density**: Connectivity between agents
- **Load Distribution**: Task distribution across agents

### Monitoring Tools
- Real-time dashboard with network visualization
- Prometheus metrics export
- Structured logging with correlation IDs
- Performance profiling and optimization

### Scaling Considerations
- Horizontal scaling with agent clusters
- Message broker integration for high throughput
- Distributed discovery with gossip protocols
- Load balancing strategies for task distribution

## 🧪 Testing and Development

### Running Tests
```bash
# Run A2A protocol tests
python -m pytest tests/test_a2a_protocol.py

# Run integration tests
python -m pytest tests/test_a2a_integration.py

# Run performance benchmarks
python benchmarks/a2a_performance.py
```

### Development Setup
```bash
# Install development dependencies
pip install -e ".[dev]"

# Start development environment
python examples/a2a_communication_demo.py

# Access development dashboard
http://127.0.0.1:8000/api/dashboard/a2a
```

## 🚀 Advanced Features

### Custom Message Types
```python
from a2a.protocol import A2AMessage, A2AMessageType

# Define custom message type
class CustomMessageType(A2AMessageType):
    CUSTOM_ANALYSIS = "custom_analysis"

# Register handler
agent.register_a2a_message_handler("custom_analysis", custom_handler)
```

### Task Assignment Strategies
```python
# Custom assignment strategy
async def capability_weighted_assignment(agents, task):
    # Score agents based on capability match and load
    scores = []
    for agent in agents:
        capability_match = len(set(agent.capabilities) & set(task.required_capabilities))
        load_factor = 1 - agent.load
        score = capability_match * load_factor
        scores.append((agent, score))
    
    # Return highest scoring agent
    return max(scores, key=lambda x: x[1])[0].agent_id

# Register strategy
task_manager.assignment_strategies["capability_weighted"] = capability_weighted_assignment
```

### Dynamic Capability Updates
```python
# Add new capability at runtime
agent.a2a_discovery.add_capability(
    AgentCapability(
        name="new_feature",
        description="Newly acquired capability",
        version="1.0"
    )
)

# Update discovery announcement
await agent.a2a_discovery._broadcast_discovery()
```

## 📚 Examples and Demos

### Basic Communication
```bash
python examples/a2a_communication_demo.py
```

### Multi-Agent Workflows  
```bash
python examples/multi_agent_workflow.py
```

### Performance Benchmarks
```bash
python benchmarks/a2a_scalability_test.py
```

## 🔍 Message Tracing and Debugging

The A2A platform includes a comprehensive message tracing system for debugging inter-agent communication flows.

### Trace Viewer Features

- **Complete Message Lifecycle**: Track messages from send → route → deliver → acknowledge/fail
- **Visual Timeline**: Interactive timeline view of message events with timestamps
- **Filtering and Search**: Filter by agent, message type, time range, and status
- **Payload Preview**: Masked payload content for debugging (sensitive data protected)
- **Export Functionality**: Export traces as JSON for external analysis
- **Real-time Statistics**: Live metrics on trace counts, success rates, and performance

### Accessing the Trace Viewer

1. Start the platform: `python run_server.py`
2. Open the A2A Dashboard: `http://127.0.0.1:8000/api/dashboard/a2a`
3. Click the "Message Traces" tab
4. Use filters to find specific traces or view recent activity

### Trace Configuration

Configure tracing behavior in `.env`:

```bash
# Enable/disable A2A tracing
A2A_TRACING_ENABLED=true

# Retention period for trace data
A2A_TRACE_RETENTION_DAYS=7

# Cleanup interval
A2A_TRACE_CLEANUP_HOURS=24

# Database path
A2A_TRACE_DB_PATH=./data/a2a_traces.db
```

### Programmatic Trace Access

```python
# Get trace by correlation ID
trace = await tracer.get_trace("correlation-id-123")
print(f"Duration: {trace.duration_ms}ms")
print(f"Status: {trace.final_status}")

# List recent traces
traces = await tracer.list_traces(
    agent_id="agent-1",
    time_range_hours=24,
    limit=50
)

# Export trace data
export_data = await tracer.export_trace("correlation-id-123")
```

### Trace Event Types

- **SENT**: Message queued for sending
- **RECEIVED**: Message received by target agent  
- **ROUTED**: Message forwarded through intermediate agent
- **RETRY**: Delivery retry attempted
- **DELIVERED**: Message successfully delivered
- **FAILED**: Message delivery failed permanently
- **ACKNOWLEDGED**: Recipient confirmed message processing
- **TIMEOUT**: Message expired before delivery

### Security and Privacy

- **Payload Masking**: Sensitive fields (api_key, password, token, etc.) are automatically masked
- **Configurable Masking**: Custom masking rules can be defined
- **Size Limits**: Payload previews are truncated to prevent storage bloat
- **Retention Controls**: Automatic cleanup based on configurable retention periods

## 🤝 Contributing

The A2A protocol is designed to be extensible and welcomes contributions:

1. **Protocol Extensions**: New message types and communication patterns
2. **Transport Adapters**: Support for additional transport mechanisms
3. **Assignment Strategies**: Novel approaches to task assignment
4. **Monitoring Tools**: Enhanced observability and debugging tools
5. **Performance Optimizations**: Improvements to scalability and efficiency

## 📞 Support and Documentation

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Complete API reference and guides
- **Examples**: Comprehensive examples and tutorials
- **Community**: Discord/Slack for discussions and support

---

**The A2A Protocol transforms individual agents into a collaborative network, enabling sophisticated multi-agent systems that can tackle complex, distributed problems autonomously.** 🌐✨