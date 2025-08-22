"""
A2A Protocol Message Definitions

This module defines the message formats and protocol structures
for agent-to-agent communication.
"""

from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import uuid


class A2AMessageType(str, Enum):
    """Types of A2A messages"""
    # Discovery messages
    PING = "ping"
    PONG = "pong"
    DISCOVERY_REQUEST = "discovery_request"
    DISCOVERY_RESPONSE = "discovery_response"
    
    # Task delegation messages
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    TASK_ACCEPT = "task_accept"
    TASK_REJECT = "task_reject"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    
    # Collaboration messages
    COLLABORATION_REQUEST = "collaboration_request"
    COLLABORATION_ACCEPT = "collaboration_accept"
    COLLABORATION_REJECT = "collaboration_reject"
    COLLABORATION_JOIN = "collaboration_join"
    COLLABORATION_LEAVE = "collaboration_leave"
    
    # Information sharing
    INFO_REQUEST = "info_request"
    INFO_RESPONSE = "info_response"
    KNOWLEDGE_SHARE = "knowledge_share"
    
    # Status messages
    STATUS_REQUEST = "status_request"
    STATUS_RESPONSE = "status_response"
    HEARTBEAT = "heartbeat"
    
    # Error messages
    ERROR = "error"
    INVALID_MESSAGE = "invalid_message"


class A2AMessage(BaseModel):
    """Base A2A message structure"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique message ID")
    type: A2AMessageType = Field(..., description="Message type")
    sender_id: str = Field(..., description="Sender agent ID")
    recipient_id: Optional[str] = Field(default=None, description="Recipient agent ID (None for broadcast)")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for request/response")
    priority: int = Field(default=5, ge=1, le=10, description="Message priority (1=highest, 10=lowest)")
    ttl_seconds: int = Field(default=300, gt=0, description="Time to live in seconds")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Message payload")
    
    class Config:
        use_enum_values = True


class A2ARequest(A2AMessage):
    """Request message with response expectation"""
    expects_response: bool = Field(default=True, description="Whether response is expected")
    response_timeout: int = Field(default=30, gt=0, description="Response timeout in seconds")


class A2AResponse(A2AMessage):
    """Response message to a request"""
    success: bool = Field(..., description="Whether the request was successful")
    error_message: Optional[str] = Field(default=None, description="Error message if unsuccessful")
    result: Optional[Any] = Field(default=None, description="Response result")


class TaskDelegation(BaseModel):
    """Task delegation request structure"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique task ID")
    task_type: str = Field(..., description="Type of task")
    task_description: str = Field(..., description="Human-readable task description")
    task_data: Dict[str, Any] = Field(default_factory=dict, description="Task input data")
    required_capabilities: List[str] = Field(default_factory=list, description="Required agent capabilities")
    priority: int = Field(default=5, ge=1, le=10, description="Task priority")
    deadline: Optional[datetime] = Field(default=None, description="Task deadline")
    max_attempts: int = Field(default=3, gt=0, description="Maximum retry attempts")
    callback_required: bool = Field(default=True, description="Whether callback is required on completion")


class CollaborationRequest(BaseModel):
    """Collaboration request structure"""
    collaboration_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique collaboration ID")
    title: str = Field(..., description="Collaboration title")
    description: str = Field(..., description="Collaboration description")
    required_agents: int = Field(default=2, gt=0, description="Number of agents needed")
    required_capabilities: List[str] = Field(default_factory=list, description="Required capabilities")
    coordinator_id: Optional[str] = Field(default=None, description="Coordinator agent ID")
    max_duration_minutes: int = Field(default=60, gt=0, description="Maximum collaboration duration")
    join_deadline: Optional[datetime] = Field(default=None, description="Deadline to join collaboration")


@dataclass
class AgentCapability:
    """Agent capability definition"""
    name: str
    description: str
    version: str = "1.0"
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class AgentProfile:
    """Agent profile for discovery"""
    agent_id: str
    name: str
    description: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    status: str = "available"
    load: float = 0.0  # 0.0 to 1.0
    max_concurrent_tasks: int = 5
    current_tasks: int = 0
    last_seen: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    
    def can_handle_task(self, required_capabilities: List[str]) -> bool:
        """Check if agent can handle a task"""
        if self.current_tasks >= self.max_concurrent_tasks:
            return False
        
        agent_caps = {cap.name for cap in self.capabilities}
        return all(cap in agent_caps for cap in required_capabilities)
    
    def get_capability(self, name: str) -> Optional[AgentCapability]:
        """Get capability by name"""
        for cap in self.capabilities:
            if cap.name == name:
                return cap
        return None


class MessageDeliveryStatus(str, Enum):
    """Message delivery status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class MessageDelivery:
    """Message delivery tracking"""
    message_id: str
    sender_id: str
    recipient_id: str
    status: MessageDeliveryStatus = MessageDeliveryStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    last_attempt: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if message has expired"""
        if not self.last_attempt:
            return False
        
        elapsed = (datetime.now() - self.last_attempt).total_seconds()
        return elapsed > ttl_seconds
    
    def can_retry(self) -> bool:
        """Check if message can be retried"""
        return (self.status == MessageDeliveryStatus.FAILED and 
                self.attempts < self.max_attempts)


class A2AError(Exception):
    """Base exception for A2A protocol errors"""
    pass


class AgentNotFoundError(A2AError):
    """Agent not found in registry"""
    pass


class MessageDeliveryError(A2AError):
    """Message delivery failed"""
    pass


class TaskDelegationError(A2AError):
    """Task delegation failed"""
    pass


class CollaborationError(A2AError):
    """Collaboration setup failed"""
    pass