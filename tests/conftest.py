import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil
from typing import Generator, AsyncGenerator

from src.agents import AgentConfig, BaseAgent


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def agent_config() -> AgentConfig:
    """Create a test agent configuration"""
    return AgentConfig(
        name="test_agent",
        description="Test agent for unit tests",
        model="gpt-3.5-turbo",
        temperature=0.5,
        max_tokens=1000,
        max_iterations=5,
        timeout_seconds=60,
        verbose=True
    )


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing"""
    return {
        "content": "This is a mock response",
        "metadata": {
            "model": "gpt-3.5-turbo",
            "tokens": {"prompt": 10, "completion": 5, "total": 15}
        }
    }


@pytest.fixture
async def async_client():
    """Create an async HTTP client for testing"""
    import httpx
    async with httpx.AsyncClient() as client:
        yield client