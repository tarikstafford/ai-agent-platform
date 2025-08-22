import asyncio
from typing import Dict, List, Optional, Any, Type
import json
from pathlib import Path

import structlog

import sys
from pathlib import Path

# Add src to path if not already there
src_path = str(Path(__file__).parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from hosting.registry import AgentRegistry, AgentRegistration, AgentStatus
from agents import BaseAgent, AgentConfig
from agents import ConversationalAgent, ReactiveAgent, PlannerAgent
from tools import CalculatorTool, WebSearchTool, FileReadTool, FileWriteTool, APICallerTool

logger = structlog.get_logger()


class AgentManager:
    """High-level manager for hosted agents"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.registry = AgentRegistry()
        self.config_dir = Path(config_dir) if config_dir else Path("./agent_configs")
        self.config_dir.mkdir(exist_ok=True)
        self.logger = logger.bind(component="agent_manager")
        
        # Available agent types
        self.agent_types: Dict[str, Type[BaseAgent]] = {
            "conversational": ConversationalAgent,
            "reactive": ReactiveAgent,
            "planner": PlannerAgent
        }
        
        # Add LangflowAgent if available
        try:
            from langflow_integration import LangflowAgent
            self.agent_types["langflow"] = LangflowAgent
        except ImportError:
            pass
        
        # Available tools
        self.available_tools = {
            "calculator": CalculatorTool,
            "web_search": WebSearchTool,
            "file_read": FileReadTool,
            "file_write": FileWriteTool,
            "api_caller": APICallerTool
        }
    
    async def create_agent(
        self,
        agent_type: str,
        config: Dict[str, Any],
        tools: List[str] = None,
        name: Optional[str] = None,
        description: str = "",
        tags: List[str] = None,
        auto_start: bool = True
    ) -> str:
        """Create and register a new agent"""
        
        if agent_type not in self.agent_types:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        # Create agent config
        agent_config = AgentConfig(**config)
        
        # Create agent instance
        agent_class = self.agent_types[agent_type]
        agent = agent_class(agent_config)
        
        # Add tools if specified
        if tools and hasattr(agent, 'add_langchain_tool'):
            for tool_name in tools:
                if tool_name in self.available_tools:
                    tool_class = self.available_tools[tool_name]
                    tool_instance = tool_class()
                    agent.add_langchain_tool(tool_instance)
                    self.logger.info("Tool added to agent", tool=tool_name)
        
        # Register agent
        agent_id = await self.registry.register_agent(
            agent=agent,
            name=name,
            description=description,
            tags=tags or [],
            auto_start=auto_start
        )
        
        # Save agent configuration
        await self._save_agent_config(agent_id, {
            "type": agent_type,
            "config": config,
            "tools": tools or [],
            "name": name,
            "description": description,
            "tags": tags or []
        })
        
        self.logger.info("Agent created", agent_id=agent_id, type=agent_type, name=name)
        return agent_id
    
    async def start_agent(self, agent_id: str) -> bool:
        """Start an agent"""
        return await self.registry.start_agent(agent_id)
    
    async def stop_agent(self, agent_id: str) -> bool:
        """Stop an agent"""
        return await self.registry.stop_agent(agent_id)
    
    async def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent"""
        success = await self.registry.remove_agent(agent_id)
        if success:
            await self._delete_agent_config(agent_id)
        return success
    
    async def chat_with_agent(self, agent_id: str, message: str) -> Dict[str, Any]:
        """Send a message to an agent"""
        return await self.registry.execute_agent_request(agent_id, message)
    
    async def execute_agent_task(self, agent_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a structured task on an agent"""
        return await self.registry.execute_agent_request(agent_id, task)
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed agent information"""
        registration = self.registry.get_agent(agent_id)
        if not registration:
            return None
        
        return {
            "id": registration.id,
            "name": registration.name,
            "description": registration.description,
            "status": registration.status.value,
            "created_at": registration.created_at.isoformat(),
            "last_seen": registration.last_seen.isoformat(),
            "endpoint": registration.endpoint,
            "tags": registration.tags,
            "config": {
                "model": registration.config.model,
                "temperature": registration.config.temperature,
                "max_tokens": registration.config.max_tokens,
                "max_iterations": registration.config.max_iterations
            },
            "metrics": {
                "total_requests": registration.metrics.total_requests,
                "successful_requests": registration.metrics.successful_requests,
                "failed_requests": registration.metrics.failed_requests,
                "average_response_time": registration.metrics.average_response_time,
                "uptime_seconds": registration.metrics.uptime_seconds
            }
        }
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents with their information"""
        agents = []
        for registration in self.registry.list_agents():
            agent_info = self.get_agent_info(registration.id)
            if agent_info:
                agents.append(agent_info)
        return agents
    
    def get_agents_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get agents by status"""
        try:
            status_enum = AgentStatus(status)
            registrations = self.registry.get_agents_by_status(status_enum)
            return [self.get_agent_info(reg.id) for reg in registrations]
        except ValueError:
            return []
    
    def get_agents_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Get agents by tag"""
        registrations = self.registry.get_agents_by_tag(tag)
        return [self.get_agent_info(reg.id) for reg in registrations]
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard overview data"""
        stats = self.registry.get_registry_stats()
        agents = self.list_agents()
        
        # Calculate additional metrics
        running_agents = [a for a in agents if a["status"] == "running"]
        busy_agents = [a for a in agents if a["status"] == "busy"]
        error_agents = [a for a in agents if a["status"] == "error"]
        
        # Recent activity
        recent_requests = sum(a["metrics"]["total_requests"] for a in agents)
        avg_response_time = sum(a["metrics"]["average_response_time"] for a in agents) / len(agents) if agents else 0
        
        return {
            "overview": {
                "total_agents": stats["total_agents"],
                "running_agents": len(running_agents),
                "busy_agents": len(busy_agents),
                "error_agents": len(error_agents),
                "total_requests": recent_requests,
                "average_response_time": avg_response_time,
                "success_rate": stats["success_rate"]
            },
            "status_distribution": stats["status_counts"],
            "agents": agents,
            "available_types": list(self.agent_types.keys()),
            "available_tools": list(self.available_tools.keys())
        }
    
    async def load_saved_agents(self) -> None:
        """Load agents from saved configurations"""
        config_files = list(self.config_dir.glob("*.json"))
        
        for config_file in config_files:
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                
                agent_id = await self.create_agent(
                    agent_type=config_data["type"],
                    config=config_data["config"],
                    tools=config_data.get("tools", []),
                    name=config_data.get("name"),
                    description=config_data.get("description", ""),
                    tags=config_data.get("tags", []),
                    auto_start=False
                )
                
                self.logger.info("Loaded saved agent", agent_id=agent_id, config_file=config_file.name)
                
            except Exception as e:
                self.logger.error("Failed to load agent config", config_file=config_file.name, error=str(e))
    
    async def _save_agent_config(self, agent_id: str, config_data: Dict[str, Any]) -> None:
        """Save agent configuration to disk"""
        config_file = self.config_dir / f"{agent_id}.json"
        
        try:
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
        except Exception as e:
            self.logger.error("Failed to save agent config", agent_id=agent_id, error=str(e))
    
    async def _delete_agent_config(self, agent_id: str) -> None:
        """Delete agent configuration file"""
        config_file = self.config_dir / f"{agent_id}.json"
        
        try:
            if config_file.exists():
                config_file.unlink()
        except Exception as e:
            self.logger.error("Failed to delete agent config", agent_id=agent_id, error=str(e))
    
    async def shutdown(self) -> None:
        """Shutdown the agent manager"""
        self.logger.info("Shutting down agent manager")
        
        # Stop all running agents
        for agent_id in list(self.registry.agents.keys()):
            await self.stop_agent(agent_id)
        
        # Cleanup executor
        if hasattr(self.registry, 'executor'):
            self.registry.executor.shutdown(wait=False)