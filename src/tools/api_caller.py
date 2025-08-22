from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field
import httpx
import json
import asyncio

from .base import BaseTool, ToolConfig


class APICallInput(BaseModel):
    """Input for API call tool"""
    url: str = Field(..., description="API endpoint URL")
    method: str = Field(default="GET", description="HTTP method (GET, POST, PUT, DELETE)")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Request headers")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Request body data")
    params: Optional[Dict[str, str]] = Field(default=None, description="URL parameters")
    timeout: int = Field(default=30, description="Request timeout in seconds")


class APICallerTool(BaseTool):
    """Tool for making API calls"""
    
    name: str = "api_caller"
    description: str = "Make HTTP API calls. Supports GET, POST, PUT, DELETE methods with headers and data."
    args_schema: Type[BaseModel] = APICallInput
    
    def __init__(self, config: Optional[ToolConfig] = None, default_headers: Optional[Dict[str, str]] = None):
        if not config:
            config = ToolConfig(
                name=self.name,
                description=self.description
            )
        super().__init__(config)
        self.default_headers = default_headers or {"User-Agent": "AI-Agent-Workflow/1.0"}
    
    def execute(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Any:
        """Execute API call synchronously"""
        try:
            # Merge headers
            request_headers = self.default_headers.copy()
            if headers:
                request_headers.update(headers)
            
            # Validate method
            method = method.upper()
            if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                return f"Error: Invalid HTTP method: {method}"
            
            # Make request
            with httpx.Client(timeout=timeout) as client:
                response = client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=data if data and method in ["POST", "PUT", "PATCH"] else None,
                    params=params
                )
            
            # Format response
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": str(response.url)
            }
            
            # Try to parse JSON response
            try:
                result["json"] = response.json()
            except:
                result["text"] = response.text
            
            self.logger.info("API call completed", 
                           url=url, 
                           method=method, 
                           status_code=response.status_code)
            
            return json.dumps(result, indent=2)
            
        except httpx.TimeoutException:
            return f"Error: Request timeout after {timeout} seconds"
        except httpx.RequestError as e:
            return f"Error: Request failed - {str(e)}"
        except Exception as e:
            self.logger.error("API call error", error=str(e))
            return f"Error: {str(e)}"
    
    async def aexecute(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Any:
        """Execute API call asynchronously"""
        try:
            # Merge headers
            request_headers = self.default_headers.copy()
            if headers:
                request_headers.update(headers)
            
            # Validate method
            method = method.upper()
            if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                return f"Error: Invalid HTTP method: {method}"
            
            # Make request
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=data if data and method in ["POST", "PUT", "PATCH"] else None,
                    params=params
                )
            
            # Format response
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": str(response.url)
            }
            
            # Try to parse JSON response
            try:
                result["json"] = response.json()
            except:
                result["text"] = response.text
            
            self.logger.info("API call completed", 
                           url=url, 
                           method=method, 
                           status_code=response.status_code)
            
            return json.dumps(result, indent=2)
            
        except httpx.TimeoutException:
            return f"Error: Request timeout after {timeout} seconds"
        except httpx.RequestError as e:
            return f"Error: Request failed - {str(e)}"
        except Exception as e:
            self.logger.error("API call error", error=str(e))
            return f"Error: {str(e)}"