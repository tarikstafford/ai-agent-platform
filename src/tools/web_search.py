from typing import Any, List, Optional, Type
from pydantic import BaseModel, Field
import httpx
import asyncio

from .base import BaseTool, ToolConfig


class WebSearchInput(BaseModel):
    """Input for web search tool"""
    query: str = Field(..., description="Search query")
    max_results: int = Field(default=5, description="Maximum number of results to return")


class SearchResult(BaseModel):
    """A single search result"""
    title: str
    url: str
    snippet: str


class WebSearchTool(BaseTool):
    """Tool for searching the web"""
    
    name: str = "web_search"
    description: str = "Search the web for information. Returns titles, URLs, and snippets of relevant pages."
    args_schema: Type[BaseModel] = WebSearchInput
    
    def __init__(self, config: Optional[ToolConfig] = None, api_key: Optional[str] = None):
        if not config:
            config = ToolConfig(
                name=self.name,
                description=self.description
            )
        super().__init__(config)
        self.api_key = api_key
        
    def execute(self, query: str, max_results: int = 5) -> Any:
        """Execute web search synchronously"""
        # This is a mock implementation
        # In production, you would use a real search API like Google Custom Search, Bing, or SerpAPI
        
        self.logger.info("Performing web search", query=query, max_results=max_results)
        
        # Mock results
        mock_results = [
            SearchResult(
                title=f"Result {i+1} for: {query}",
                url=f"https://example.com/result{i+1}",
                snippet=f"This is a snippet for search result {i+1} about {query}..."
            )
            for i in range(min(max_results, 3))
        ]
        
        # Format results
        formatted_results = []
        for result in mock_results:
            formatted_results.append(
                f"**{result.title}**\n"
                f"URL: {result.url}\n"
                f"{result.snippet}\n"
            )
        
        return "\n---\n".join(formatted_results) if formatted_results else "No results found."
    
    async def aexecute(self, query: str, max_results: int = 5) -> Any:
        """Execute web search asynchronously"""
        # In a real implementation, this would make async HTTP requests
        await asyncio.sleep(0.1)  # Simulate API call
        return self.execute(query, max_results)