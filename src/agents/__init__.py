from .base import BaseAgent, AgentConfig, AgentResponse, AgentState
from .conversational import ConversationalAgent
from .reactive import ReactiveAgent
from .planner import PlannerAgent

# Import LangflowAgent if available
try:
    import sys
    from pathlib import Path
    src_path = str(Path(__file__).parent.parent)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    from langflow_integration import LangflowAgent
    LANGFLOW_AVAILABLE = True
except ImportError:
    LangflowAgent = None
    LANGFLOW_AVAILABLE = False

__all__ = [
    "BaseAgent",
    "AgentConfig", 
    "AgentResponse",
    "AgentState",
    "ConversationalAgent",
    "ReactiveAgent",
    "PlannerAgent",
]

if LANGFLOW_AVAILABLE:
    __all__.append("LangflowAgent")