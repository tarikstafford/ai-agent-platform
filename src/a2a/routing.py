"""
Message Routing System

This module provides message routing and delivery capabilities for the A2A protocol.
"""

import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict
import json

import structlog
from .protocol import (
    A2AMessage, A2AMessageType, A2ARequest, A2AResponse,
    MessageDelivery, MessageDeliveryStatus, AgentProfile
)

logger = structlog.get_logger()


class MessageRouter:
    """Message routing and delivery system"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.logger = logger.bind(component="message_router", agent_id=agent_id)
        
        # Routing table: agent_id -> transport method
        self.routing_table: Dict[str, Dict[str, Any]] = {}
        
        # Message queues per agent
        self.agent_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        
        # Transport handlers
        self.transport_handlers: Dict[str, Callable] = {}
        
        # Delivery tracking
        self.active_deliveries: Dict[str, MessageDelivery] = {}
        
        # Routing metrics
        self.metrics = {
            "messages_routed": 0,
            "messages_delivered": 0,
            "messages_failed": 0,
            "routing_errors": 0,
            "average_delivery_time": 0.0
        }
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.running = False
    
    async def start(self):
        """Start the message router"""
        if self.running:
            return
        
        self.running = True
        
        # Start background tasks
        self.background_tasks.extend([
            asyncio.create_task(self._process_routing_queues()),
            asyncio.create_task(self._monitor_deliveries()),
            asyncio.create_task(self._update_routing_table())
        ])
        
        self.logger.info("Message router started")
    
    async def stop(self):
        """Stop the message router"""
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        self.background_tasks.clear()
        
        self.logger.info("Message router stopped")
    
    def register_transport_handler(self, transport_type: str, handler: Callable):
        """Register a transport handler"""
        self.transport_handlers[transport_type] = handler
        self.logger.info("Transport handler registered", transport_type=transport_type)
    
    def add_route(
        self, 
        agent_id: str, 
        transport_type: str, 
        endpoint: str,
        priority: int = 5
    ):
        """Add routing entry for an agent"""
        self.routing_table[agent_id] = {
            "transport_type": transport_type,
            "endpoint": endpoint,
            "priority": priority,
            "last_updated": datetime.now(),
            "success_count": 0,
            "failure_count": 0
        }
        
        self.logger.debug("Route added", 
                         agent_id=agent_id, 
                         transport=transport_type,
                         endpoint=endpoint)
    
    def remove_route(self, agent_id: str):
        """Remove routing entry for an agent"""
        if agent_id in self.routing_table:
            del self.routing_table[agent_id]
            self.logger.debug("Route removed", agent_id=agent_id)
    
    def update_route_metrics(self, agent_id: str, success: bool, response_time: float):
        """Update route metrics"""
        if agent_id in self.routing_table:
            route = self.routing_table[agent_id]
            
            if success:
                route["success_count"] += 1
            else:
                route["failure_count"] += 1
            
            route["last_response_time"] = response_time
            route["last_updated"] = datetime.now()
            
            # Calculate success rate
            total = route["success_count"] + route["failure_count"]
            route["success_rate"] = route["success_count"] / total if total > 0 else 0.0
    
    async def route_message(self, message: A2AMessage) -> MessageDelivery:
        """Route a message to its destination"""
        delivery = MessageDelivery(
            message_id=message.id,
            sender_id=message.sender_id,
            recipient_id=message.recipient_id or "broadcast"
        )
        
        self.active_deliveries[message.id] = delivery
        
        try:
            if message.recipient_id:
                # Direct message routing
                await self._route_direct_message(message, delivery)
            else:
                # Broadcast message routing
                await self._route_broadcast_message(message, delivery)
            
            self.metrics["messages_routed"] += 1
            
        except Exception as e:
            delivery.status = MessageDeliveryStatus.FAILED
            delivery.error_message = str(e)
            self.metrics["routing_errors"] += 1
            self.logger.error("Routing error", 
                            message_id=message.id, 
                            error=str(e))
        
        return delivery
    
    async def _route_direct_message(self, message: A2AMessage, delivery: MessageDelivery):
        """Route message to specific recipient"""
        recipient_id = message.recipient_id
        
        if recipient_id not in self.routing_table:
            # Try to discover route
            await self._discover_route(recipient_id)
        
        if recipient_id not in self.routing_table:
            delivery.status = MessageDeliveryStatus.FAILED
            delivery.error_message = f"No route to agent {recipient_id}"
            return
        
        # Add to agent queue for processing
        await self.agent_queues[recipient_id].put((message, delivery))
    
    async def _route_broadcast_message(self, message: A2AMessage, delivery: MessageDelivery):
        """Route broadcast message to all known agents"""
        if not self.routing_table:
            delivery.status = MessageDeliveryStatus.FAILED
            delivery.error_message = "No known agents for broadcast"
            return
        
        # Add to all agent queues
        for agent_id in self.routing_table:
            if agent_id != self.agent_id:  # Don't send to self
                await self.agent_queues[agent_id].put((message, delivery))
    
    async def _discover_route(self, agent_id: str):
        """Attempt to discover route to unknown agent"""
        # This would integrate with the discovery system
        # For now, we'll check if we have any default transport
        if "http" in self.transport_handlers:
            # Assume HTTP transport with standard endpoint
            self.add_route(
                agent_id=agent_id,
                transport_type="http",
                endpoint=f"http://agent-{agent_id}:8000/a2a/receive",
                priority=7  # Lower priority for discovered routes
            )
            
            self.logger.debug("Route discovered via HTTP", agent_id=agent_id)
    
    async def _process_routing_queues(self):
        """Process message queues for each agent"""
        while self.running:
            try:
                # Process queues for each agent
                for agent_id, queue in list(self.agent_queues.items()):
                    if queue.empty():
                        continue
                    
                    try:
                        message, delivery = await asyncio.wait_for(
                            queue.get(), 
                            timeout=0.1
                        )
                        
                        # Attempt delivery
                        await self._attempt_delivery(agent_id, message, delivery)
                        
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        self.logger.error("Queue processing error", 
                                        agent_id=agent_id,
                                        error=str(e))
                
                await asyncio.sleep(0.1)  # Small delay between queue checks
                
            except Exception as e:
                self.logger.error("Error processing routing queues", error=str(e))
                await asyncio.sleep(1.0)
    
    async def _attempt_delivery(
        self, 
        agent_id: str, 
        message: A2AMessage, 
        delivery: MessageDelivery
    ):
        """Attempt to deliver message to specific agent"""
        if agent_id not in self.routing_table:
            delivery.status = MessageDeliveryStatus.FAILED
            delivery.error_message = f"No route to {agent_id}"
            return
        
        route = self.routing_table[agent_id]
        transport_type = route["transport_type"]
        
        if transport_type not in self.transport_handlers:
            delivery.status = MessageDeliveryStatus.FAILED
            delivery.error_message = f"No handler for transport {transport_type}"
            return
        
        start_time = datetime.now()
        delivery.attempts += 1
        delivery.last_attempt = start_time
        
        try:
            handler = self.transport_handlers[transport_type]
            
            # Attempt delivery via transport
            success = await handler(route["endpoint"], message)
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            if success:
                delivery.status = MessageDeliveryStatus.DELIVERED
                delivery.delivered_at = datetime.now()
                self.metrics["messages_delivered"] += 1
                
                self.update_route_metrics(agent_id, True, response_time)
                
                # Update average delivery time
                current_avg = self.metrics["average_delivery_time"]
                total_delivered = self.metrics["messages_delivered"]
                self.metrics["average_delivery_time"] = (
                    (current_avg * (total_delivered - 1) + response_time) / total_delivered
                )
                
                self.logger.debug("Message delivered", 
                                message_id=message.id,
                                agent_id=agent_id,
                                response_time=response_time)
            else:
                delivery.status = MessageDeliveryStatus.FAILED
                delivery.error_message = "Transport handler returned failure"
                self.metrics["messages_failed"] += 1
                
                self.update_route_metrics(agent_id, False, response_time)
        
        except Exception as e:
            delivery.status = MessageDeliveryStatus.FAILED
            delivery.error_message = str(e)
            self.metrics["messages_failed"] += 1
            
            response_time = (datetime.now() - start_time).total_seconds()
            self.update_route_metrics(agent_id, False, response_time)
            
            self.logger.error("Delivery attempt failed", 
                            message_id=message.id,
                            agent_id=agent_id,
                            error=str(e))
    
    async def _monitor_deliveries(self):
        """Monitor active deliveries and handle retries"""
        while self.running:
            try:
                current_time = datetime.now()
                retry_deliveries = []
                expired_deliveries = []
                
                for delivery in list(self.active_deliveries.values()):
                    # Check for expired messages
                    if delivery.last_attempt:
                        time_since_attempt = (current_time - delivery.last_attempt).total_seconds()
                        
                        # Expire after 5 minutes of no progress
                        if time_since_attempt > 300:
                            if delivery.status == MessageDeliveryStatus.PENDING:
                                delivery.status = MessageDeliveryStatus.EXPIRED
                                expired_deliveries.append(delivery.message_id)
                    
                    # Check for retryable failures
                    if delivery.can_retry():
                        retry_deliveries.append(delivery)
                
                # Handle retries
                for delivery in retry_deliveries:
                    recipient_id = delivery.recipient_id
                    if recipient_id != "broadcast" and recipient_id in self.routing_table:
                        # Re-queue for delivery attempt
                        message = A2AMessage(id=delivery.message_id, 
                                           sender_id=delivery.sender_id,
                                           recipient_id=delivery.recipient_id,
                                           type=A2AMessageType.PING)  # Placeholder
                        
                        await self.agent_queues[recipient_id].put((message, delivery))
                
                # Clean up expired deliveries
                for message_id in expired_deliveries:
                    if message_id in self.active_deliveries:
                        del self.active_deliveries[message_id]
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error("Error monitoring deliveries", error=str(e))
                await asyncio.sleep(30)
    
    async def _update_routing_table(self):
        """Update routing table based on agent availability"""
        while self.running:
            try:
                current_time = datetime.now()
                stale_routes = []
                
                # Check for stale routes
                for agent_id, route in self.routing_table.items():
                    last_updated = route.get("last_updated", current_time)
                    time_since_update = (current_time - last_updated).total_seconds()
                    
                    # Mark routes as stale after 10 minutes of no updates
                    if time_since_update > 600:
                        # Check success rate
                        success_rate = route.get("success_rate", 0.0)
                        if success_rate < 0.1:  # Less than 10% success rate
                            stale_routes.append(agent_id)
                
                # Remove stale routes
                for agent_id in stale_routes:
                    self.remove_route(agent_id)
                    self.logger.info("Removed stale route", agent_id=agent_id)
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                self.logger.error("Error updating routing table", error=str(e))
                await asyncio.sleep(60)
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        active_routes = len(self.routing_table)
        queue_sizes = {
            agent_id: queue.qsize() 
            for agent_id, queue in self.agent_queues.items()
            if not queue.empty()
        }
        
        route_health = {}
        for agent_id, route in self.routing_table.items():
            success_rate = route.get("success_rate", 0.0)
            route_health[agent_id] = {
                "success_rate": success_rate,
                "success_count": route.get("success_count", 0),
                "failure_count": route.get("failure_count", 0),
                "transport_type": route.get("transport_type", "unknown"),
                "last_response_time": route.get("last_response_time", 0.0)
            }
        
        return {
            **self.metrics,
            "active_routes": active_routes,
            "active_deliveries": len(self.active_deliveries),
            "queue_sizes": queue_sizes,
            "route_health": route_health,
            "transport_handlers": list(self.transport_handlers.keys())
        }
    
    def get_route(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get route information for specific agent"""
        return self.routing_table.get(agent_id)
    
    def get_all_routes(self) -> Dict[str, Dict[str, Any]]:
        """Get all routing table entries"""
        return self.routing_table.copy()