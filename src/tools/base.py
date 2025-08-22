from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool as LangchainBaseTool
import structlog

logger = structlog.get_logger()


class ToolConfig(BaseModel):
    """Configuration for a tool"""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    return_direct: bool = Field(default=False, description="Return result directly to user")
    verbose: bool = Field(default=False, description="Enable verbose logging")
    max_retries: int = Field(default=3, description="Maximum retries on failure")


class BaseTool(LangchainBaseTool):
    """Base class for all tools"""
    
    name: str = "base_tool"
    description: str = "Base tool class"
    args_schema: Optional[Type[BaseModel]] = None
    return_direct: bool = False
    
    def __init__(self, config: Optional[ToolConfig] = None, **kwargs):
        # Prepare arguments for parent initialization
        init_kwargs = {}
        
        if config:
            init_kwargs.update({
                'name': config.name,
                'description': config.description,
                'return_direct': config.return_direct
            })
        
        # Add any additional kwargs
        init_kwargs.update(kwargs)
        
        # Initialize parent class with proper arguments
        super().__init__(**init_kwargs)
        
        # Set additional attributes using object.__setattr__ to bypass Pydantic
        if config:
            object.__setattr__(self, 'verbose', config.verbose)
            object.__setattr__(self, '_max_retries', config.max_retries)
        else:
            object.__setattr__(self, 'verbose', False)
            object.__setattr__(self, '_max_retries', 3)
        
        object.__setattr__(self, 'logger', logger.bind(tool_name=self.name))
    
    def _run(self, *args, **kwargs) -> str:
        """Synchronous implementation"""
        try:
            self.logger.info("Tool execution started", args=args, kwargs=kwargs)
            result = self.execute(*args, **kwargs)
            self.logger.info("Tool execution completed", result=result)
            return str(result)
        except Exception as e:
            self.logger.error("Tool execution failed", error=str(e))
            return f"Error: {str(e)}"
    
    async def _arun(self, *args, **kwargs) -> str:
        """Asynchronous implementation"""
        try:
            self.logger.info("Tool async execution started", args=args, kwargs=kwargs)
            result = await self.aexecute(*args, **kwargs)
            self.logger.info("Tool async execution completed", result=result)
            return str(result)
        except Exception as e:
            self.logger.error("Tool async execution failed", error=str(e))
            return f"Error: {str(e)}"
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute the tool synchronously"""
        pass
    
    async def aexecute(self, *args, **kwargs) -> Any:
        """Execute the tool asynchronously (default to sync implementation)"""
        return self.execute(*args, **kwargs)