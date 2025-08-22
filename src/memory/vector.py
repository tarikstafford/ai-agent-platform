from typing import Any, Dict, List, Optional
import uuid
from datetime import datetime
import chromadb
from chromadb.config import Settings

from .base import BaseMemory, MemoryConfig, MemoryEntry


class VectorMemory(BaseMemory):
    """Vector database memory using ChromaDB"""
    
    def __init__(self, config: MemoryConfig, collection_name: str = "agent_memory"):
        super().__init__(config)
        self.collection_name = collection_name
        
        # Initialize ChromaDB
        if config.persist and config.persist_path:
            self.client = chromadb.PersistentClient(
                path=config.persist_path,
                settings=Settings(anonymized_telemetry=False)
            )
        else:
            self.client = chromadb.EphemeralClient(
                settings=Settings(anonymized_telemetry=False)
            )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    async def add(self, content: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add content to vector memory"""
        entry_id = str(uuid.uuid4())
        
        # Convert content to string for embedding
        if isinstance(content, dict):
            text_content = " ".join(str(v) for v in content.values())
        else:
            text_content = str(content)
        
        # Prepare metadata
        entry_metadata = metadata or {}
        entry_metadata["timestamp"] = datetime.now().isoformat()
        
        # Add to ChromaDB
        self.collection.add(
            documents=[text_content],
            metadatas=[entry_metadata],
            ids=[entry_id]
        )
        
        # Also add to local entries for compatibility
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            metadata=entry_metadata,
            timestamp=datetime.now()
        )
        self.entries.append(entry)
        
        # Enforce max entries
        if len(self.entries) > self.config.max_entries:
            # Remove oldest entries
            to_remove = self.entries[:len(self.entries) - self.config.max_entries]
            for entry in to_remove:
                try:
                    self.collection.delete(ids=[entry.id])
                except:
                    pass
            self.entries = self.entries[-self.config.max_entries:]
        
        return entry_id
    
    async def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory entry"""
        try:
            result = self.collection.get(ids=[entry_id])
            
            if result["documents"]:
                # Find in local entries
                for entry in self.entries:
                    if entry.id == entry_id:
                        return entry
                
                # Create from ChromaDB result
                return MemoryEntry(
                    id=entry_id,
                    content=result["documents"][0],
                    metadata=result["metadatas"][0] if result["metadatas"] else {},
                    timestamp=datetime.fromisoformat(
                        result["metadatas"][0].get("timestamp", datetime.now().isoformat())
                    )
                )
        except:
            pass
        
        return None
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search vector memory using semantic similarity"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit
            )
            
            entries = []
            if results["ids"] and results["ids"][0]:
                for i, entry_id in enumerate(results["ids"][0]):
                    # Try to find in local entries first
                    local_entry = None
                    for entry in self.entries:
                        if entry.id == entry_id:
                            local_entry = entry
                            break
                    
                    if local_entry:
                        entries.append(local_entry)
                    else:
                        # Create from query result
                        entry = MemoryEntry(
                            id=entry_id,
                            content=results["documents"][0][i],
                            metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                            timestamp=datetime.fromisoformat(
                                results["metadatas"][0][i].get("timestamp", datetime.now().isoformat())
                            )
                        )
                        entries.append(entry)
            
            return entries
            
        except Exception as e:
            # Fallback to simple search
            return await super().search(query, limit)
    
    async def clear(self) -> None:
        """Clear all vector memory"""
        try:
            # Delete collection and recreate
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except:
            pass
        
        self.entries.clear()
    
    def get_similar_memories(self, content: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get memories similar to the given content"""
        try:
            results = self.collection.query(
                query_texts=[content],
                n_results=limit
            )
            
            memories = []
            if results["ids"] and results["ids"][0]:
                for i, entry_id in enumerate(results["ids"][0]):
                    memory = {
                        "id": entry_id,
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else None
                    }
                    memories.append(memory)
            
            return memories
            
        except:
            return []