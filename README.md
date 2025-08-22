# AI Agent Workflow Framework

A modern, extensible platform for building, hosting, and managing AI agents with web dashboard, REST API, and real-time monitoring.

## Features

### 🤖 Agent Framework
- **Multiple Agent Types**: Conversational, Reactive (tool-using), and Planning agents
- **Tool System**: Extensible tool framework with built-in tools for calculations, web search, file operations, and API calls
- **Memory Management**: Support for conversation memory and vector-based semantic memory
- **Async Support**: Built with async/await for efficient concurrent operations

### 🌐 Hosting Platform
- **Web Dashboard**: Modern web interface for managing agents
- **REST API**: Complete API for agent creation, management, and interaction
- **Real-time Monitoring**: Live metrics and status updates via WebSocket
- **Agent Registry**: Centralized agent lifecycle management
- **Persistence**: Agent configurations and state persistence

### 🎨 Visual Workflow Builder
- **Langflow Integration**: Embedded visual workflow builder with drag-and-drop interface
- **Pre-built Components**: LLMs, tools, memory, and I/O components library
- **Workflow Templates**: Ready-made templates for common agent patterns
- **Visual Agent Creation**: Create complex agents without coding
- **Real-time Testing**: Test workflows with sample inputs before deployment

### 🤝 Agent-to-Agent (A2A) Communication
- **Agent Discovery**: Automatic discovery of agents and their capabilities
- **Task Delegation**: Intelligent task assignment to specialized agents
- **Multi-Agent Collaboration**: Coordinate complex workflows across multiple agents
- **Real-time Messaging**: Direct inter-agent communication with fault tolerance
- **Load Balancing**: Smart task distribution based on agent capacity and capabilities
- **Network Visualization**: Interactive dashboard for monitoring agent communications

### 🛠️ Developer Experience
- **Type Safety**: Full type hints and mypy support
- **Testing**: Comprehensive test suite with pytest
- **Examples**: Ready-to-run examples demonstrating various capabilities
- **Docker Support**: Containerized deployment with docker-compose

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd CollectionsUAE
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package:
```bash
pip install -e ".[dev]"
```

4. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

### Starting the Platform

```bash
# Start the agent hosting platform
python run_server.py --host 127.0.0.1 --port 8000

# Access the web dashboard
open http://127.0.0.1:8000/api/dashboard/ui
```

### Running Examples

```bash
# Test the platform capabilities
python examples/platform_demo.py

# Test visual workflow integration
python examples/visual_workflow_demo.py

# Run basic agent examples
python examples/basic_usage.py

# Run research assistant example
python examples/research_assistant.py

# Test A2A communication features
python examples/a2a_communication_demo.py
```

## Agent Types

### Conversational Agent
Simple conversational AI that maintains dialogue history:

```python
from src.agents import ConversationalAgent, AgentConfig

config = AgentConfig(
    name="Assistant",
    description="A helpful AI assistant",
    model="gpt-3.5-turbo"
)

agent = ConversationalAgent(config)
response = await agent.run("Hello, how are you?")
print(response.content)
```

### Reactive Agent
Agent that can use tools to accomplish tasks:

```python
from src.agents import ReactiveAgent
from src.tools import CalculatorTool, WebSearchTool

agent = ReactiveAgent(config)
agent.add_langchain_tool(CalculatorTool())
agent.add_langchain_tool(WebSearchTool())

response = await agent.run("What is the square root of 144?")
```

### Planner Agent
Agent that breaks down complex goals into executable tasks:

```python
from src.agents import PlannerAgent

agent = PlannerAgent(config)
response = await agent.run("Build a web scraper for news articles")
# Returns a structured plan with tasks and dependencies
```

### Visual Workflow Agent (NEW!)
Agent created using the visual workflow builder:

```python
from src.agents import LangflowAgent

# Create from visual workflow
agent = LangflowAgent(config, flow_id="your-workflow-id")
response = await agent.run("Process this with my visual workflow")
```

**Create visual agents through the dashboard:**
1. Select "Visual Workflow" agent type
2. Click "🎨 Open Visual Builder"  
3. Design your workflow with drag-and-drop
4. Test and deploy as agent

### A2A Communication Agent (NEW!)
Agents with Agent-to-Agent communication capabilities:

```python
from src.agents import ConversationalAgent, AgentConfig

# Create agent with A2A enabled
config = AgentConfig(
    name="CoordinatorBot",
    description="Coordinates tasks between agents",
    model="gpt-4",
    a2a_enabled=True,
    a2a_capabilities=["coordination", "task_delegation", "collaboration"]
)

agent = ConversationalAgent(config, agent_id="coordinator_001")
await agent.start_a2a_communication()

# Discover other agents
available_agents = await agent.discover_agents(["calculation", "research"])

# Delegate tasks
success = await agent.delegate_task_to_agent(
    agent_id="math_specialist_001",
    task_type="calculation", 
    task_data={"expression": "15 * 7 + 25"}
)

# Start collaboration
collaboration_id = await agent.collaborate_with_agents(
    agent_ids=["agent_001", "agent_002"],
    collaboration_title="Research Project",
    collaboration_description="Multi-agent research collaboration"
)
```

**Access A2A Dashboard:**
- Open http://127.0.0.1:8000/api/dashboard/a2a
- Monitor agent network in real-time
- Visualize communications and collaborations
- Delegate tasks through the UI

## Available Tools

- **CalculatorTool**: Perform mathematical calculations
- **WebSearchTool**: Search the web for information
- **FileReadTool**: Read files from the filesystem
- **FileWriteTool**: Write files to the filesystem
- **APICallerTool**: Make HTTP API calls

## Creating Custom Agents

```python
from src.agents import BaseAgent, AgentResponse

class CustomAgent(BaseAgent):
    async def think(self, input_data):
        # Process input and generate response
        return AgentResponse(
            content="Processed result",
            success=True
        )
    
    async def act(self, action):
        # Execute actions
        return {"status": "completed"}
```

## Hosting Platform Usage

### Web Dashboard
Access the dashboard at `http://localhost:8000/api/dashboard/ui` to:
- View all running agents and their status
- Create new agents with different configurations
- Monitor real-time metrics and performance
- Start, stop, and manage agent lifecycle
- Chat with agents directly from the interface

### REST API
Complete API for programmatic access:

```bash
# List all agents
curl http://localhost:8000/api/agents/

# Create a new agent
curl -X POST http://localhost:8000/api/agents/ \
  -H "Content-Type: application/json" \
  -d '{
    "type": "conversational",
    "config": {
      "name": "MyAgent",
      "model": "gpt-3.5-turbo",
      "temperature": 0.7
    },
    "name": "Test Agent"
  }'

# Chat with an agent
curl -X POST http://localhost:8000/api/agents/{agent_id}/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

### Docker Deployment
```bash
# Using Docker Compose
docker-compose up -d

# Access dashboard
open http://localhost:8000/api/dashboard/ui
```

## Creating Custom Tools

```python
from src.tools import BaseTool
from pydantic import BaseModel, Field

class CustomToolInput(BaseModel):
    param: str = Field(..., description="Tool parameter")

class CustomTool(BaseTool):
    name = "custom_tool"
    description = "My custom tool"
    args_schema = CustomToolInput
    
    def execute(self, param: str):
        # Tool logic here
        return f"Processed: {param}"
```

## Development

### Running Tests
```bash
make test         # Run all tests
make test-cov     # Run tests with coverage
```

### Code Quality
```bash
make lint         # Run linter
make format       # Format code
make type-check   # Type checking
```

### Pre-commit Hooks
```bash
make setup-pre-commit  # Install pre-commit hooks
```

## Project Structure

```
├── src/
│   ├── agents/         # Agent implementations
│   ├── tools/          # Tool implementations
│   ├── memory/         # Memory systems
│   ├── hosting/        # Agent hosting infrastructure
│   ├── api/            # REST API and WebSocket handlers
│   └── dashboard/      # Web dashboard UI
├── tests/              # Test suite
├── examples/           # Example scripts
├── deployment/         # Deployment configurations
├── Dockerfile          # Container configuration
├── docker-compose.yml  # Multi-service deployment
└── pyproject.toml      # Project configuration
```

## API Reference

### Agent Management
- `GET /api/agents/` - List all agents
- `POST /api/agents/` - Create new agent
- `GET /api/agents/{id}` - Get agent details
- `DELETE /api/agents/{id}` - Delete agent
- `POST /api/agents/{id}/start` - Start agent
- `POST /api/agents/{id}/stop` - Stop agent
- `POST /api/agents/{id}/chat` - Chat with agent

### Dashboard
- `GET /api/dashboard/` - Get dashboard data
- `GET /api/dashboard/ui` - Web dashboard interface
- `WebSocket /socket.io/` - Real-time updates

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details