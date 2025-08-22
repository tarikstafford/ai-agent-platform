from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import asyncio
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel, Field
import structlog

import sys
from pathlib import Path

# Add src to path if not already there
src_path = str(Path(__file__).parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from agents import BaseAgent, AgentConfig, AgentState

logger = structlog.get_logger()


class AgentStatus(str, Enum):
    """Status of a hosted agent"""
    STARTING = "starting"
    RUNNING = "running"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class AgentMetrics:
    """Metrics for an agent"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_activity: Optional[datetime] = None
    uptime_seconds: float = 0.0
    memory_usage_mb: float = 0.0


class AgentRegistration(BaseModel):
    """Registration information for a hosted agent"""
    id: str = Field(..., description="Unique agent ID")
    name: str = Field(..., description="Agent name")
    description: str = Field(default="", description="Agent description")
    config: AgentConfig = Field(..., description="Agent configuration")
    status: AgentStatus = Field(default=AgentStatus.STARTING, description="Current status")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")
    last_seen: datetime = Field(default_factory=datetime.now, description="Last activity")
    metrics: AgentMetrics = Field(default_factory=AgentMetrics, description="Agent metrics")
    endpoint: Optional[str] = Field(default=None, description="Agent endpoint URL")
    tags: List[str] = Field(default_factory=list, description="Agent tags")
    
    class Config:
        arbitrary_types_allowed = True


class AgentRegistry:
    """Registry for managing hosted agents"""
    
    def __init__(self):
        self.agents: Dict[str, AgentRegistration] = {}
        self.running_agents: Dict[str, BaseAgent] = {}
        self.agent_tasks: Dict[str, asyncio.Task] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.logger = logger.bind(component="agent_registry")
        
    async def register_agent(
        self,
        agent: BaseAgent,
        name: Optional[str] = None,
        description: str = "",
        tags: List[str] = None,
        auto_start: bool = True
    ) -> str:
        """Register a new agent"""
        agent_id = str(uuid.uuid4())
        
        registration = AgentRegistration(
            id=agent_id,
            name=name or agent.config.name,
            description=description,
            config=agent.config,
            status=AgentStatus.STARTING,
            tags=tags or [],
            endpoint=f"/agents/{agent_id}"
        )
        
        self.agents[agent_id] = registration
        self.running_agents[agent_id] = agent
        
        self.logger.info("Agent registered", agent_id=agent_id, name=registration.name)
        
        if auto_start:
            await self.start_agent(agent_id)
        
        return agent_id
    
    async def start_agent(self, agent_id: str) -> bool:
        """Start a registered agent"""
        if agent_id not in self.agents:
            self.logger.error("Agent not found", agent_id=agent_id)
            return False
        
        registration = self.agents[agent_id]
        agent = self.running_agents[agent_id]
        
        try:
            registration.status = AgentStatus.RUNNING
            registration.last_seen = datetime.now()
            registration.metrics.uptime_seconds = 0.0
            
            # Create background task for agent monitoring
            task = asyncio.create_task(self._monitor_agent(agent_id))
            self.agent_tasks[agent_id] = task
            
            self.logger.info("Agent started", agent_id=agent_id)
            return True
            
        except Exception as e:
            registration.status = AgentStatus.ERROR
            self.logger.error("Failed to start agent", agent_id=agent_id, error=str(e))
            return False
    
    async def stop_agent(self, agent_id: str) -> bool:
        """Stop a running agent"""
        if agent_id not in self.agents:
            return False
        
        registration = self.agents[agent_id]
        
        # Cancel monitoring task
        if agent_id in self.agent_tasks:
            self.agent_tasks[agent_id].cancel()
            del self.agent_tasks[agent_id]
        
        registration.status = AgentStatus.STOPPED
        self.logger.info("Agent stopped", agent_id=agent_id)
        return True
    
    async def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from registry"""
        if agent_id not in self.agents:
            return False
        
        await self.stop_agent(agent_id)
        
        del self.agents[agent_id]
        if agent_id in self.running_agents:
            del self.running_agents[agent_id]
        
        self.logger.info("Agent removed", agent_id=agent_id)
        return True
    
    async def execute_agent_request(self, agent_id: str, input_data: Any) -> Dict[str, Any]:
        """Execute a request on a specific agent"""
        if agent_id not in self.agents or agent_id not in self.running_agents:
            return {"error": "Agent not found", "success": False}
        
        registration = self.agents[agent_id]
        agent = self.running_agents[agent_id]
        
        if registration.status != AgentStatus.RUNNING:
            return {"error": f"Agent is {registration.status.value}", "success": False}
        
        start_time = datetime.now()
        registration.status = AgentStatus.BUSY
        registration.metrics.total_requests += 1
        
        try:
            # Execute agent request
            response = await agent.run(input_data)
            
            # Update metrics
            duration = (datetime.now() - start_time).total_seconds()
            registration.metrics.last_activity = datetime.now()
            registration.metrics.successful_requests += 1
            
            # Update average response time
            total = registration.metrics.total_requests
            current_avg = registration.metrics.average_response_time
            registration.metrics.average_response_time = (
                (current_avg * (total - 1) + duration) / total
            )
            
            registration.status = AgentStatus.RUNNING
            registration.last_seen = datetime.now()
            
            return {
                "success": response.success,
                "content": response.content,
                "metadata": response.metadata,
                "error": response.error,
                "duration_seconds": duration
            }
            
        except Exception as e:
            registration.metrics.failed_requests += 1
            registration.status = AgentStatus.ERROR
            self.logger.error("Agent request failed", agent_id=agent_id, error=str(e))
            
            return {
                "error": str(e),
                "success": False,
                "duration_seconds": (datetime.now() - start_time).total_seconds()
            }
    
    def get_agent(self, agent_id: str) -> Optional[AgentRegistration]:
        """Get agent registration info"""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[AgentRegistration]:
        """List all registered agents"""
        return list(self.agents.values())
    
    def get_agents_by_status(self, status: AgentStatus) -> List[AgentRegistration]:
        """Get agents by status"""
        return [agent for agent in self.agents.values() if agent.status == status]
    
    def get_agents_by_tag(self, tag: str) -> List[AgentRegistration]:
        """Get agents by tag"""
        return [agent for agent in self.agents.values() if tag in agent.tags]
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        total_agents = len(self.agents)
        status_counts = {}
        
        for status in AgentStatus:
            status_counts[status.value] = len(self.get_agents_by_status(status))
        
        total_requests = sum(agent.metrics.total_requests for agent in self.agents.values())
        total_successful = sum(agent.metrics.successful_requests for agent in self.agents.values())
        total_failed = sum(agent.metrics.failed_requests for agent in self.agents.values())
        
        return {
            "total_agents": total_agents,
            "status_counts": status_counts,
            "total_requests": total_requests,
            "successful_requests": total_successful,
            "failed_requests": total_failed,
            "success_rate": total_successful / total_requests if total_requests > 0 else 0.0
        }
    
    async def _monitor_agent(self, agent_id: str):
        """Background task to monitor agent health"""
        start_time = datetime.now()
        
        while agent_id in self.agents:
            try:
                registration = self.agents[agent_id]
                
                # Update uptime
                registration.metrics.uptime_seconds = (
                    datetime.now() - start_time
                ).total_seconds()
                
                # Check if agent is responsive
                if registration.status == AgentStatus.RUNNING:
                    time_since_activity = datetime.now() - registration.last_seen
                    if time_since_activity.total_seconds() > 300:  # 5 minutes
                        registration.status = AgentStatus.IDLE
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Agent monitoring error", agent_id=agent_id, error=str(e))
                await asyncio.sleep(60)