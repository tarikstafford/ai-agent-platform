"""
Test suite for A2A (Agent-to-Agent) Communication Protocol
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock

# Import A2A components
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from a2a.protocol import (
    A2AMessage, A2AMessageType, A2ARequest, A2AResponse,
    TaskDelegation, CollaborationRequest, AgentProfile, AgentCapability
)
from a2a.communicator import A2ACommunicator
from a2a.discovery import AgentDiscovery
from a2a.tasks import TaskManager, CollaborationManager
from agents import AgentConfig, BaseAgent


class TestA2AProtocol:
    """Test A2A protocol message structures"""
    
    def test_a2a_message_creation(self):
        """Test A2A message creation"""
        message = A2AMessage(
            type=A2AMessageType.PING,
            sender_id="agent_001",
            recipient_id="agent_002",
            payload={"test": "data"}
        )
        
        assert message.type == A2AMessageType.PING
        assert message.sender_id == "agent_001"
        assert message.recipient_id == "agent_002"
        assert message.payload["test"] == "data"
        assert isinstance(message.timestamp, datetime)
    
    def test_a2a_request_creation(self):
        """Test A2A request message creation"""
        request = A2ARequest(
            type=A2AMessageType.TASK_REQUEST,
            sender_id="agent_001",
            recipient_id="agent_002",
            expects_response=True,
            response_timeout=30,
            payload={"task": "calculation"}
        )
        
        assert request.expects_response is True
        assert request.response_timeout == 30
        assert request.payload["task"] == "calculation"
    
    def test_a2a_response_creation(self):
        """Test A2A response message creation"""
        response = A2AResponse(
            type=A2AMessageType.TASK_RESPONSE,
            sender_id="agent_002",
            recipient_id="agent_001",
            correlation_id="request_123",
            success=True,
            result={"result": 42}
        )
        
        assert response.success is True
        assert response.result["result"] == 42
        assert response.correlation_id == "request_123"
    
    def test_task_delegation_creation(self):
        """Test task delegation structure"""
        task = TaskDelegation(
            task_type="calculation",
            task_description="Perform mathematical calculation",
            task_data={"expression": "2 + 2"},
            required_capabilities=["math", "calculation"],
            priority=5
        )
        
        assert task.task_type == "calculation"
        assert task.task_data["expression"] == "2 + 2"
        assert "math" in task.required_capabilities
        assert task.priority == 5
    
    def test_collaboration_request_creation(self):
        """Test collaboration request structure"""
        collab = CollaborationRequest(
            title="Research Project",
            description="Collaborative AI research",
            required_agents=3,
            required_capabilities=["research", "analysis"],
            coordinator_id="agent_001"
        )
        
        assert collab.title == "Research Project"
        assert collab.required_agents == 3
        assert "research" in collab.required_capabilities
        assert collab.coordinator_id == "agent_001"


class TestAgentCapabilities:
    """Test agent capability system"""
    
    def test_agent_capability_creation(self):
        """Test agent capability creation"""
        capability = AgentCapability(
            name="calculation",
            description="Mathematical calculations",
            version="1.0",
            parameters={"max_precision": 10}
        )
        
        assert capability.name == "calculation"
        assert capability.description == "Mathematical calculations"
        assert capability.version == "1.0"
        assert capability.parameters["max_precision"] == 10
    
    def test_agent_profile_creation(self):
        """Test agent profile creation"""
        capabilities = [
            AgentCapability(name="calc", description="Math"),
            AgentCapability(name="search", description="Web search")
        ]
        
        profile = AgentProfile(
            agent_id="agent_001",
            name="MathBot",
            description="Mathematical agent",
            capabilities=capabilities,
            status="available",
            max_concurrent_tasks=5
        )
        
        assert profile.agent_id == "agent_001"
        assert profile.name == "MathBot"
        assert len(profile.capabilities) == 2
        assert profile.can_handle_task(["calc"])
        assert not profile.can_handle_task(["unknown_capability"])
    
    def test_agent_profile_capability_matching(self):
        """Test capability matching logic"""
        capabilities = [
            AgentCapability(name="math", description="Math"),
            AgentCapability(name="analysis", description="Analysis")
        ]
        
        profile = AgentProfile(
            agent_id="agent_001",
            name="Analyst",
            description="Analysis agent",
            capabilities=capabilities,
            current_tasks=2,
            max_concurrent_tasks=5
        )
        
        # Should handle tasks with available capabilities
        assert profile.can_handle_task(["math"])
        assert profile.can_handle_task(["analysis"])
        assert profile.can_handle_task(["math", "analysis"])
        
        # Should not handle unknown capabilities
        assert not profile.can_handle_task(["unknown"])
        
        # Should not handle when at capacity
        profile.current_tasks = 5
        assert not profile.can_handle_task(["math"])


class MockAgent(BaseAgent):
    """Mock agent for testing"""
    
    def __init__(self, config, agent_id=None):
        super().__init__(config, agent_id)
        self.responses = []
    
    async def think(self, input_data):
        return Mock(content="Mock response", success=True)
    
    async def act(self, action):
        return {"status": "completed"}


class TestA2ACommunicator:
    """Test A2A communicator functionality"""
    
    @pytest.fixture
    def communicator(self):
        """Create test communicator"""
        return A2ACommunicator("test_agent", "TestAgent")
    
    def test_communicator_initialization(self, communicator):
        """Test communicator initialization"""
        assert communicator.agent_id == "test_agent"
        assert communicator.agent_name == "TestAgent"
        assert communicator.running is False
        assert len(communicator.message_handlers) == 0
    
    def test_message_handler_registration(self, communicator):
        """Test message handler registration"""
        handler = Mock()
        
        communicator.register_message_handler(A2AMessageType.PING, handler)
        
        assert len(communicator.message_handlers[A2AMessageType.PING]) == 1
        assert handler in communicator.message_handlers[A2AMessageType.PING]
    
    @pytest.mark.asyncio
    async def test_message_queueing(self, communicator):
        """Test message queueing"""
        message = A2AMessage(
            type=A2AMessageType.PING,
            sender_id="test_agent",
            recipient_id="other_agent"
        )
        
        # Start communicator
        await communicator.start()
        
        # Queue message
        message_id = await communicator.send_message(message)
        
        assert message_id == message.id
        assert message.id in communicator.pending_deliveries
        
        # Stop communicator
        await communicator.stop()
    
    @pytest.mark.asyncio
    async def test_message_receiving(self, communicator):
        """Test message receiving"""
        received_messages = []
        
        def message_handler(message):
            received_messages.append(message)
        
        communicator.register_message_handler(A2AMessageType.PING, message_handler)
        
        # Start communicator
        await communicator.start()
        
        # Receive message
        message = A2AMessage(
            type=A2AMessageType.PING,
            sender_id="other_agent",
            recipient_id="test_agent"
        )
        
        await communicator.receive_message(message)
        
        # Give some time for processing
        await asyncio.sleep(0.1)
        
        assert len(received_messages) == 1
        assert received_messages[0].sender_id == "other_agent"
        
        # Stop communicator
        await communicator.stop()


class TestAgentDiscovery:
    """Test agent discovery functionality"""
    
    @pytest.fixture
    def mock_communicator(self):
        """Create mock communicator"""
        communicator = Mock()
        communicator.agent_name = "TestAgent"
        return communicator
    
    @pytest.fixture
    def discovery(self, mock_communicator):
        """Create test discovery service"""
        return AgentDiscovery("test_agent", mock_communicator)
    
    def test_discovery_initialization(self, discovery):
        """Test discovery service initialization"""
        assert discovery.agent_id == "test_agent"
        assert len(discovery.own_capabilities) == 0
        assert len(discovery.discovered_agents) == 0
    
    def test_capability_management(self, discovery):
        """Test capability management"""
        capability = AgentCapability(
            name="test_capability",
            description="Test capability"
        )
        
        discovery.add_capability(capability)
        
        assert len(discovery.own_capabilities) == 1
        assert discovery.own_capabilities[0].name == "test_capability"
        
        discovery.remove_capability("test_capability")
        
        assert len(discovery.own_capabilities) == 0
    
    def test_agent_profile_updating(self, discovery):
        """Test agent profile updates"""
        capabilities = [
            AgentCapability(name="calc", description="Math")
        ]
        
        profile = AgentProfile(
            agent_id="other_agent",
            name="OtherAgent",
            description="Test agent",
            capabilities=capabilities
        )
        
        discovery._update_agent_profile(profile)
        
        assert "other_agent" in discovery.discovered_agents
        assert "calc" in discovery.capability_index
        assert "other_agent" in discovery.capability_index["calc"]
    
    def test_capability_search(self, discovery):
        """Test capability-based agent search"""
        # Add test agents
        math_agent = AgentProfile(
            agent_id="math_agent",
            name="MathAgent",
            description="Math specialist",
            capabilities=[AgentCapability(name="math", description="Math")]
        )
        
        search_agent = AgentProfile(
            agent_id="search_agent", 
            name="SearchAgent",
            description="Search specialist",
            capabilities=[AgentCapability(name="search", description="Search")]
        )
        
        discovery._update_agent_profile(math_agent)
        discovery._update_agent_profile(search_agent)
        
        # Test capability search
        math_agents = discovery._find_agents_by_capabilities(["math"])
        search_agents = discovery._find_agents_by_capabilities(["search"])
        all_agents = discovery._find_agents_by_capabilities([])
        
        assert len(math_agents) == 1
        assert math_agents[0].agent_id == "math_agent"
        
        assert len(search_agents) == 1 
        assert search_agents[0].agent_id == "search_agent"
        
        assert len(all_agents) == 2


class TestTaskManager:
    """Test task management functionality"""
    
    @pytest.fixture
    def mock_communicator(self):
        """Create mock communicator"""
        communicator = Mock()
        communicator.send_request = AsyncMock()
        return communicator
    
    @pytest.fixture
    def task_manager(self, mock_communicator):
        """Create test task manager"""
        return TaskManager("test_agent", mock_communicator)
    
    def test_task_manager_initialization(self, task_manager):
        """Test task manager initialization"""
        assert task_manager.agent_id == "test_agent"
        assert len(task_manager.active_tasks) == 0
        assert len(task_manager.task_handlers) == 0
    
    def test_task_handler_registration(self, task_manager):
        """Test task handler registration"""
        def test_handler(task_data):
            return {"result": "test"}
        
        task_manager.register_task_handler("test_task", test_handler)
        
        assert "test_task" in task_manager.task_handlers
        assert task_manager.task_handlers["test_task"] == test_handler
    
    @pytest.mark.asyncio
    async def test_task_execution(self, task_manager):
        """Test task execution"""
        # Register handler
        async def calculation_handler(task_data):
            expression = task_data.get("expression", "")
            return {"result": eval(expression)}
        
        task_manager.register_task_handler("calculation", calculation_handler)
        
        # Create task delegation
        task = TaskDelegation(
            task_type="calculation",
            task_description="Test calculation",
            task_data={"expression": "2 + 2"}
        )
        
        # Execute task
        result = await task_manager.execute_task(task)
        
        assert result["success"] is True
        assert result["result"]["result"] == 4
        assert task.task_id in task_manager.active_tasks
    
    def test_assignment_strategies(self, task_manager):
        """Test task assignment strategies"""
        # Test strategy registration
        def custom_strategy(agents, task):
            return agents[0].agent_id if agents else None
        
        task_manager.assignment_strategies["custom"] = custom_strategy
        
        assert "custom" in task_manager.assignment_strategies
        assert task_manager.assignment_strategies["custom"] == custom_strategy


class TestA2AIntegration:
    """Integration tests for A2A system"""
    
    @pytest.mark.asyncio
    async def test_agent_a2a_initialization(self):
        """Test A2A initialization in agents"""
        config = AgentConfig(
            name="TestAgent",
            description="Test agent",
            a2a_enabled=True,
            a2a_capabilities=["test", "calculation"]
        )
        
        agent = MockAgent(config, agent_id="test_agent_001")
        
        # Check A2A components
        assert hasattr(agent, 'a2a_communicator')
        assert hasattr(agent, 'a2a_discovery')
        assert agent.config.a2a_enabled is True
        assert "test" in agent.config.a2a_capabilities
    
    @pytest.mark.asyncio
    async def test_agent_task_handling(self):
        """Test agent task handling"""
        config = AgentConfig(
            name="TestAgent",
            description="Test agent",
            a2a_enabled=True,
            a2a_capabilities=["calculation"]
        )
        
        agent = MockAgent(config, agent_id="test_agent_001")
        
        # Register task handler
        async def calc_handler(task_data):
            return {"result": 42}
        
        agent.register_task_handler("calculation", calc_handler)
        
        assert "calculation" in agent.a2a_task_handlers
        assert agent.a2a_task_handlers["calculation"] == calc_handler
    
    @pytest.mark.asyncio
    async def test_end_to_end_communication(self):
        """Test end-to-end A2A communication"""
        # Create two test agents
        agent1_config = AgentConfig(
            name="Agent1",
            a2a_enabled=True,
            a2a_capabilities=["sender"]
        )
        
        agent2_config = AgentConfig(
            name="Agent2", 
            a2a_enabled=True,
            a2a_capabilities=["receiver"]
        )
        
        agent1 = MockAgent(agent1_config, "agent_001")
        agent2 = MockAgent(agent2_config, "agent_002")
        
        # Start A2A communication
        await agent1.start_a2a_communication()
        await agent2.start_a2a_communication()
        
        # Test message sending (mock level)
        if hasattr(agent1, 'a2a_communicator') and agent1.a2a_communicator:
            message_id = await agent1.send_message_to_agent(
                recipient_id="agent_002",
                message_type="ping",
                payload={"test": "data"}
            )
            
            assert message_id is not None
        
        # Stop A2A communication
        await agent1.stop_a2a_communication()
        await agent2.stop_a2a_communication()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])