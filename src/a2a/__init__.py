"""
Agent-to-Agent (A2A) Communication Protocol

This module provides the foundation for inter-agent communication,
enabling agents to discover, communicate, and collaborate with each other.
"""

from .protocol import (
    A2AMessage,
    A2AMessageType,
    A2ARequest,
    A2AResponse,
    TaskDelegation,
    CollaborationRequest
)

from .communicator import A2ACommunicator
from .discovery import AgentDiscovery
from .routing import MessageRouter

__all__ = [
    "A2AMessage",
    "A2AMessageType", 
    "A2ARequest",
    "A2AResponse",
    "TaskDelegation",
    "CollaborationRequest",
    "A2ACommunicator",
    "AgentDiscovery",
    "MessageRouter"
]