# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI Agent Workflow platform written in Python that provides:
- Multiple agent types (Conversational, Reactive, Planner)
- Extensible tool system for agent capabilities
- Memory management with vector and conversation storage
- Async-first architecture for concurrent operations
- Web-based hosting platform with dashboard and REST API
- Real-time monitoring and metrics collection
- Agent persistence and lifecycle management

## Key Commands

### Development
```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=src --cov-report=term

# Format code
black src/ tests/ examples/

# Lint code
ruff check src/ tests/ examples/

# Type check
mypy src/

# Run pre-commit hooks
pre-commit run --all-files
```

### Running the Platform
```bash
# Start the hosting platform
python run_server.py --host 127.0.0.1 --port 8000

# Start with Docker
docker-compose up -d

# Access dashboard
open http://localhost:8000/api/dashboard/ui
```

### Running Examples
```bash
# Test platform capabilities
python examples/platform_demo.py

# Basic agent examples
python examples/basic_usage.py

# Research assistant example
python examples/research_assistant.py
```

## Architecture

### Core Components

1. **Agents** (`src/agents/`)
   - `BaseAgent`: Abstract base class defining agent interface
   - `ConversationalAgent`: Maintains dialogue history
   - `ReactiveAgent`: Uses tools via ReAct pattern
   - `PlannerAgent`: Breaks down goals into executable tasks

2. **Tools** (`src/tools/`)
   - `BaseTool`: LangChain-compatible tool base class
   - Built-in tools: Calculator, WebSearch, FileOperations, APICaller
   - Tools are added to ReactiveAgent instances

3. **Memory** (`src/memory/`)
   - `BaseMemory`: Abstract memory interface
   - `ConversationMemory`: Simple list-based memory
   - `VectorMemory`: ChromaDB-based semantic search

4. **Hosting** (`src/hosting/`)
   - `AgentRegistry`: Central registry for agent lifecycle management
   - `AgentManager`: High-level agent management with persistence
   - `AgentServer`: Main server with CLI interface

5. **API** (`src/api/`)
   - `Flask` app with REST endpoints for agent management
   - `WebSocket` support for real-time updates
   - `Dashboard` serving for web interface

6. **Key Design Patterns**
   - All agents inherit from `BaseAgent` and implement `think()` and `act()` methods
   - Tools follow LangChain tool interface for compatibility
   - Async/await used throughout for concurrent operations
   - Pydantic models for configuration and validation
   - Registry pattern for agent management
   - REST API with WebSocket for real-time features

### Important Files

- `pyproject.toml`: Project configuration, dependencies, and tool settings
- `.env.example`: Template for API keys and configuration
- `Makefile`: Common development tasks

### Testing Approach

- Unit tests in `tests/` mirror source structure
- Heavy use of mocking for external dependencies
- Fixtures in `tests/conftest.py` for common test needs
- Run tests before committing changes

## Common Tasks

### Adding a New Agent Type

1. Create new file in `src/agents/`
2. Inherit from `BaseAgent`
3. Implement `think()` and `act()` methods
4. Add to `src/agents/__init__.py`
5. Create tests in `tests/test_agents.py`

### Adding a New Tool

1. Create new file in `src/tools/`
2. Inherit from `BaseTool`
3. Define `args_schema` with Pydantic model
4. Implement `execute()` method
5. Add to `src/tools/__init__.py`
6. Create tests in `tests/test_tools.py`

### Debugging Agents

- Set `verbose=True` in `AgentConfig`
- Check agent state with `agent.get_state()`
- Review memory with `agent.get_memory()`
- Use structured logging via `structlog`

## Code Style

- Use type hints for all function parameters and returns
- Follow existing patterns for async/await usage
- Keep tool implementations focused and single-purpose
- Write comprehensive docstrings for public methods
- Ensure all new code has corresponding tests