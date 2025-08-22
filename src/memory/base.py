from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class MemoryConfig(BaseModel):
    """Configuration for memory systems"""
    max_entries: int = Field(default=1000, description="Maximum number of memory entries")
    ttl_seconds: Optional[int] = Field(default=None, description="Time to live for entries")
    persist: bool = Field(default=False, description="Whether to persist memory")
    persist_path: Optional[str] = Field(default=None, description="Path for persistence")


class MemoryEntry(BaseModel):
    """A single memory entry"""
    id: str = Field(..., description="Unique identifier")
    content: Any = Field(..., description="Memory content")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    
class BaseMemory(ABC):
    """Base class for memory implementations"""
    
    def __init__(self, config: MemoryConfig):
        self.config = config
        self.entries: List[MemoryEntry] = []
        
    @abstractmethod
    async def add(self, content: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a memory entry"""
        pass
    
    @abstractmethod
    async def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID"""
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search memory entries"""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all memory entries"""
        pass