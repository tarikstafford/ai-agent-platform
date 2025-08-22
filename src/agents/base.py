from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Callable
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
    a2a_enabled: bool = Field(default=True, description="Enable A2A communication")
    a2a_capabilities: List[str] = Field(default_factory=list, description="A2A capabilities")


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
    
    def __init__(self, config: AgentConfig, agent_id: Optional[str] = None):
        self.config = config
        self.agent_id = agent_id or f"agent_{id(self)}"
        self.state = AgentState.IDLE
        self.memory: List[Dict[str, Any]] = []
        self.tools: Dict[str, Any] = {}
        self.iteration_count = 0
        self.logger = logger.bind(agent_name=config.name, agent_id=self.agent_id)
        
        # A2A communication components
        self.a2a_communicator = None
        self.a2a_discovery = None
        self.a2a_message_handlers: Dict[str, List[Callable]] = {}
        self.a2a_task_handlers: Dict[str, Callable] = {}
        
        # Initialize A2A if enabled
        if config.a2a_enabled:
            self._init_a2a_communication()
        
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
    
    # A2A Communication Methods
    
    def _init_a2a_communication(self):
        """Initialize A2A communication components"""
        try:
            import sys
            from pathlib import Path
            
            # Add src to path if not already there
            src_path = str(Path(__file__).parent.parent)
            if src_path not in sys.path:
                sys.path.insert(0, src_path)
            
            from a2a import A2ACommunicator, AgentDiscovery
            from a2a.protocol import AgentCapability
            
            # Initialize communicator
            self.a2a_communicator = A2ACommunicator(
                agent_id=self.agent_id,
                agent_name=self.config.name
            )
            
            # Initialize discovery
            self.a2a_discovery = AgentDiscovery(
                agent_id=self.agent_id,
                communicator=self.a2a_communicator
            )
            
            # Set capabilities from config
            capabilities = []
            for cap_name in self.config.a2a_capabilities:
                capability = AgentCapability(
                    name=cap_name,
                    description=f"{cap_name} capability",
                    version="1.0"
                )
                capabilities.append(capability)
            
            self.a2a_discovery.set_own_capabilities(capabilities)
            
            # Register default message handlers
            self._register_default_a2a_handlers()
            
            self.logger.info("A2A communication initialized")
            
        except ImportError as e:
            self.logger.warning("A2A communication not available", error=str(e))
            self.config.a2a_enabled = False
    
    def _register_default_a2a_handlers(self):
        """Register default A2A message handlers"""
        if not self.a2a_communicator:
            return
        
        from a2a.protocol import A2AMessageType
        
        # Register default handlers
        self.a2a_communicator.register_message_handler(
            A2AMessageType.TASK_REQUEST,
            self._handle_task_request
        )
        self.a2a_communicator.register_message_handler(
            A2AMessageType.COLLABORATION_REQUEST,
            self._handle_collaboration_request
        )
        self.a2a_communicator.register_message_handler(
            A2AMessageType.INFO_REQUEST,
            self._handle_info_request
        )
        self.a2a_communicator.register_message_handler(
            A2AMessageType.STATUS_REQUEST,
            self._handle_status_request
        )
    
    async def start_a2a_communication(self):
        """Start A2A communication services"""
        if not self.config.a2a_enabled or not self.a2a_communicator:
            return
        
        await self.a2a_communicator.start()
        await self.a2a_discovery.start()
        self.logger.info("A2A communication services started")
    
    async def stop_a2a_communication(self):
        """Stop A2A communication services"""
        if not self.config.a2a_enabled:
            return
        
        if self.a2a_discovery:
            await self.a2a_discovery.stop()
        if self.a2a_communicator:
            await self.a2a_communicator.stop()
        
        self.logger.info("A2A communication services stopped")
    
    async def send_message_to_agent(self, recipient_id: str, message_type: str, payload: Dict[str, Any]) -> str:
        """Send a message to another agent"""
        if not self.a2a_communicator:
            raise Exception("A2A communication not enabled")
        
        from a2a.protocol import A2AMessage, A2AMessageType
        
        message = A2AMessage(
            type=A2AMessageType(message_type),
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            payload=payload
        )
        
        return await self.a2a_communicator.send_message(message)
    
    async def delegate_task_to_agent(self, agent_id: str, task_type: str, task_data: Dict[str, Any]) -> bool:
        """Delegate a task to another agent"""
        if not self.a2a_communicator:
            raise Exception("A2A communication not enabled")
        
        from a2a.protocol import A2ARequest, A2AMessageType, TaskDelegation
        
        task_delegation = TaskDelegation(
            task_type=task_type,
            task_description=f"Task delegated from {self.config.name}",
            task_data=task_data
        )
        
        request = A2ARequest(
            type=A2AMessageType.TASK_REQUEST,
            sender_id=self.agent_id,
            recipient_id=agent_id,
            payload={"task_delegation": task_delegation.dict()}
        )
        
        try:
            response = await self.a2a_communicator.send_request(request)
            return response.success
        except Exception as e:
            self.logger.error("Task delegation failed", error=str(e))
            return False
    
    async def discover_agents(self, required_capabilities: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Discover other agents with specific capabilities"""
        if not self.a2a_discovery:
            return []
        
        profiles = await self.a2a_discovery.discover_agents(required_capabilities)
        
        return [
            {
                "agent_id": profile.agent_id,
                "name": profile.name,
                "description": profile.description,
                "capabilities": [cap.name for cap in profile.capabilities],
                "status": profile.status,
                "load": profile.load
            }
            for profile in profiles
        ]
    
    async def collaborate_with_agents(self, agent_ids: List[str], collaboration_title: str, collaboration_description: str) -> str:
        """Initiate collaboration with other agents"""
        if not self.a2a_communicator:
            raise Exception("A2A communication not enabled")
        
        from a2a.protocol import A2AMessage, A2AMessageType, CollaborationRequest
        
        collaboration = CollaborationRequest(
            title=collaboration_title,
            description=collaboration_description,
            required_agents=len(agent_ids),
            coordinator_id=self.agent_id
        )
        
        # Send collaboration request to each agent
        for agent_id in agent_ids:
            message = A2AMessage(
                type=A2AMessageType.COLLABORATION_REQUEST,
                sender_id=self.agent_id,
                recipient_id=agent_id,
                payload={"collaboration": collaboration.dict()}
            )
            
            await self.a2a_communicator.send_message(message)
        
        return collaboration.collaboration_id
    
    def register_a2a_message_handler(self, message_type: str, handler: Callable):
        """Register custom A2A message handler"""
        if not self.a2a_communicator:
            return
        
        from a2a.protocol import A2AMessageType
        
        self.a2a_communicator.register_message_handler(
            A2AMessageType(message_type),
            handler
        )
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """Register handler for specific task type"""
        self.a2a_task_handlers[task_type] = handler
        self.logger.info("Task handler registered", task_type=task_type)
    
    async def _handle_task_request(self, message):
        """Handle incoming task requests"""
        try:
            payload = message.payload
            task_data = payload.get("task_delegation", {})
            task_type = task_data.get("task_type")
            
            if task_type in self.a2a_task_handlers:
                # Execute task handler
                handler = self.a2a_task_handlers[task_type]
                result = await handler(task_data.get("task_data", {}))
                
                # Send success response
                from a2a.protocol import A2AResponse, A2AMessageType
                
                response = A2AResponse(
                    type=A2AMessageType.TASK_RESPONSE,
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    correlation_id=message.id,
                    success=True,
                    result=result
                )
                
                await self.a2a_communicator.send_response(response)
            else:
                # Send rejection response
                from a2a.protocol import A2AResponse, A2AMessageType
                
                response = A2AResponse(
                    type=A2AMessageType.TASK_REJECT,
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    correlation_id=message.id,
                    success=False,
                    error_message=f"No handler for task type: {task_type}"
                )
                
                await self.a2a_communicator.send_response(response)
                
        except Exception as e:
            self.logger.error("Error handling task request", error=str(e))
    
    async def _handle_collaboration_request(self, message):
        """Handle collaboration requests"""
        # Default implementation - can be overridden by subclasses
        from a2a.protocol import A2AResponse, A2AMessageType
        
        response = A2AResponse(
            type=A2AMessageType.COLLABORATION_ACCEPT,
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            correlation_id=message.id,
            success=True,
            result={"status": "accepted"}
        )
        
        await self.a2a_communicator.send_response(response)
    
    async def _handle_info_request(self, message):
        """Handle information requests"""
        from a2a.protocol import A2AResponse, A2AMessageType
        
        info = {
            "agent_id": self.agent_id,
            "name": self.config.name,
            "description": self.config.description,
            "state": self.state.value,
            "capabilities": self.config.a2a_capabilities,
            "memory_entries": len(self.memory),
            "available_tools": list(self.tools.keys())
        }
        
        response = A2AResponse(
            type=A2AMessageType.INFO_RESPONSE,
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            correlation_id=message.id,
            success=True,
            result=info
        )
        
        await self.a2a_communicator.send_response(response)
    
    async def _handle_status_request(self, message):
        """Handle status requests"""
        from a2a.protocol import A2AResponse, A2AMessageType
        
        status = {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "iteration_count": self.iteration_count,
            "uptime": (datetime.now() - self.logger._context.get("start_time", datetime.now())).total_seconds(),
            "memory_usage": len(self.memory)
        }
        
        response = A2AResponse(
            type=A2AMessageType.STATUS_RESPONSE,
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            correlation_id=message.id,
            success=True,
            result=status
        )
        
        await self.a2a_communicator.send_response(response)