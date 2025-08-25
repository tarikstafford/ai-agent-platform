"""
A2A Communicator

This module provides the main communication interface for agent-to-agent messaging.
"""

import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict
import json

import structlog
from .protocol import (
    A2AMessage, A2AMessageType, A2ARequest, A2AResponse,
    MessageDelivery, MessageDeliveryStatus, AgentProfile,
    A2AError, AgentNotFoundError, MessageDeliveryError
)
from .traces import get_tracer

logger = structlog.get_logger()


class A2ACommunicator:
    """Main communication interface for A2A messaging"""
    
    def __init__(self, agent_id: str, agent_name: str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.logger = logger.bind(component="a2a_communicator", agent_id=agent_id)
        
        # Message handlers
        self.message_handlers: Dict[A2AMessageType, List[Callable]] = defaultdict(list)
        
        # Outbound message queue
        self.outbound_queue: asyncio.Queue = asyncio.Queue()
        
        # Inbound message queue
        self.inbound_queue: asyncio.Queue = asyncio.Queue()
        
        # Delivery tracking
        self.pending_deliveries: Dict[str, MessageDelivery] = {}
        
        # Response waiting
        self.pending_responses: Dict[str, asyncio.Future] = {}
        
        # Agent discovery
        self.known_agents: Dict[str, AgentProfile] = {}
        
        # Communication stats
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_failed": 0,
            "responses_received": 0,
            "responses_timeout": 0
        }
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.running = False
    
    async def start(self):
        """Start the communicator"""
        if self.running:
            return
        
        self.running = True
        
        # Start background tasks
        self.background_tasks.extend([
            asyncio.create_task(self._process_outbound_messages()),
            asyncio.create_task(self._process_inbound_messages()),
            asyncio.create_task(self._cleanup_expired_messages()),
            asyncio.create_task(self._heartbeat_loop())
        ])
        
        self.logger.info("A2A communicator started")
    
    async def stop(self):
        """Stop the communicator"""
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        self.background_tasks.clear()
        
        self.logger.info("A2A communicator stopped")
    
    def register_message_handler(
        self, 
        message_type: A2AMessageType, 
        handler: Callable[[A2AMessage], Any]
    ):
        """Register a message handler for a specific message type"""
        self.message_handlers[message_type].append(handler)
        self.logger.info("Message handler registered", message_type=message_type.value)
    
    def unregister_message_handler(
        self, 
        message_type: A2AMessageType, 
        handler: Callable[[A2AMessage], Any]
    ):
        """Unregister a message handler"""
        if handler in self.message_handlers[message_type]:
            self.message_handlers[message_type].remove(handler)
            self.logger.info("Message handler unregistered", message_type=message_type.value)
    
    async def send_message(
        self, 
        message: A2AMessage, 
        delivery_callback: Optional[Callable[[MessageDelivery], None]] = None
    ) -> str:
        """Send a message to another agent"""
        if not message.sender_id:
            message.sender_id = self.agent_id
        
        # Create delivery tracking
        delivery = MessageDelivery(
            message_id=message.id,
            sender_id=message.sender_id,
            recipient_id=message.recipient_id or "broadcast"
        )
        
        self.pending_deliveries[message.id] = delivery
        
        # Trace message sent
        tracer = get_tracer()
        if tracer:
            await tracer.trace_message_sent(message)
        
        # Queue message for sending
        await self.outbound_queue.put((message, delivery_callback))
        
        self.logger.debug("Message queued for sending", 
                         message_id=message.id, 
                         recipient=message.recipient_id,
                         message_type=message.type.value if hasattr(message.type, 'value') else message.type)
        
        return message.id
    
    async def send_request(
        self, 
        request: A2ARequest,
        timeout: Optional[int] = None
    ) -> A2AResponse:
        """Send a request and wait for response"""
        timeout = timeout or request.response_timeout
        
        # Create future for response
        response_future = asyncio.Future()
        self.pending_responses[request.id] = response_future
        
        try:
            # Send the request
            await self.send_message(request)
            
            # Wait for response
            response = await asyncio.wait_for(response_future, timeout=timeout)
            self.stats["responses_received"] += 1
            return response
            
        except asyncio.TimeoutError:
            self.stats["responses_timeout"] += 1
            self.logger.warning("Request timeout", request_id=request.id, timeout=timeout)
            raise
        
        finally:
            # Clean up
            self.pending_responses.pop(request.id, None)
    
    async def send_response(self, response: A2AResponse):
        """Send a response to a request"""
        await self.send_message(response)
    
    async def broadcast_message(self, message: A2AMessage):
        """Broadcast message to all known agents"""
        message.recipient_id = None  # Broadcast indicator
        await self.send_message(message)
    
    async def receive_message(self, message: A2AMessage):
        """Receive an incoming message"""
        # Trace message received
        tracer = get_tracer()
        if tracer:
            await tracer.trace_message_received(message, self.agent_id)
        
        await self.inbound_queue.put(message)
        self.stats["messages_received"] += 1
        
        self.logger.debug("Message received", 
                         message_id=message.id,
                         sender=message.sender_id,
                         message_type=message.type.value if hasattr(message.type, 'value') else message.type)
    
    async def ping_agent(self, agent_id: str, timeout: int = 10) -> bool:
        """Ping another agent to check availability"""
        try:
            ping_request = A2ARequest(
                type=A2AMessageType.PING,
                sender_id=self.agent_id,
                recipient_id=agent_id,
                response_timeout=timeout,
                payload={"timestamp": datetime.now().isoformat()}
            )
            
            response = await self.send_request(ping_request, timeout)
            return response.success
            
        except Exception as e:
            self.logger.warning("Ping failed", target_agent=agent_id, error=str(e))
            return False
    
    async def discover_agents(
        self, 
        capabilities: Optional[List[str]] = None,
        timeout: int = 30
    ) -> List[AgentProfile]:
        """Discover agents with specific capabilities"""
        discovery_request = A2ARequest(
            type=A2AMessageType.DISCOVERY_REQUEST,
            sender_id=self.agent_id,
            recipient_id=None,  # Broadcast
            response_timeout=timeout,
            payload={
                "required_capabilities": capabilities or [],
                "requester_profile": self._get_own_profile()
            }
        )
        
        # Send broadcast discovery request
        await self.send_message(discovery_request)
        
        # Collect responses
        discovered_agents = []
        response_deadline = datetime.now() + timedelta(seconds=timeout)
        
        while datetime.now() < response_deadline:
            try:
                # Wait for discovery responses
                await asyncio.sleep(0.1)  # Small delay to allow responses
                
                # Check for discovery responses in handlers
                # This would be handled by the discovery response handler
                
            except asyncio.TimeoutError:
                break
        
        return list(self.known_agents.values())
    
    def update_agent_profile(self, agent_id: str, profile: AgentProfile):
        """Update knowledge of another agent's profile"""
        self.known_agents[agent_id] = profile
        profile.last_seen = datetime.now()
        
        self.logger.debug("Agent profile updated", 
                         agent_id=agent_id,
                         capabilities=[cap.name for cap in profile.capabilities])
    
    def get_known_agents(self) -> List[AgentProfile]:
        """Get list of known agents"""
        return list(self.known_agents.values())
    
    def get_agent_profile(self, agent_id: str) -> Optional[AgentProfile]:
        """Get profile of a known agent"""
        return self.known_agents.get(agent_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get communication statistics"""
        return {
            **self.stats,
            "known_agents": len(self.known_agents),
            "pending_deliveries": len(self.pending_deliveries),
            "pending_responses": len(self.pending_responses),
            "message_handlers": {
                msg_type.value: len(handlers) 
                for msg_type, handlers in self.message_handlers.items()
            }
        }
    
    def _get_own_profile(self) -> Dict[str, Any]:
        """Get own agent profile for discovery"""
        # This would be populated by the agent itself
        return {
            "agent_id": self.agent_id,
            "name": self.agent_name,
            "status": "available",
            "capabilities": []  # Would be populated by agent
        }
    
    async def _process_outbound_messages(self):
        """Process outbound message queue"""
        while self.running:
            try:
                message, callback = await asyncio.wait_for(
                    self.outbound_queue.get(), 
                    timeout=1.0
                )
                
                delivery = self.pending_deliveries.get(message.id)
                if not delivery:
                    continue
                
                success = await self._deliver_message(message)
                
                # Trace delivery result
                tracer = get_tracer()
                if tracer:
                    if success:
                        await tracer.trace_message_delivered(message)
                    else:
                        await tracer.trace_message_failed(message, "Delivery failed")
                
                if success:
                    delivery.status = MessageDeliveryStatus.DELIVERED
                    delivery.delivered_at = datetime.now()
                    self.stats["messages_sent"] += 1
                else:
                    delivery.status = MessageDeliveryStatus.FAILED
                    delivery.attempts += 1
                    self.stats["messages_failed"] += 1
                    
                    # Trace retry if applicable
                    if tracer and delivery.can_retry():
                        await tracer.trace_message_retry(message, delivery.attempts, "Retrying delivery")
                
                delivery.last_attempt = datetime.now()
                
                if callback:
                    callback(delivery)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error("Error processing outbound messages", error=str(e))
    
    async def _process_inbound_messages(self):
        """Process inbound message queue"""
        while self.running:
            try:
                message = await asyncio.wait_for(
                    self.inbound_queue.get(), 
                    timeout=1.0
                )
                
                # Handle responses to pending requests
                if message.correlation_id and message.correlation_id in self.pending_responses:
                    future = self.pending_responses[message.correlation_id]
                    if not future.done():
                        future.set_result(message)
                    continue
                
                # Route to message handlers
                handlers = self.message_handlers.get(message.type, [])
                
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(message)
                        else:
                            handler(message)
                    except Exception as e:
                        self.logger.error("Message handler error", 
                                        handler=str(handler), 
                                        error=str(e))
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error("Error processing inbound messages", error=str(e))
    
    async def _deliver_message(self, message: A2AMessage) -> bool:
        """Deliver message to recipient(s)"""
        try:
            # This would interface with the actual message transport
            # For now, we'll simulate delivery
            
            if message.recipient_id:
                # Direct message
                # In real implementation, this would send via HTTP/WebSocket/etc
                success = await self._send_to_agent(message.recipient_id, message)
            else:
                # Broadcast message
                success = await self._broadcast_to_agents(message)
            
            return success
            
        except Exception as e:
            self.logger.error("Message delivery error", 
                            message_id=message.id,
                            error=str(e))
            return False
    
    async def _send_to_agent(self, agent_id: str, message: A2AMessage) -> bool:
        """Send message to specific agent"""
        # This would be implemented with actual transport mechanism
        # For now, we'll return success if agent is known
        return agent_id in self.known_agents
    
    async def _broadcast_to_agents(self, message: A2AMessage) -> bool:
        """Broadcast message to all known agents"""
        # This would broadcast to all known agents
        success_count = 0
        
        for agent_id in self.known_agents:
            if await self._send_to_agent(agent_id, message):
                success_count += 1
        
        return success_count > 0
    
    async def _cleanup_expired_messages(self):
        """Clean up expired messages and deliveries"""
        while self.running:
            try:
                current_time = datetime.now()
                expired_messages = []
                
                for message_id, delivery in self.pending_deliveries.items():
                    # Check if delivery has expired
                    if delivery.last_attempt:
                        time_since_attempt = (current_time - delivery.last_attempt).total_seconds()
                        # Consider expired if no delivery success after 5 minutes
                        if time_since_attempt > 300 and delivery.status != MessageDeliveryStatus.DELIVERED:
                            delivery.status = MessageDeliveryStatus.EXPIRED
                            expired_messages.append(message_id)
                
                # Clean up expired messages
                for message_id in expired_messages:
                    del self.pending_deliveries[message_id]
                    self.logger.debug("Expired message cleaned up", message_id=message_id)
                
                # Clean up expired pending responses
                expired_responses = []
                for request_id, future in self.pending_responses.items():
                    if future.done():
                        expired_responses.append(request_id)
                
                for request_id in expired_responses:
                    del self.pending_responses[request_id]
                
                await asyncio.sleep(60)  # Cleanup every minute
                
            except Exception as e:
                self.logger.error("Error during cleanup", error=str(e))
                await asyncio.sleep(60)
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to known agents"""
        while self.running:
            try:
                # Send heartbeat to all known agents
                for agent_id in list(self.known_agents.keys()):
                    heartbeat = A2AMessage(
                        type=A2AMessageType.HEARTBEAT,
                        sender_id=self.agent_id,
                        recipient_id=agent_id,
                        payload={
                            "timestamp": datetime.now().isoformat(),
                            "status": "active"
                        }
                    )
                    
                    await self.send_message(heartbeat)
                
                # Remove agents that haven't been seen recently
                cutoff_time = datetime.now() - timedelta(minutes=10)
                inactive_agents = [
                    agent_id for agent_id, profile in self.known_agents.items()
                    if profile.last_seen < cutoff_time
                ]
                
                for agent_id in inactive_agents:
                    del self.known_agents[agent_id]
                    self.logger.info("Removed inactive agent", agent_id=agent_id)
                
                await asyncio.sleep(300)  # Heartbeat every 5 minutes
                
            except Exception as e:
                self.logger.error("Heartbeat error", error=str(e))
                await asyncio.sleep(60)