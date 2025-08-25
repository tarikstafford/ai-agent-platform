"""Agent hosting infrastructure"""

from .registry import AgentRegistry, AgentRegistration
from .manager import AgentManager

# Import AgentServer lazily to avoid circular imports with api module
def get_agent_server():
    """Lazy import wrapper for AgentServer to avoid circular imports"""
    from .server import AgentServer
    return AgentServer

__all__ = [
    "AgentRegistry",
    "AgentRegistration", 
    "AgentManager",
    "get_agent_server",
]