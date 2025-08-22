from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
import structlog

logger = structlog.get_logger()


class AgentState(str, Enum):
    """Agent state enumeration"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"
    ERROR = "error"
    COMPLETED = "completed"


class AgentConfig(BaseModel):
    """Configuration for an agent"""
    model_config = ConfigDict(extra="allow")
    
    name: str = Field(..., description="Agent name")
    description: str = Field(default="", description="Agent description")
    model: str = Field(default="gpt-4", description="LLM model to use")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature for LLM")
    max_tokens: int = Field(default=2000, gt=0, description="Maximum tokens for response")
    max_iterations: int = Field(default=10, gt=0, description="Maximum iterations for task")
    timeout_seconds: int = Field(default=300, gt=0, description="Timeout in seconds")
    tools: List[str] = Field(default_factory=list, description="Available tools")
    memory_enabled: bool = Field(default=True, description="Enable memory")
    verbose: bool = Field(default=False, description="Verbose logging")


@dataclass
class AgentResponse:
    """Response from an agent"""
    content: str
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    iterations: int = 0
    state: AgentState = AgentState.COMPLETED


class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.state = AgentState.IDLE
        self.memory: List[Dict[str, Any]] = []
        self.tools: Dict[str, Any] = {}
        self.iteration_count = 0
        self.logger = logger.bind(agent_name=config.name)
        
    @abstractmethod
    async def think(self, input_data: Union[str, Dict[str, Any]]) -> AgentResponse:
        """Process input and generate a response"""
        pass
    
    @abstractmethod
    async def act(self, action: Dict[str, Any]) -> Any:
        """Execute an action"""
        pass
    
    async def run(self, input_data: Union[str, Dict[str, Any]]) -> AgentResponse:
        """Main execution method"""
        self.logger.info("Agent starting", input=input_data)
        self.state = AgentState.THINKING
        self.iteration_count = 0
        
        try:
            response = await self.think(input_data)
            
            if self.config.memory_enabled:
                self.memory.append({
                    "input": input_data,
                    "output": response.content,
                    "timestamp": response.timestamp,
                    "success": response.success
                })
            
            self.state = AgentState.COMPLETED
            self.logger.info("Agent completed", success=response.success)
            return response
            
        except Exception as e:
            self.state = AgentState.ERROR
            self.logger.error("Agent error", error=str(e))
            return AgentResponse(
                content="",
                success=False,
                error=str(e),
                state=AgentState.ERROR
            )
    
    def add_tool(self, name: str, tool: Any) -> None:
        """Add a tool to the agent"""
        self.tools[name] = tool
        self.logger.info("Tool added", tool_name=name)
    
    def get_memory(self) -> List[Dict[str, Any]]:
        """Get agent memory"""
        return self.memory
    
    def clear_memory(self) -> None:
        """Clear agent memory"""
        self.memory.clear()
        self.logger.info("Memory cleared")
    
    def get_state(self) -> AgentState:
        """Get current agent state"""
        return self.state