from typing import Any, Dict, List, Optional, Union
import asyncio

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI

from .base import BaseAgent, AgentConfig, AgentResponse, AgentState


class ConversationalAgent(BaseAgent):
    """A conversational agent that can engage in dialogue"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.conversation_history: List[Union[HumanMessage, AIMessage, SystemMessage]] = []
        self.system_prompt = f"""You are {config.name}, a helpful AI assistant.
{config.description}

Your responses should be helpful, accurate, and conversational."""
        
        # Initialize with system message
        self.conversation_history.append(SystemMessage(content=self.system_prompt))
        
    async def think(self, input_data: Union[str, Dict[str, Any]]) -> AgentResponse:
        """Process user input and generate a conversational response"""
        try:
            # Convert input to string if needed
            if isinstance(input_data, dict):
                user_message = input_data.get("message", str(input_data))
            else:
                user_message = str(input_data)
            
            # Add user message to history
            self.conversation_history.append(HumanMessage(content=user_message))
            
            # Create LLM
            llm = ChatOpenAI(
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            
            # Generate response
            self.logger.info("Generating response", message_count=len(self.conversation_history))
            response = await llm.ainvoke(self.conversation_history)
            
            # Add assistant response to history
            self.conversation_history.append(AIMessage(content=response.content))
            
            return AgentResponse(
                content=response.content,
                success=True,
                metadata={
                    "model": self.config.model,
                    "conversation_length": len(self.conversation_history),
                    "tokens_used": response.response_metadata.get("token_usage", {})
                }
            )
            
        except Exception as e:
            self.logger.error("Error in conversational agent", error=str(e))
            return AgentResponse(
                content="I apologize, but I encountered an error processing your request.",
                success=False,
                error=str(e),
                state=AgentState.ERROR
            )
    
    async def act(self, action: Dict[str, Any]) -> Any:
        """Execute an action (not typically used for conversational agents)"""
        action_type = action.get("type", "unknown")
        
        if action_type == "clear_history":
            self.clear_conversation()
            return {"status": "success", "message": "Conversation history cleared"}
        
        return {"status": "error", "message": f"Unknown action: {action_type}"}
    
    def clear_conversation(self) -> None:
        """Clear conversation history but keep system prompt"""
        self.conversation_history = [SystemMessage(content=self.system_prompt)]
        self.logger.info("Conversation history cleared")
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history in a serializable format"""
        history = []
        for msg in self.conversation_history:
            if isinstance(msg, SystemMessage):
                history.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
        return history