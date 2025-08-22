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
    
    def __init__(self, config: Optional[ToolConfig] = None):
        super().__init__()
        if config:
            self.name = config.name
            self.description = config.description
            self.return_direct = config.return_direct
            self.verbose = config.verbose
            self.max_retries = config.max_retries
        
        self.logger = logger.bind(tool_name=self.name)
    
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