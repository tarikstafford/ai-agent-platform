# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a comprehensive **AI Agent Hosting Platform** written in Python that provides enterprise-grade agent management with visual workflow creation capabilities. It's a production-ready system for building, hosting, and managing multiple AI agents with a modern web interface.

### Key Features
- **4 Agent Types**: Conversational, Reactive, Planner, and Visual Workflow agents
- **Visual Workflow Builder**: Integrated Langflow for drag-and-drop agent creation
- **Web-based Hosting Platform**: Complete dashboard for agent management
- **REST API + WebSocket**: Full programmatic control with real-time updates
- **Agent Persistence**: Automatic save/restore of agent configurations
- **Real-time Monitoring**: Live metrics, status tracking, and performance analytics
- **Tool System**: Extensible framework with built-in tools (Calculator, WebSearch, FileOps, API)
- **Memory Management**: Vector and conversation-based memory systems
- **Production Ready**: Docker deployment, CI/CD structure, comprehensive testing

## Key Commands

### Quick Setup
```bash
# One-command setup (installs dependencies, creates .env)
python setup_platform.py

# Verify setup
python check_setup.py

# Start platform
python run_server.py --host 127.0.0.1 --port 8000
```

### Development
```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# Format and lint
make format  # black + ruff
make lint    # ruff check
make type-check  # mypy

# All development tasks
make all     # clean, install, format, lint, type-check, test
```

### Running the Platform
```bash
# Start the hosting platform
python run_server.py --host 127.0.0.1 --port 8000

# With Docker
docker-compose up -d

# Access interfaces
open http://localhost:8000/api/dashboard/ui        # Main Dashboard
open http://localhost:8000/api/dashboard/builder   # Visual Workflow Builder
```

### Running Examples
```bash
# Test platform capabilities
python examples/platform_demo.py

# Test visual workflow integration  
python examples/visual_workflow_demo.py

# Basic agent examples
python examples/basic_usage.py

# Research assistant example
python examples/research_assistant.py
```

## Architecture

### Core Components

1. **Agents** (`src/agents/`)
   - `BaseAgent`: Abstract base class with `think()` and `act()` methods
   - `ConversationalAgent`: Chat-based agents with conversation history
   - `ReactiveAgent`: Tool-using agents via ReAct pattern
   - `PlannerAgent`: Task breakdown and execution planning
   - `LangflowAgent`: **NEW** - Visual workflow execution engine

2. **Visual Workflow System** (`src/langflow_integration/`)
   - `LangflowServer`: Manages embedded Langflow server
   - `WorkflowBuilder`: High-level workflow creation and management
   - `WorkflowManager`: Template and storage management
   - `LangflowAgent`: Agent that executes visual workflows

3. **Hosting Infrastructure** (`src/hosting/`)
   - `AgentRegistry`: Central registry with lifecycle management and metrics
   - `AgentManager`: High-level management with persistence and auto-loading
   - `AgentServer`: Main server with CLI interface and graceful shutdown

4. **Web Platform** (`src/api/` + `src/dashboard/`)
   - **REST API**: Complete CRUD operations for agents and workflows
   - **WebSocket**: Real-time status updates and monitoring
   - **Dashboard**: Modern web interface with embedded visual builder
   - **Langflow Routes**: API endpoints for visual workflow management

5. **Tools System** (`src/tools/`)
   - `BaseTool`: LangChain-compatible base class
   - Built-in tools: Calculator, WebSearch, FileOperations, APICaller
   - Automatic tool integration with ReactiveAgent

6. **Memory Systems** (`src/memory/`)
   - `ConversationMemory`: Simple dialogue history
   - `VectorMemory`: ChromaDB-based semantic search and retrieval

7. **Workflows** (`src/workflows/`)
   - **NEW**: Infrastructure for multi-agent workflow orchestration
   - Sequential and parallel execution patterns

### Architecture Patterns
- **Agent-Centric Design**: All functionality built around BaseAgent interface
- **Plugin Architecture**: Extensible tools and memory systems
- **Registry Pattern**: Centralized agent lifecycle management
- **Event-Driven**: WebSocket updates for real-time monitoring
- **Async-First**: Concurrent agent execution and request handling
- **Configuration-Driven**: Pydantic models for type-safe configuration
- **Microservice-Ready**: Containerized with service separation

### Key Files

**Core Configuration:**
- `pyproject.toml`: Complete project configuration with all dependencies
- `requirements.txt`: Flattened dependencies for simple installation
- `.env.example`: Template for API keys and platform configuration
- `docker-compose.yml`: Multi-service deployment configuration

**Entry Points:**
- `run_server.py`: Main platform server
- `setup_platform.py`: One-command setup script
- `check_setup.py`: Installation verification

**Documentation:**
- `README.md`: Main project documentation
- `VISUAL_WORKFLOWS.md`: Visual workflow builder guide
- `QUICKSTART.md`: Quick start instructions
- `GITHUB_SETUP.md`: Repository setup guide

## Agent Types and Usage

### 1. Conversational Agent
```python
from src.agents import ConversationalAgent, AgentConfig

config = AgentConfig(name="ChatBot", model="gpt-3.5-turbo")
agent = ConversationalAgent(config)
response = await agent.run("Hello!")
```

### 2. Reactive Agent (with Tools)
```python
from src.agents import ReactiveAgent
from src.tools import CalculatorTool, WebSearchTool

agent = ReactiveAgent(config)
agent.add_langchain_tool(CalculatorTool())
agent.add_langchain_tool(WebSearchTool())
response = await agent.run("What's 15% of 200?")
```

### 3. Planner Agent
```python
from src.agents import PlannerAgent

agent = PlannerAgent(config)
response = await agent.run("Plan a product launch campaign")
# Returns structured task breakdown
```

### 4. Visual Workflow Agent (NEW!)
```python
from src.agents import LangflowAgent

# Create from visual workflow
agent = LangflowAgent(config, flow_id="workflow-uuid")
response = await agent.run("Process with visual workflow")
```

## Platform Management

### Hosting Multiple Agents
```python
from src.hosting import AgentManager

manager = AgentManager()

# Create agents
agent_id = await manager.create_agent(
    agent_type="conversational",
    config={"name": "Support", "model": "gpt-4"},
    auto_start=True
)

# Chat with agent
response = await manager.chat_with_agent(agent_id, "Help me")

# Get platform overview
dashboard_data = manager.get_dashboard_data()
```

### Visual Workflow Creation
```python
from src.langflow_integration import WorkflowBuilder

builder = WorkflowBuilder()
await builder.initialize()

# Create from template
flow_id = builder.create_from_template("simple_chat", "my_bot")

# Create agent from workflow
agent_id = await manager.create_agent(
    agent_type="langflow",
    config={"name": "VisualBot", "flow_id": flow_id}
)
```

## API Usage

### REST API
```bash
# Agent Management
GET    /api/agents/                 # List agents
POST   /api/agents/                 # Create agent  
GET    /api/agents/{id}             # Get agent details
DELETE /api/agents/{id}             # Delete agent
POST   /api/agents/{id}/start       # Start agent
POST   /api/agents/{id}/stop        # Stop agent
POST   /api/agents/{id}/chat        # Chat with agent

# Visual Workflows  
GET    /api/langflow/status         # Check Langflow status
POST   /api/langflow/initialize     # Initialize Langflow
GET    /api/langflow/workflows      # List workflows
POST   /api/langflow/workflows      # Create workflow
POST   /api/langflow/agents         # Create agent from workflow

# Dashboard
GET    /api/dashboard/              # Get dashboard data
GET    /api/dashboard/ui            # Web dashboard
GET    /api/dashboard/builder       # Visual workflow builder
```

### WebSocket Events
- `agent_update`: Real-time agent status changes
- `dashboard_update`: Platform metrics updates
- `workflow_update`: Visual workflow status changes

## Development Workflow

### Adding New Agent Types

1. **Create Agent Class** (`src/agents/new_agent.py`):
```python
from .base import BaseAgent, AgentResponse

class NewAgent(BaseAgent):
    async def think(self, input_data):
        # Agent logic
        return AgentResponse(content="result")
    
    async def act(self, action):
        # Action execution
        return {"status": "completed"}
```

2. **Register Agent** (`src/agents/__init__.py`):
```python
from .new_agent import NewAgent
__all__.append("NewAgent")
```

3. **Add to Manager** (`src/hosting/manager.py`):
```python
self.agent_types["new_type"] = NewAgent
```

4. **Create Tests** (`tests/test_agents.py`):
```python
def test_new_agent():
    agent = NewAgent(config)
    # Test agent functionality
```

### Adding New Tools

1. **Create Tool** (`src/tools/new_tool.py`):
```python
from .base import BaseTool

class NewTool(BaseTool):
    name = "new_tool"
    description = "Tool description"
    
    def execute(self, input_param):
        # Tool logic
        return "result"
```

2. **Register Tool** (`src/tools/__init__.py`):
```python
from .new_tool import NewTool
__all__.append("NewTool")
```

3. **Add to Manager** (`src/hosting/manager.py`):
```python
self.available_tools["new_tool"] = NewTool
```

### Debugging and Monitoring

**Agent Debugging:**
```python
# Enable verbose logging
config = AgentConfig(name="Debug", verbose=True)

# Check agent state
agent.get_state()  # Returns AgentState enum

# Review agent memory
agent.get_memory()  # Returns conversation history

# Monitor metrics
agent_info = manager.get_agent_info(agent_id)
print(agent_info["metrics"])
```

**Platform Monitoring:**
```python
# Get platform statistics
stats = manager.get_registry_stats()

# Monitor specific agents
running_agents = manager.get_agents_by_status("running")

# Check agent performance
dashboard_data = manager.get_dashboard_data()
```

## Testing Strategy

### Test Structure
- `tests/test_agents.py`: Agent functionality tests
- `tests/test_tools.py`: Tool execution tests
- `tests/test_hosting.py`: Platform management tests  
- `tests/test_api.py`: API endpoint tests
- `tests/conftest.py`: Shared fixtures and utilities

### Running Tests
```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_agents.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Test specific functionality
pytest tests/ -k "test_conversational" -v
```

### Mock Strategy
- Heavy use of `pytest-mock` for external dependencies
- Mock LLM calls in tests to avoid API costs
- Mock file system operations for safety
- Mock network requests for reliability

## Deployment

### Local Development
```bash
python run_server.py --debug --host 127.0.0.1 --port 8000
```

### Docker Deployment
```bash
docker-compose up -d  # Full platform with nginx
docker logs ai-agent-platform  # Check logs
```

### Production Considerations
- Set strong secret keys in production
- Use proper database for agent persistence  
- Configure monitoring and alerting
- Set up SSL/TLS termination
- Scale with multiple instances behind load balancer

## Code Standards

### Style Guidelines
- **Type Hints**: All functions have complete type annotations
- **Docstrings**: All public methods have comprehensive docstrings
- **Error Handling**: Proper exception handling with structured logging
- **Async Patterns**: Consistent async/await usage throughout
- **Configuration**: Pydantic models for all configuration objects

### Quality Checks
- **Black**: Code formatting (line length 100)
- **Ruff**: Fast linting with comprehensive rule set
- **MyPy**: Type checking with strict configuration
- **Pytest**: Comprehensive test coverage
- **Pre-commit**: Automated quality checks on commit

### Security Practices
- **Input Validation**: All user inputs validated with Pydantic
- **API Key Management**: Environment-based configuration
- **Path Traversal Protection**: Secure file operations
- **Request Sanitization**: Clean all API inputs
- **CORS Configuration**: Proper cross-origin policies

## Platform Unique Features

### Visual Workflow Integration
- **First-of-its-kind**: Embedded Langflow in agent platform
- **Drag-and-Drop**: Visual workflow creation without coding
- **Template Library**: Pre-built workflow patterns
- **Real-time Testing**: Immediate workflow validation
- **Agent Integration**: One-click agent creation from workflows

### Enterprise Features
- **Multi-tenant Ready**: Agent isolation and management
- **Real-time Monitoring**: Live metrics and status updates
- **Scalable Architecture**: Horizontal scaling support
- **Professional UI**: Modern dashboard with embedded tools
- **Comprehensive API**: Full platform control via REST API

This platform represents a complete, production-ready AI agent hosting solution with unique visual workflow capabilities.