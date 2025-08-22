"""
Task Delegation and Collaboration System

This module provides advanced task delegation and collaboration capabilities
for the A2A protocol.
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import uuid

import structlog
from .protocol import (
    A2AMessage, A2AMessageType, A2ARequest, A2AResponse,
    TaskDelegation, CollaborationRequest, AgentProfile
)

logger = structlog.get_logger()


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class CollaborationStatus(str, Enum):
    """Collaboration status"""
    FORMING = "forming"
    ACTIVE = "active"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskExecution:
    """Task execution tracking"""
    task_id: str
    task_type: str
    description: str
    requester_id: str
    assigned_agent_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error_message: Optional[str] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class ActiveCollaboration:
    """Active collaboration tracking"""
    collaboration_id: str
    title: str
    description: str
    coordinator_id: str
    participants: List[str] = field(default_factory=list)
    status: CollaborationStatus = CollaborationStatus.FORMING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    shared_context: Dict[str, Any] = field(default_factory=dict)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    tasks: List[str] = field(default_factory=list)  # Task IDs


class TaskManager:
    """Task delegation and execution manager"""
    
    def __init__(self, agent_id: str, communicator):
        self.agent_id = agent_id
        self.communicator = communicator
        self.logger = logger.bind(component="task_manager", agent_id=agent_id)
        
        # Task tracking
        self.active_tasks: Dict[str, TaskExecution] = {}
        self.task_history: List[TaskExecution] = []
        
        # Task handlers
        self.task_handlers: Dict[str, Callable] = {}
        
        # Task assignment strategies
        self.assignment_strategies: Dict[str, Callable] = {
            "least_loaded": self._assign_least_loaded,
            "capability_match": self._assign_capability_match,
            "round_robin": self._assign_round_robin
        }
        
        # Current assignment strategy
        self.default_strategy = "capability_match"
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.running = False
    
    async def start(self):
        """Start the task manager"""
        if self.running:
            return
        
        self.running = True
        
        # Start background tasks
        self.background_tasks.extend([
            asyncio.create_task(self._monitor_tasks()),
            asyncio.create_task(self._cleanup_completed_tasks())
        ])
        
        self.logger.info("Task manager started")
    
    async def stop(self):
        """Stop the task manager"""
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        self.background_tasks.clear()
        
        self.logger.info("Task manager stopped")
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """Register a handler for a specific task type"""
        self.task_handlers[task_type] = handler
        self.logger.info("Task handler registered", task_type=task_type)
    
    async def delegate_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        description: Optional[str] = None,
        required_capabilities: Optional[List[str]] = None,
        deadline: Optional[datetime] = None,
        strategy: Optional[str] = None
    ) -> str:
        """Delegate a task to another agent"""
        
        task_delegation = TaskDelegation(
            task_type=task_type,
            task_description=description or f"Task: {task_type}",
            task_data=task_data,
            required_capabilities=required_capabilities or [],
            deadline=deadline
        )
        
        # Create task execution record
        task_execution = TaskExecution(
            task_id=task_delegation.task_id,
            task_type=task_type,
            description=task_delegation.task_description,
            requester_id=self.agent_id
        )
        
        self.active_tasks[task_delegation.task_id] = task_execution
        
        # Find suitable agent
        assignment_strategy = strategy or self.default_strategy
        target_agent = await self._assign_task(task_delegation, assignment_strategy)
        
        if not target_agent:
            task_execution.status = TaskStatus.FAILED
            task_execution.error_message = "No suitable agent found"
            self.logger.error("Task delegation failed", 
                            task_id=task_delegation.task_id,
                            error="No suitable agent found")
            return task_delegation.task_id
        
        # Send task request
        request = A2ARequest(
            type=A2AMessageType.TASK_REQUEST,
            sender_id=self.agent_id,
            recipient_id=target_agent,
            payload={"task_delegation": task_delegation.dict()}
        )
        
        try:
            response = await self.communicator.send_request(request)
            
            if response.success:
                task_execution.status = TaskStatus.ASSIGNED
                task_execution.assigned_agent_id = target_agent
                task_execution.started_at = datetime.now()
                
                self.logger.info("Task delegated successfully", 
                               task_id=task_delegation.task_id,
                               assigned_agent=target_agent)
            else:
                task_execution.status = TaskStatus.FAILED
                task_execution.error_message = response.error_message
                
                self.logger.error("Task delegation rejected", 
                                task_id=task_delegation.task_id,
                                agent=target_agent,
                                error=response.error_message)
        
        except Exception as e:
            task_execution.status = TaskStatus.FAILED
            task_execution.error_message = str(e)
            
            self.logger.error("Task delegation error", 
                            task_id=task_delegation.task_id,
                            error=str(e))
        
        return task_delegation.task_id
    
    async def execute_task(self, task_delegation: TaskDelegation) -> Dict[str, Any]:
        """Execute a delegated task locally"""
        task_type = task_delegation.task_type
        
        if task_type not in self.task_handlers:
            raise Exception(f"No handler for task type: {task_type}")
        
        # Create local task execution record
        task_execution = TaskExecution(
            task_id=task_delegation.task_id,
            task_type=task_type,
            description=task_delegation.task_description,
            requester_id="external",  # From external agent
            assigned_agent_id=self.agent_id,
            status=TaskStatus.IN_PROGRESS,
            started_at=datetime.now()
        )
        
        self.active_tasks[task_delegation.task_id] = task_execution
        
        try:
            # Execute task handler
            handler = self.task_handlers[task_type]
            
            if asyncio.iscoroutinefunction(handler):
                result = await handler(task_delegation.task_data)
            else:
                result = handler(task_delegation.task_data)
            
            # Update task status
            task_execution.status = TaskStatus.COMPLETED
            task_execution.completed_at = datetime.now()
            task_execution.result = result
            task_execution.progress = 1.0
            
            self.logger.info("Task completed successfully", 
                           task_id=task_delegation.task_id,
                           task_type=task_type)
            
            return {
                "success": True,
                "result": result,
                "task_id": task_delegation.task_id
            }
        
        except Exception as e:
            # Update task status
            task_execution.status = TaskStatus.FAILED
            task_execution.error_message = str(e)
            task_execution.completed_at = datetime.now()
            
            self.logger.error("Task execution failed", 
                            task_id=task_delegation.task_id,
                            error=str(e))
            
            return {
                "success": False,
                "error": str(e),
                "task_id": task_delegation.task_id
            }
    
    async def _assign_task(self, task_delegation: TaskDelegation, strategy: str) -> Optional[str]:
        """Assign task to an agent using specified strategy"""
        
        # Get available agents from discovery
        discovery = getattr(self.communicator, 'discovery', None)
        if not discovery:
            return None
        
        # Find agents with required capabilities
        suitable_agents = await discovery.discover_agents(
            task_delegation.required_capabilities
        )
        
        if not suitable_agents:
            return None
        
        # Apply assignment strategy
        assignment_func = self.assignment_strategies.get(strategy)
        if assignment_func:
            return await assignment_func(suitable_agents, task_delegation)
        
        # Default to first available agent
        return suitable_agents[0].agent_id
    
    async def _assign_least_loaded(self, agents: List[AgentProfile], task: TaskDelegation) -> Optional[str]:
        """Assign to agent with lowest load"""
        if not agents:
            return None
        
        # Sort by load (ascending)
        sorted_agents = sorted(agents, key=lambda a: a.load)
        return sorted_agents[0].agent_id
    
    async def _assign_capability_match(self, agents: List[AgentProfile], task: TaskDelegation) -> Optional[str]:
        """Assign to agent with best capability match"""
        if not agents:
            return None
        
        required_caps = set(task.required_capabilities)
        best_agent = None
        best_score = -1
        
        for agent in agents:
            agent_caps = set(cap.name for cap in agent.capabilities)
            
            # Calculate match score
            match_score = len(required_caps & agent_caps)
            total_caps = len(agent_caps)
            
            # Prefer agents with more matching capabilities and lower load
            score = match_score - (agent.load * 0.5) + (total_caps * 0.1)
            
            if score > best_score:
                best_score = score
                best_agent = agent
        
        return best_agent.agent_id if best_agent else None
    
    async def _assign_round_robin(self, agents: List[AgentProfile], task: TaskDelegation) -> Optional[str]:
        """Assign using round-robin strategy"""
        if not agents:
            return None
        
        # Simple round-robin based on task count
        task_count = len(self.active_tasks)
        agent_index = task_count % len(agents)
        
        return agents[agent_index].agent_id
    
    def get_task_status(self, task_id: str) -> Optional[TaskExecution]:
        """Get status of a specific task"""
        return self.active_tasks.get(task_id)
    
    def get_active_tasks(self) -> List[TaskExecution]:
        """Get all active tasks"""
        return list(self.active_tasks.values())
    
    def get_task_history(self) -> List[TaskExecution]:
        """Get task history"""
        return self.task_history.copy()
    
    def get_task_stats(self) -> Dict[str, Any]:
        """Get task management statistics"""
        active_count = len(self.active_tasks)
        total_count = len(self.task_history) + active_count
        
        status_counts = {}
        for status in TaskStatus:
            status_counts[status.value] = sum(
                1 for task in self.active_tasks.values() 
                if task.status == status
            )
        
        completed_tasks = [t for t in self.task_history if t.status == TaskStatus.COMPLETED]
        failed_tasks = [t for t in self.task_history if t.status == TaskStatus.FAILED]
        
        success_rate = (
            len(completed_tasks) / len(self.task_history) 
            if self.task_history else 0.0
        )
        
        return {
            "active_tasks": active_count,
            "total_tasks": total_count,
            "completed_tasks": len(completed_tasks),
            "failed_tasks": len(failed_tasks),
            "success_rate": success_rate,
            "status_counts": status_counts,
            "task_handlers": list(self.task_handlers.keys()),
            "assignment_strategies": list(self.assignment_strategies.keys()),
            "default_strategy": self.default_strategy
        }
    
    async def _monitor_tasks(self):
        """Monitor active tasks for timeouts and progress"""
        while self.running:
            try:
                current_time = datetime.now()
                timeout_tasks = []
                
                for task_id, task in self.active_tasks.items():
                    # Check for timeouts
                    if task.started_at:
                        elapsed = (current_time - task.started_at).total_seconds()
                        if elapsed > 3600:  # 1 hour timeout
                            timeout_tasks.append(task_id)
                
                # Handle timeout tasks
                for task_id in timeout_tasks:
                    task = self.active_tasks[task_id]
                    task.status = TaskStatus.TIMEOUT
                    task.completed_at = current_time
                    task.error_message = "Task execution timeout"
                    
                    self.logger.warning("Task timeout", task_id=task_id)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error("Error monitoring tasks", error=str(e))
                await asyncio.sleep(60)
    
    async def _cleanup_completed_tasks(self):
        """Clean up completed tasks"""
        while self.running:
            try:
                cutoff_time = datetime.now() - timedelta(hours=24)  # Keep for 24 hours
                completed_tasks = []
                
                for task_id, task in list(self.active_tasks.items()):
                    if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT] 
                        and task.completed_at 
                        and task.completed_at < cutoff_time):
                        
                        completed_tasks.append(task_id)
                
                # Move to history and remove from active
                for task_id in completed_tasks:
                    task = self.active_tasks.pop(task_id)
                    self.task_history.append(task)
                
                # Limit history size
                if len(self.task_history) > 1000:
                    self.task_history = self.task_history[-1000:]
                
                if completed_tasks:
                    self.logger.info("Cleaned up completed tasks", count=len(completed_tasks))
                
                await asyncio.sleep(3600)  # Cleanup every hour
                
            except Exception as e:
                self.logger.error("Error cleaning up tasks", error=str(e))
                await asyncio.sleep(3600)


class CollaborationManager:
    """Collaboration management system"""
    
    def __init__(self, agent_id: str, communicator):
        self.agent_id = agent_id
        self.communicator = communicator
        self.logger = logger.bind(component="collaboration_manager", agent_id=agent_id)
        
        # Collaboration tracking
        self.active_collaborations: Dict[str, ActiveCollaboration] = {}
        self.collaboration_history: List[ActiveCollaboration] = []
        
        # Collaboration handlers
        self.collaboration_handlers: Dict[str, Callable] = {}
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.running = False
    
    async def start(self):
        """Start the collaboration manager"""
        if self.running:
            return
        
        self.running = True
        
        # Start background tasks
        self.background_tasks.extend([
            asyncio.create_task(self._monitor_collaborations())
        ])
        
        self.logger.info("Collaboration manager started")
    
    async def stop(self):
        """Stop the collaboration manager"""
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        self.background_tasks.clear()
        
        self.logger.info("Collaboration manager stopped")
    
    async def initiate_collaboration(
        self,
        title: str,
        description: str,
        participant_ids: List[str],
        required_capabilities: Optional[List[str]] = None
    ) -> str:
        """Initiate a new collaboration"""
        
        collaboration = ActiveCollaboration(
            collaboration_id=str(uuid.uuid4()),
            title=title,
            description=description,
            coordinator_id=self.agent_id,
            participants=[self.agent_id],  # Include self as participant
            status=CollaborationStatus.FORMING
        )
        
        self.active_collaborations[collaboration.collaboration_id] = collaboration
        
        # Send collaboration requests
        collaboration_request = CollaborationRequest(
            collaboration_id=collaboration.collaboration_id,
            title=title,
            description=description,
            required_agents=len(participant_ids) + 1,  # +1 for coordinator
            required_capabilities=required_capabilities or [],
            coordinator_id=self.agent_id
        )
        
        for agent_id in participant_ids:
            message = A2AMessage(
                type=A2AMessageType.COLLABORATION_REQUEST,
                sender_id=self.agent_id,
                recipient_id=agent_id,
                payload={"collaboration_request": collaboration_request.dict()}
            )
            
            await self.communicator.send_message(message)
        
        self.logger.info("Collaboration initiated", 
                        collaboration_id=collaboration.collaboration_id,
                        participants=participant_ids)
        
        return collaboration.collaboration_id
    
    async def join_collaboration(self, collaboration_id: str) -> bool:
        """Join an existing collaboration"""
        if collaboration_id in self.active_collaborations:
            collaboration = self.active_collaborations[collaboration_id]
            
            if self.agent_id not in collaboration.participants:
                collaboration.participants.append(self.agent_id)
                
                # Notify coordinator
                message = A2AMessage(
                    type=A2AMessageType.COLLABORATION_JOIN,
                    sender_id=self.agent_id,
                    recipient_id=collaboration.coordinator_id,
                    payload={
                        "collaboration_id": collaboration_id,
                        "participant_id": self.agent_id
                    }
                )
                
                await self.communicator.send_message(message)
                
                self.logger.info("Joined collaboration", collaboration_id=collaboration_id)
                return True
        
        return False
    
    async def leave_collaboration(self, collaboration_id: str) -> bool:
        """Leave a collaboration"""
        if collaboration_id in self.active_collaborations:
            collaboration = self.active_collaborations[collaboration_id]
            
            if self.agent_id in collaboration.participants:
                collaboration.participants.remove(self.agent_id)
                
                # Notify coordinator
                message = A2AMessage(
                    type=A2AMessageType.COLLABORATION_LEAVE,
                    sender_id=self.agent_id,
                    recipient_id=collaboration.coordinator_id,
                    payload={
                        "collaboration_id": collaboration_id,
                        "participant_id": self.agent_id
                    }
                )
                
                await self.communicator.send_message(message)
                
                self.logger.info("Left collaboration", collaboration_id=collaboration_id)
                
                # Remove from active if we're no longer a participant
                if collaboration.coordinator_id != self.agent_id:
                    del self.active_collaborations[collaboration_id]
                
                return True
        
        return False
    
    def get_active_collaborations(self) -> List[ActiveCollaboration]:
        """Get all active collaborations"""
        return list(self.active_collaborations.values())
    
    def get_collaboration(self, collaboration_id: str) -> Optional[ActiveCollaboration]:
        """Get specific collaboration"""
        return self.active_collaborations.get(collaboration_id)
    
    async def _monitor_collaborations(self):
        """Monitor active collaborations"""
        while self.running:
            try:
                current_time = datetime.now()
                stale_collaborations = []
                
                for collab_id, collaboration in self.active_collaborations.items():
                    # Check for stale collaborations (no activity for 2 hours)
                    if collaboration.created_at:
                        elapsed = (current_time - collaboration.created_at).total_seconds()
                        if elapsed > 7200 and collaboration.status == CollaborationStatus.FORMING:
                            stale_collaborations.append(collab_id)
                
                # Clean up stale collaborations
                for collab_id in stale_collaborations:
                    collaboration = self.active_collaborations.pop(collab_id)
                    collaboration.status = CollaborationStatus.FAILED
                    self.collaboration_history.append(collaboration)
                    
                    self.logger.info("Removed stale collaboration", collaboration_id=collab_id)
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error("Error monitoring collaborations", error=str(e))
                await asyncio.sleep(300)