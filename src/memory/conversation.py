from typing import Any, Dict, List, Optional
import uuid
from datetime import datetime, timedelta

from .base import BaseMemory, MemoryConfig, MemoryEntry


class ConversationMemory(BaseMemory):
    """Simple conversation memory implementation"""
    
    def __init__(self, config: MemoryConfig):
        super().__init__(config)
        
    async def add(self, content: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a conversation turn to memory"""
        entry_id = str(uuid.uuid4())
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            metadata=metadata or {},
            timestamp=datetime.now()
        )
        
        self.entries.append(entry)
        
        # Enforce max entries
        if len(self.entries) > self.config.max_entries:
            self.entries = self.entries[-self.config.max_entries:]
        
        # Clean up expired entries if TTL is set
        if self.config.ttl_seconds:
            cutoff_time = datetime.now() - timedelta(seconds=self.config.ttl_seconds)
            self.entries = [e for e in self.entries if e.timestamp > cutoff_time]
        
        return entry_id
    
    async def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory entry"""
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search conversation history"""
        results = []
        query_lower = query.lower()
        
        for entry in reversed(self.entries):  # Search most recent first
            if isinstance(entry.content, str) and query_lower in entry.content.lower():
                results.append(entry)
            elif isinstance(entry.content, dict):
                # Search in dict values
                for value in entry.content.values():
                    if isinstance(value, str) and query_lower in value.lower():
                        results.append(entry)
                        break
            
            if len(results) >= limit:
                break
        
        return results
    
    async def clear(self) -> None:
        """Clear all conversation memory"""
        self.entries.clear()
    
    def get_conversation_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get formatted conversation history"""
        entries = self.entries[-limit:] if limit else self.entries
        
        history = []
        for entry in entries:
            if isinstance(entry.content, dict):
                history.append(entry.content)
            else:
                history.append({
                    "content": entry.content,
                    "timestamp": entry.timestamp.isoformat(),
                    "metadata": entry.metadata
                })
        
        return history