from typing import Any, Dict, List, Optional, Union
import json

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from .base import BaseAgent, AgentConfig, AgentResponse, AgentState


class ReactiveAgent(BaseAgent):
    """A reactive agent that can use tools to accomplish tasks"""
    
    def __init__(self, config: AgentConfig, agent_id: Optional[str] = None):
        super().__init__(config, agent_id)
        self.tool_instances: List[BaseTool] = []
        self.agent_executor: Optional[AgentExecutor] = None
        
    async def think(self, input_data: Union[str, Dict[str, Any]]) -> AgentResponse:
        """Process input using ReAct pattern (Reasoning + Acting)"""
        try:
            # Convert input to string if needed
            if isinstance(input_data, dict):
                task = input_data.get("task", str(input_data))
            else:
                task = str(input_data)
            
            # Initialize agent if not done
            if not self.agent_executor:
                self._initialize_agent()
            
            # Execute with agent
            self.logger.info("Starting reactive agent execution", task=task)
            
            result = await self.agent_executor.ainvoke({
                "input": task,
                "chat_history": []
            })
            
            return AgentResponse(
                content=result["output"],
                success=True,
                metadata={
                    "model": self.config.model,
                    "tools_used": self._extract_tools_used(result),
                    "iterations": self.iteration_count
                }
            )
            
        except Exception as e:
            self.logger.error("Error in reactive agent", error=str(e))
            return AgentResponse(
                content=f"Failed to complete task: {str(e)}",
                success=False,
                error=str(e),
                state=AgentState.ERROR
            )
    
    async def act(self, action: Dict[str, Any]) -> Any:
        """Execute a specific action with tools"""
        tool_name = action.get("tool")
        tool_input = action.get("input", {})
        
        if not tool_name:
            return {"error": "No tool specified"}
        
        # Find the tool
        for tool in self.tool_instances:
            if tool.name == tool_name:
                try:
                    result = await tool.arun(tool_input)
                    return {"result": result, "success": True}
                except Exception as e:
                    return {"error": str(e), "success": False}
        
        return {"error": f"Tool '{tool_name}' not found", "success": False}
    
    def add_langchain_tool(self, tool: BaseTool) -> None:
        """Add a LangChain tool to the agent"""
        self.tool_instances.append(tool)
        self.add_tool(tool.name, tool)
        # Reset agent executor to include new tool
        self.agent_executor = None
        
    def _initialize_agent(self) -> None:
        """Initialize the ReAct agent with tools"""
        if not self.tool_instances:
            self.logger.warning("No tools available for reactive agent")
            
        # Create prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are {self.config.name}, a helpful AI assistant with access to tools.
{self.config.description}

Use the tools available to help accomplish the user's task. Think step by step:
1. Understand what the user is asking
2. Determine which tools might be helpful
3. Use the tools to gather information or perform actions
4. Provide a clear and helpful response

Available tools: {[tool.name for tool in self.tool_instances]}"""),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create LLM
        llm = ChatOpenAI(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        
        # Create agent
        agent = create_openai_tools_agent(llm, self.tool_instances, prompt)
        
        # Create executor
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tool_instances,
            verbose=self.config.verbose,
            max_iterations=self.config.max_iterations,
            return_intermediate_steps=True,
            handle_parsing_errors=True,
        )
        
        self.logger.info("Reactive agent initialized", 
                        tools=[tool.name for tool in self.tool_instances])
    
    def _extract_tools_used(self, result: Dict[str, Any]) -> List[str]:
        """Extract list of tools used from agent result"""
        tools_used = []
        if "intermediate_steps" in result:
            for step in result["intermediate_steps"]:
                if len(step) >= 2 and hasattr(step[0], "tool"):
                    tools_used.append(step[0].tool)
        return tools_used