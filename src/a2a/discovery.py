"""
Agent Discovery System

This module provides agent discovery capabilities for the A2A protocol.
"""

import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import json

import structlog
from .protocol import (
    A2AMessage, A2AMessageType, A2ARequest, A2AResponse,
    AgentProfile, AgentCapability
)

logger = structlog.get_logger()


class AgentDiscovery:
    """Agent discovery and capability management"""
    
    def __init__(self, agent_id: str, communicator):
        self.agent_id = agent_id
        self.communicator = communicator
        self.logger = logger.bind(component="agent_discovery", agent_id=agent_id)
        
        # Own capabilities
        self.own_capabilities: List[AgentCapability] = []
        self.own_profile: Optional[AgentProfile] = None
        
        # Discovery cache
        self.discovered_agents: Dict[str, AgentProfile] = {}
        self.capability_index: Dict[str, Set[str]] = {}  # capability -> set of agent_ids
        
        # Discovery settings
        self.discovery_interval = 300  # 5 minutes
        self.agent_ttl = 600  # 10 minutes
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.running = False
        
        # Register message handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register discovery message handlers"""
        self.communicator.register_message_handler(
            A2AMessageType.DISCOVERY_REQUEST, 
            self._handle_discovery_request
        )
        self.communicator.register_message_handler(
            A2AMessageType.DISCOVERY_RESPONSE,
            self._handle_discovery_response
        )
        self.communicator.register_message_handler(
            A2AMessageType.PING,
            self._handle_ping
        )
        self.communicator.register_message_handler(
            A2AMessageType.PONG,
            self._handle_pong
        )
    
    async def start(self):
        """Start the discovery service"""
        if self.running:
            return
        
        self.running = True
        
        # Start background tasks
        self.background_tasks.extend([
            asyncio.create_task(self._periodic_discovery()),
            asyncio.create_task(self._cleanup_stale_agents())
        ])
        
        # Initial discovery broadcast
        await self._broadcast_discovery()
        
        self.logger.info("Agent discovery started")
    
    async def stop(self):
        """Stop the discovery service"""
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        self.background_tasks.clear()
        
        self.logger.info("Agent discovery stopped")
    
    def set_own_capabilities(self, capabilities: List[AgentCapability]):
        """Set own agent capabilities"""
        self.own_capabilities = capabilities
        self._update_own_profile()
        
        self.logger.info("Own capabilities updated", 
                        capabilities=[cap.name for cap in capabilities])
    
    def add_capability(self, capability: AgentCapability):
        """Add a capability to own agent"""
        self.own_capabilities.append(capability)
        self._update_own_profile()
        
        self.logger.info("Capability added", capability=capability.name)
    
    def remove_capability(self, capability_name: str):
        """Remove a capability from own agent"""
        self.own_capabilities = [
            cap for cap in self.own_capabilities 
            if cap.name != capability_name
        ]
        self._update_own_profile()
        
        self.logger.info("Capability removed", capability=capability_name)
    
    def _update_own_profile(self):
        """Update own agent profile"""
        self.own_profile = AgentProfile(
            agent_id=self.agent_id,
            name=self.communicator.agent_name,
            description=f"Agent {self.communicator.agent_name}",
            capabilities=self.own_capabilities,
            status="available",
            load=0.0,  # Would be updated based on current workload
            max_concurrent_tasks=5,
            current_tasks=0,
            last_seen=datetime.now(),
            tags=[]
        )
    
    async def discover_agents(
        self, 
        required_capabilities: Optional[List[str]] = None,
        timeout: int = 30
    ) -> List[AgentProfile]:
        """Discover agents with specific capabilities"""
        # First check local cache
        if required_capabilities:
            cached_agents = self._find_agents_by_capabilities(required_capabilities)
            if cached_agents:
                return cached_agents
        
        # Broadcast discovery request
        await self._broadcast_discovery_request(required_capabilities)
        
        # Wait for responses
        await asyncio.sleep(timeout)
        
        # Return discovered agents
        if required_capabilities:
            return self._find_agents_by_capabilities(required_capabilities)
        else:
            return list(self.discovered_agents.values())
    
    def find_agents_by_capability(self, capability: str) -> List[AgentProfile]:
        """Find agents that have a specific capability"""
        return self._find_agents_by_capabilities([capability])
    
    def _find_agents_by_capabilities(self, capabilities: List[str]) -> List[AgentProfile]:
        """Find agents that have all required capabilities"""
        if not capabilities:
            return list(self.discovered_agents.values())
        
        # Find agents that have all required capabilities
        candidate_agents = None
        
        for capability in capabilities:
            agents_with_capability = self.capability_index.get(capability, set())
            
            if candidate_agents is None:
                candidate_agents = agents_with_capability.copy()
            else:
                candidate_agents &= agents_with_capability
        
        if candidate_agents is None:
            return []
        
        return [
            self.discovered_agents[agent_id] 
            for agent_id in candidate_agents
            if agent_id in self.discovered_agents
        ]
    
    def get_agent_profile(self, agent_id: str) -> Optional[AgentProfile]:
        """Get profile of a discovered agent"""
        return self.discovered_agents.get(agent_id)
    
    def get_all_discovered_agents(self) -> List[AgentProfile]:
        """Get all discovered agents"""
        return list(self.discovered_agents.values())
    
    def get_capability_stats(self) -> Dict[str, int]:
        """Get statistics about available capabilities"""
        return {
            capability: len(agent_ids)
            for capability, agent_ids in self.capability_index.items()
        }
    
    async def _broadcast_discovery(self):
        """Broadcast own presence to network"""
        if not self.own_profile:
            self._update_own_profile()
        
        discovery_message = A2AMessage(
            type=A2AMessageType.DISCOVERY_RESPONSE,
            sender_id=self.agent_id,
            recipient_id=None,  # Broadcast
            payload={
                "profile": {
                    "agent_id": self.own_profile.agent_id,
                    "name": self.own_profile.name,
                    "description": self.own_profile.description,
                    "capabilities": [
                        {
                            "name": cap.name,
                            "description": cap.description,
                            "version": cap.version,
                            "parameters": cap.parameters
                        }
                        for cap in self.own_profile.capabilities
                    ],
                    "status": self.own_profile.status,
                    "load": self.own_profile.load,
                    "max_concurrent_tasks": self.own_profile.max_concurrent_tasks,
                    "current_tasks": self.own_profile.current_tasks,
                    "tags": self.own_profile.tags
                }
            }
        )
        
        await self.communicator.send_message(discovery_message)
        self.logger.debug("Discovery broadcast sent")
    
    async def _broadcast_discovery_request(self, required_capabilities: Optional[List[str]]):
        """Broadcast discovery request"""
        discovery_request = A2ARequest(
            type=A2AMessageType.DISCOVERY_REQUEST,
            sender_id=self.agent_id,
            recipient_id=None,  # Broadcast
            payload={
                "required_capabilities": required_capabilities or [],
                "requester_id": self.agent_id
            }
        )
        
        await self.communicator.send_message(discovery_request)
        self.logger.debug("Discovery request broadcast", 
                         required_capabilities=required_capabilities)
    
    def _update_agent_profile(self, profile: AgentProfile):
        """Update discovered agent profile"""
        agent_id = profile.agent_id
        
        # Update discovered agents
        self.discovered_agents[agent_id] = profile
        
        # Update capability index
        # Remove old capabilities for this agent
        for capability, agent_set in self.capability_index.items():
            agent_set.discard(agent_id)
        
        # Add new capabilities
        for capability in profile.capabilities:
            if capability.name not in self.capability_index:
                self.capability_index[capability.name] = set()
            self.capability_index[capability.name].add(agent_id)
        
        # Update communicator's known agents
        self.communicator.update_agent_profile(agent_id, profile)
        
        self.logger.debug("Agent profile updated", 
                         agent_id=agent_id,
                         capabilities=[cap.name for cap in profile.capabilities])
    
    async def _handle_discovery_request(self, message: A2AMessage):
        """Handle incoming discovery request"""
        payload = message.payload
        required_capabilities = payload.get("required_capabilities", [])
        
        # Check if we match the requirements
        if self.own_profile and self.own_profile.can_handle_task(required_capabilities):
            # Send our profile as response
            response = A2AResponse(
                type=A2AMessageType.DISCOVERY_RESPONSE,
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                correlation_id=message.id,
                success=True,
                result={
                    "profile": {
                        "agent_id": self.own_profile.agent_id,
                        "name": self.own_profile.name,
                        "description": self.own_profile.description,
                        "capabilities": [
                            {
                                "name": cap.name,
                                "description": cap.description,
                                "version": cap.version,
                                "parameters": cap.parameters
                            }
                            for cap in self.own_profile.capabilities
                        ],
                        "status": self.own_profile.status,
                        "load": self.own_profile.load,
                        "max_concurrent_tasks": self.own_profile.max_concurrent_tasks,
                        "current_tasks": self.own_profile.current_tasks,
                        "tags": self.own_profile.tags
                    }
                }
            )
            
            await self.communicator.send_response(response)
            
            self.logger.debug("Discovery response sent", 
                            requester=message.sender_id,
                            capabilities_match=required_capabilities)
    
    async def _handle_discovery_response(self, message: A2AMessage):
        """Handle incoming discovery response"""
        if message.sender_id == self.agent_id:
            return  # Ignore our own messages
        
        try:
            profile_data = None
            
            if hasattr(message, 'result') and message.result:
                profile_data = message.result.get("profile")
            else:
                profile_data = message.payload.get("profile")
            
            if not profile_data:
                return
            
            # Create agent profile
            capabilities = []
            for cap_data in profile_data.get("capabilities", []):
                capability = AgentCapability(
                    name=cap_data["name"],
                    description=cap_data["description"],
                    version=cap_data.get("version", "1.0"),
                    parameters=cap_data.get("parameters", {})
                )
                capabilities.append(capability)
            
            profile = AgentProfile(
                agent_id=profile_data["agent_id"],
                name=profile_data["name"],
                description=profile_data["description"],
                capabilities=capabilities,
                status=profile_data.get("status", "unknown"),
                load=profile_data.get("load", 0.0),
                max_concurrent_tasks=profile_data.get("max_concurrent_tasks", 5),
                current_tasks=profile_data.get("current_tasks", 0),
                last_seen=datetime.now(),
                tags=profile_data.get("tags", [])
            )
            
            self._update_agent_profile(profile)
            
        except Exception as e:
            self.logger.error("Error processing discovery response", 
                            sender=message.sender_id, 
                            error=str(e))
    
    async def _handle_ping(self, message: A2AMessage):
        """Handle ping request"""
        pong_response = A2AResponse(
            type=A2AMessageType.PONG,
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            correlation_id=message.id,
            success=True,
            result={"timestamp": datetime.now().isoformat()}
        )
        
        await self.communicator.send_response(pong_response)
    
    async def _handle_pong(self, message: A2AMessage):
        """Handle pong response"""
        # Update agent's last seen time
        if message.sender_id in self.discovered_agents:
            self.discovered_agents[message.sender_id].last_seen = datetime.now()
    
    async def _periodic_discovery(self):
        """Periodic discovery broadcast"""
        while self.running:
            try:
                await self._broadcast_discovery()
                await asyncio.sleep(self.discovery_interval)
            except Exception as e:
                self.logger.error("Error in periodic discovery", error=str(e))
                await asyncio.sleep(60)
    
    async def _cleanup_stale_agents(self):
        """Clean up stale agent entries"""
        while self.running:
            try:
                cutoff_time = datetime.now() - timedelta(seconds=self.agent_ttl)
                stale_agents = []
                
                for agent_id, profile in self.discovered_agents.items():
                    if profile.last_seen < cutoff_time:
                        stale_agents.append(agent_id)
                
                for agent_id in stale_agents:
                    # Remove from discovered agents
                    del self.discovered_agents[agent_id]
                    
                    # Remove from capability index
                    for capability, agent_set in self.capability_index.items():
                        agent_set.discard(agent_id)
                    
                    self.logger.info("Removed stale agent", agent_id=agent_id)
                
                await asyncio.sleep(120)  # Cleanup every 2 minutes
                
            except Exception as e:
                self.logger.error("Error cleaning up stale agents", error=str(e))
                await asyncio.sleep(60)