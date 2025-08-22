import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.agents import BaseAgent, AgentConfig, AgentResponse, AgentState
from src.agents import ConversationalAgent, ReactiveAgent, PlannerAgent


class TestAgentConfig:
    """Test AgentConfig model"""
    
    def test_default_config(self):
        config = AgentConfig(name="test")
        assert config.name == "test"
        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 2000
        
    def test_custom_config(self):
        config = AgentConfig(
            name="custom",
            description="Custom agent",
            model="gpt-3.5-turbo",
            temperature=0.3,
            max_tokens=500
        )
        assert config.name == "custom"
        assert config.description == "Custom agent"
        assert config.model == "gpt-3.5-turbo"
        assert config.temperature == 0.3
        assert config.max_tokens == 500


class TestAgentResponse:
    """Test AgentResponse dataclass"""
    
    def test_successful_response(self):
        response = AgentResponse(content="Success")
        assert response.content == "Success"
        assert response.success is True
        assert response.error is None
        assert response.state == AgentState.COMPLETED
        
    def test_error_response(self):
        response = AgentResponse(
            content="",
            success=False,
            error="Test error",
            state=AgentState.ERROR
        )
        assert response.content == ""
        assert response.success is False
        assert response.error == "Test error"
        assert response.state == AgentState.ERROR


class TestBaseAgent:
    """Test BaseAgent abstract class"""
    
    class ConcreteAgent(BaseAgent):
        """Concrete implementation for testing"""
        
        async def think(self, input_data):
            return AgentResponse(content=f"Processed: {input_data}")
        
        async def act(self, action):
            return {"action": action, "result": "success"}
    
    def test_agent_initialization(self, agent_config):
        agent = self.ConcreteAgent(agent_config)
        assert agent.config == agent_config
        assert agent.state == AgentState.IDLE
        assert agent.memory == []
        assert agent.tools == {}
        assert agent.iteration_count == 0
    
    @pytest.mark.asyncio
    async def test_agent_run_success(self, agent_config):
        agent = self.ConcreteAgent(agent_config)
        response = await agent.run("test input")
        
        assert response.success is True
        assert response.content == "Processed: test input"
        assert agent.state == AgentState.COMPLETED
        assert len(agent.memory) == 1
    
    @pytest.mark.asyncio
    async def test_agent_run_error(self, agent_config):
        agent = self.ConcreteAgent(agent_config)
        
        # Mock think to raise an error
        agent.think = AsyncMock(side_effect=Exception("Test error"))
        
        response = await agent.run("test input")
        
        assert response.success is False
        assert response.error == "Test error"
        assert agent.state == AgentState.ERROR
    
    def test_add_tool(self, agent_config):
        agent = self.ConcreteAgent(agent_config)
        mock_tool = Mock()
        
        agent.add_tool("test_tool", mock_tool)
        
        assert "test_tool" in agent.tools
        assert agent.tools["test_tool"] == mock_tool
    
    def test_memory_operations(self, agent_config):
        agent = self.ConcreteAgent(agent_config)
        
        # Add to memory
        agent.memory.append({"test": "data"})
        assert len(agent.get_memory()) == 1
        
        # Clear memory
        agent.clear_memory()
        assert len(agent.get_memory()) == 0


class TestConversationalAgent:
    """Test ConversationalAgent"""
    
    @pytest.mark.asyncio
    @patch('src.agents.conversational.ChatOpenAI')
    async def test_conversational_response(self, mock_llm, agent_config):
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = "Hello! How can I help you?"
        mock_response.response_metadata = {"token_usage": {"total": 10}}
        
        mock_llm_instance = AsyncMock()
        mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.return_value = mock_llm_instance
        
        # Create agent and test
        agent = ConversationalAgent(agent_config)
        response = await agent.think("Hello")
        
        assert response.success is True
        assert response.content == "Hello! How can I help you?"
        assert len(agent.conversation_history) == 3  # system + user + assistant
    
    def test_clear_conversation(self, agent_config):
        agent = ConversationalAgent(agent_config)
        
        # Add some messages
        from langchain.schema import HumanMessage
        agent.conversation_history.append(HumanMessage(content="Test"))
        
        # Clear
        agent.clear_conversation()
        
        # Should only have system message
        assert len(agent.conversation_history) == 1
        assert agent.conversation_history[0].content.startswith("You are test_agent")


class TestReactiveAgent:
    """Test ReactiveAgent"""
    
    def test_reactive_agent_initialization(self, agent_config):
        agent = ReactiveAgent(agent_config)
        assert agent.tool_instances == []
        assert agent.agent_executor is None
    
    @pytest.mark.asyncio
    async def test_act_with_tool(self, agent_config):
        agent = ReactiveAgent(agent_config)
        
        # Create mock tool
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.arun = AsyncMock(return_value="Tool result")
        
        agent.add_langchain_tool(mock_tool)
        
        # Test act
        result = await agent.act({
            "tool": "test_tool",
            "input": {"test": "data"}
        })
        
        assert result["success"] is True
        assert result["result"] == "Tool result"
    
    @pytest.mark.asyncio
    async def test_act_tool_not_found(self, agent_config):
        agent = ReactiveAgent(agent_config)
        
        result = await agent.act({
            "tool": "nonexistent_tool",
            "input": {}
        })
        
        assert result["success"] is False
        assert "not found" in result["error"]


class TestPlannerAgent:
    """Test PlannerAgent"""
    
    def test_planner_initialization(self, agent_config):
        agent = PlannerAgent(agent_config)
        assert agent.current_plan is None
        assert agent.execution_agents == {}
    
    @pytest.mark.asyncio
    @patch('src.agents.planner.ChatOpenAI')
    async def test_create_plan(self, mock_llm, agent_config):
        # Mock plan response
        from src.agents.planner import Plan, Task, TaskStatus
        
        mock_plan = Plan(
            goal="Test goal",
            tasks=[
                Task(id=1, name="Task 1", description="First task"),
                Task(id=2, name="Task 2", description="Second task", dependencies=[1])
            ]
        )
        
        # Setup mock
        mock_parser = Mock()
        mock_parser.invoke = AsyncMock(return_value=mock_plan)
        
        with patch('src.agents.planner.ChatPromptTemplate'):
            with patch('src.agents.planner.PydanticOutputParser', return_value=mock_parser):
                agent = PlannerAgent(agent_config)
                response = await agent.think("Test goal")
        
                assert response.success is True
                assert "Test goal" in response.content
                assert agent.current_plan is not None
                assert len(agent.current_plan.tasks) == 2