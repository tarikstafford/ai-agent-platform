"""
A2A Message Store

This module provides storage and retrieval capabilities for A2A messages,
supporting both in-memory ring buffer and optional SQLite persistence.
"""

import asyncio
import json
import sqlite3
import threading
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum

import structlog
from pydantic import BaseModel, Field

from .protocol import A2AMessage, A2AMessageType

logger = structlog.get_logger()


class MessageDirection(str, Enum):
    """Direction of message flow"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageProcessingStatus(str, Enum):
    """Message processing status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRIED = "retried"
    EXPIRED = "expired"


@dataclass
class StoredMessage:
    """Stored message with metadata"""
    id: str
    timestamp: datetime
    direction: MessageDirection
    type: str
    sender_id: str
    recipient_id: Optional[str]
    correlation_id: Optional[str]
    priority: int
    ttl_seconds: int
    payload_summary: str
    full_payload: Optional[Dict[str, Any]]
    size_bytes: int
    processing_status: MessageProcessingStatus
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction.value,
            "type": self.type,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "correlation_id": self.correlation_id,
            "priority": self.priority,
            "ttl_seconds": self.ttl_seconds,
            "payload_summary": self.payload_summary,
            "full_payload_available": self.full_payload is not None,
            "size_bytes": self.size_bytes,
            "processing_status": self.processing_status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class MessageStoreConfig(BaseModel):
    """Configuration for A2A Message Store"""
    max_messages: int = Field(default=5000, gt=0, description="Maximum messages in memory")
    max_age_hours: int = Field(default=24, gt=0, description="Maximum message age in hours")
    payload_summary_length: int = Field(default=512, gt=0, description="Length of payload summary")
    allow_full_payload: bool = Field(default=False, description="Store full payloads")
    persistent_storage: bool = Field(default=False, description="Enable SQLite persistence")
    sqlite_path: str = Field(default="a2a_messages.db", description="SQLite database path")
    enable_sampling: bool = Field(default=False, description="Enable message sampling under load")
    sampling_rate: float = Field(default=0.1, ge=0.0, le=1.0, description="Sampling rate when enabled")


class A2AMessageStore:
    """A2A Message Store with ring buffer and optional persistence"""
    
    def __init__(self, config: Optional[MessageStoreConfig] = None):
        self.config = config or MessageStoreConfig()
        self.logger = logger.bind(component="a2a_message_store")
        
        # In-memory ring buffer
        self._messages: deque = deque(maxlen=self.config.max_messages)
        self._messages_by_id: Dict[str, StoredMessage] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # SQLite connection
        self._sqlite_conn: Optional[sqlite3.Connection] = None
        
        # Statistics
        self._stats = {
            "total_messages_stored": 0,
            "messages_dropped": 0,
            "queries_executed": 0,
            "last_cleanup": None,
            "storage_errors": 0
        }
        
        # Message event callbacks
        self._event_callbacks: List[Callable[[StoredMessage, str], None]] = []
        
        if self.config.persistent_storage:
            self._init_sqlite()
    
    def _init_sqlite(self):
        """Initialize SQLite database"""
        try:
            self._sqlite_conn = sqlite3.connect(
                self.config.sqlite_path,
                check_same_thread=False
            )
            
            # Create messages table
            self._sqlite_conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    type TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    recipient_id TEXT,
                    correlation_id TEXT,
                    priority INTEGER NOT NULL,
                    ttl_seconds INTEGER NOT NULL,
                    payload_summary TEXT NOT NULL,
                    full_payload TEXT,
                    size_bytes INTEGER NOT NULL,
                    processing_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Create indexes
            self._sqlite_conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
                ON messages(timestamp)
            """)
            self._sqlite_conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_sender 
                ON messages(sender_id)
            """)
            self._sqlite_conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_recipient 
                ON messages(recipient_id)
            """)
            self._sqlite_conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_type 
                ON messages(type)
            """)
            self._sqlite_conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_correlation 
                ON messages(correlation_id)
            """)
            
            self._sqlite_conn.commit()
            self.logger.info("SQLite database initialized", path=self.config.sqlite_path)
            
        except Exception as e:
            self.logger.error("Failed to initialize SQLite", error=str(e))
            self._sqlite_conn = None
    
    async def start(self):
        """Start the message store"""
        if self._running:
            return
        
        self._running = True
        
        # Start background cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self.logger.info("A2A Message Store started")
    
    async def stop(self):
        """Stop the message store"""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._sqlite_conn:
            self._sqlite_conn.close()
            self._sqlite_conn = None
        
        self.logger.info("A2A Message Store stopped")
    
    def add_event_callback(self, callback: Callable[[StoredMessage, str], None]):
        """Add callback for message events"""
        self._event_callbacks.append(callback)
    
    def remove_event_callback(self, callback: Callable[[StoredMessage, str], None]):
        """Remove event callback"""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
    
    def log_message(
        self,
        message: A2AMessage,
        direction: MessageDirection,
        processing_status: MessageProcessingStatus = MessageProcessingStatus.PENDING
    ) -> bool:
        """Log a message to the store"""
        try:
            # Check sampling
            if self.config.enable_sampling:
                import random
                if random.random() > self.config.sampling_rate:
                    return True  # "Success" but not stored
            
            # Create stored message
            payload_str = json.dumps(message.payload) if message.payload else "{}"
            payload_summary = payload_str[:self.config.payload_summary_length]
            if len(payload_str) > self.config.payload_summary_length:
                payload_summary += "..."
            
            stored_message = StoredMessage(
                id=message.id,
                timestamp=message.timestamp,
                direction=direction,
                type=message.type.value if hasattr(message.type, 'value') else str(message.type),
                sender_id=message.sender_id,
                recipient_id=message.recipient_id,
                correlation_id=message.correlation_id,
                priority=message.priority,
                ttl_seconds=message.ttl_seconds,
                payload_summary=payload_summary,
                full_payload=message.payload if self.config.allow_full_payload else None,
                size_bytes=len(payload_str.encode('utf-8')),
                processing_status=processing_status
            )
            
            with self._lock:
                # Remove old message if exists
                if message.id in self._messages_by_id:
                    old_message = self._messages_by_id[message.id]
                    try:
                        self._messages.remove(old_message)
                    except ValueError:
                        pass
                
                # Add new message
                self._messages.append(stored_message)
                self._messages_by_id[message.id] = stored_message
                
                # Handle overflow
                while len(self._messages_by_id) > self.config.max_messages:
                    oldest = self._messages.popleft()
                    del self._messages_by_id[oldest.id]
                    self._stats["messages_dropped"] += 1
            
            # Store in SQLite if enabled
            if self._sqlite_conn:
                self._store_in_sqlite(stored_message)
            
            # Update stats
            self._stats["total_messages_stored"] += 1
            
            # Notify callbacks
            for callback in self._event_callbacks:
                try:
                    callback(stored_message, "message_stored")
                except Exception as e:
                    self.logger.warning("Event callback error", error=str(e))
            
            self.logger.debug("Message logged", 
                            message_id=message.id, 
                            direction=direction.value,
                            type=stored_message.type)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to log message", error=str(e))
            self._stats["storage_errors"] += 1
            return False
    
    def _store_in_sqlite(self, message: StoredMessage):
        """Store message in SQLite"""
        try:
            cursor = self._sqlite_conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO messages (
                    id, timestamp, direction, type, sender_id, recipient_id,
                    correlation_id, priority, ttl_seconds, payload_summary,
                    full_payload, size_bytes, processing_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.id,
                message.timestamp.isoformat(),
                message.direction.value,
                message.type,
                message.sender_id,
                message.recipient_id,
                message.correlation_id,
                message.priority,
                message.ttl_seconds,
                message.payload_summary,
                json.dumps(message.full_payload) if message.full_payload else None,
                message.size_bytes,
                message.processing_status.value,
                message.created_at.isoformat(),
                message.updated_at.isoformat()
            ))
            self._sqlite_conn.commit()
            
        except Exception as e:
            self.logger.error("Failed to store in SQLite", error=str(e))
            self._stats["storage_errors"] += 1
    
    def get_message(self, message_id: str) -> Optional[StoredMessage]:
        """Get a specific message by ID"""
        self._stats["queries_executed"] += 1
        
        with self._lock:
            message = self._messages_by_id.get(message_id)
            if message:
                return message
        
        # Try SQLite if available
        if self._sqlite_conn:
            return self._get_from_sqlite(message_id)
        
        return None
    
    def _get_from_sqlite(self, message_id: str) -> Optional[StoredMessage]:
        """Get message from SQLite"""
        try:
            cursor = self._sqlite_conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_stored_message(row)
            
        except Exception as e:
            self.logger.error("Failed to get from SQLite", error=str(e))
        
        return None
    
    def _row_to_stored_message(self, row) -> StoredMessage:
        """Convert SQLite row to StoredMessage"""
        return StoredMessage(
            id=row[0],
            timestamp=datetime.fromisoformat(row[1]),
            direction=MessageDirection(row[2]),
            type=row[3],
            sender_id=row[4],
            recipient_id=row[5],
            correlation_id=row[6],
            priority=row[7],
            ttl_seconds=row[8],
            payload_summary=row[9],
            full_payload=json.loads(row[10]) if row[10] else None,
            size_bytes=row[11],
            processing_status=MessageProcessingStatus(row[12]),
            created_at=datetime.fromisoformat(row[13]),
            updated_at=datetime.fromisoformat(row[14])
        )
    
    def search_messages(
        self,
        sender_id: Optional[str] = None,
        recipient_id: Optional[str] = None,
        message_type: Optional[str] = None,
        direction: Optional[MessageDirection] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[StoredMessage]:
        """Search messages with filters"""
        self._stats["queries_executed"] += 1
        
        results = []
        
        # Search in memory first
        with self._lock:
            messages = list(self._messages)
        
        for message in messages:
            if not self._message_matches_filter(
                message, sender_id, recipient_id, message_type, 
                direction, since, until, correlation_id, query
            ):
                continue
            results.append(message)
        
        # Search in SQLite if enabled and needed
        if self._sqlite_conn and (limit > len(results) or offset > 0):
            sqlite_results = self._search_sqlite(
                sender_id, recipient_id, message_type, direction,
                since, until, correlation_id, query, limit, offset
            )
            
            # Merge results, avoiding duplicates
            existing_ids = {msg.id for msg in results}
            for sqlite_msg in sqlite_results:
                if sqlite_msg.id not in existing_ids:
                    results.append(sqlite_msg)
        
        # Sort by timestamp (newest first)
        results.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply pagination
        if offset:
            results = results[offset:]
        if limit:
            results = results[:limit]
        
        return results
    
    def _message_matches_filter(
        self,
        message: StoredMessage,
        sender_id: Optional[str] = None,
        recipient_id: Optional[str] = None,
        message_type: Optional[str] = None,
        direction: Optional[MessageDirection] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        query: Optional[str] = None
    ) -> bool:
        """Check if message matches search filters"""
        if sender_id and message.sender_id != sender_id:
            return False
        
        if recipient_id and message.recipient_id != recipient_id:
            return False
        
        if message_type and message.type != message_type:
            return False
        
        if direction and message.direction != direction:
            return False
        
        if since and message.timestamp < since:
            return False
        
        if until and message.timestamp > until:
            return False
        
        if correlation_id and message.correlation_id != correlation_id:
            return False
        
        if query:
            # Simple text search in payload summary
            if query.lower() not in message.payload_summary.lower():
                return False
        
        return True
    
    def _search_sqlite(
        self,
        sender_id: Optional[str] = None,
        recipient_id: Optional[str] = None,
        message_type: Optional[str] = None,
        direction: Optional[MessageDirection] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[StoredMessage]:
        """Search messages in SQLite"""
        try:
            cursor = self._sqlite_conn.cursor()
            
            where_clauses = []
            params = []
            
            if sender_id:
                where_clauses.append("sender_id = ?")
                params.append(sender_id)
            
            if recipient_id:
                where_clauses.append("recipient_id = ?")
                params.append(recipient_id)
            
            if message_type:
                where_clauses.append("type = ?")
                params.append(message_type)
            
            if direction:
                where_clauses.append("direction = ?")
                params.append(direction.value)
            
            if since:
                where_clauses.append("timestamp >= ?")
                params.append(since.isoformat())
            
            if until:
                where_clauses.append("timestamp <= ?")
                params.append(until.isoformat())
            
            if correlation_id:
                where_clauses.append("correlation_id = ?")
                params.append(correlation_id)
            
            if query:
                where_clauses.append("payload_summary LIKE ?")
                params.append(f"%{query}%")
            
            where_clause = ""
            if where_clauses:
                where_clause = "WHERE " + " AND ".join(where_clauses)
            
            sql = f"""
                SELECT * FROM messages 
                {where_clause}
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [self._row_to_stored_message(row) for row in rows]
            
        except Exception as e:
            self.logger.error("Failed to search SQLite", error=str(e))
            return []
    
    def get_recent_messages(self, limit: int = 100) -> List[StoredMessage]:
        """Get most recent messages"""
        return self.search_messages(limit=limit)
    
    def export_messages(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        format: str = "json"
    ) -> Union[List[Dict[str, Any]], str]:
        """Export messages for a time range"""
        messages = self.search_messages(since=since, until=until, limit=10000)
        
        if format == "json":
            return [msg.to_dict() for msg in messages]
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                "id", "timestamp", "direction", "type", "sender_id", "recipient_id",
                "correlation_id", "priority", "size_bytes", "processing_status"
            ])
            
            # Data
            for msg in messages:
                writer.writerow([
                    msg.id, msg.timestamp.isoformat(), msg.direction.value,
                    msg.type, msg.sender_id, msg.recipient_id,
                    msg.correlation_id, msg.priority, msg.size_bytes,
                    msg.processing_status.value
                ])
            
            return output.getvalue()
        
        raise ValueError(f"Unsupported export format: {format}")
    
    def update_message_status(
        self, 
        message_id: str, 
        status: MessageProcessingStatus
    ) -> bool:
        """Update processing status of a message"""
        try:
            with self._lock:
                message = self._messages_by_id.get(message_id)
                if message:
                    message.processing_status = status
                    message.updated_at = datetime.now()
                    
                    # Update in SQLite if enabled
                    if self._sqlite_conn:
                        cursor = self._sqlite_conn.cursor()
                        cursor.execute("""
                            UPDATE messages 
                            SET processing_status = ?, updated_at = ?
                            WHERE id = ?
                        """, (status.value, message.updated_at.isoformat(), message_id))
                        self._sqlite_conn.commit()
                    
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error("Failed to update message status", error=str(e))
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get message store statistics"""
        with self._lock:
            memory_count = len(self._messages)
        
        sqlite_count = 0
        if self._sqlite_conn:
            try:
                cursor = self._sqlite_conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM messages")
                sqlite_count = cursor.fetchone()[0]
            except Exception:
                pass
        
        cutoff_time = datetime.now() - timedelta(hours=self.config.max_age_hours)
        
        return {
            **self._stats,
            "memory_messages": memory_count,
            "sqlite_messages": sqlite_count,
            "config": {
                "max_messages": self.config.max_messages,
                "max_age_hours": self.config.max_age_hours,
                "persistent_storage": self.config.persistent_storage,
                "allow_full_payload": self.config.allow_full_payload
            },
            "cutoff_time": cutoff_time.isoformat()
        }
    
    async def _cleanup_loop(self):
        """Background cleanup task"""
        while self._running:
            try:
                await self._cleanup_expired_messages()
                self._stats["last_cleanup"] = datetime.now().isoformat()
                await asyncio.sleep(3600)  # Cleanup every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Cleanup error", error=str(e))
                await asyncio.sleep(300)  # Retry in 5 minutes
    
    async def _cleanup_expired_messages(self):
        """Clean up expired messages"""
        cutoff_time = datetime.now() - timedelta(hours=self.config.max_age_hours)
        expired_count = 0
        
        with self._lock:
            # Clean memory
            expired_messages = []
            for message in self._messages:
                if message.timestamp < cutoff_time:
                    expired_messages.append(message)
            
            for message in expired_messages:
                try:
                    self._messages.remove(message)
                    del self._messages_by_id[message.id]
                    expired_count += 1
                except (ValueError, KeyError):
                    pass
        
        # Clean SQLite
        if self._sqlite_conn:
            try:
                cursor = self._sqlite_conn.cursor()
                cursor.execute(
                    "DELETE FROM messages WHERE timestamp < ?",
                    (cutoff_time.isoformat(),)
                )
                sqlite_expired = cursor.rowcount
                self._sqlite_conn.commit()
                expired_count += sqlite_expired
                
            except Exception as e:
                self.logger.error("Failed to cleanup SQLite", error=str(e))
        
        if expired_count > 0:
            self.logger.info("Cleaned up expired messages", count=expired_count)


# Global message store instance
_message_store: Optional[A2AMessageStore] = None


def get_message_store() -> Optional[A2AMessageStore]:
    """Get the global message store instance"""
    return _message_store


def init_message_store(config: Optional[MessageStoreConfig] = None) -> A2AMessageStore:
    """Initialize the global message store"""
    global _message_store
    if _message_store is None:
        _message_store = A2AMessageStore(config)
    return _message_store


async def start_message_store(config: Optional[MessageStoreConfig] = None):
    """Start the global message store"""
    store = init_message_store(config)
    await store.start()
    return store


async def stop_message_store():
    """Stop the global message store"""
    global _message_store
    if _message_store:
        await _message_store.stop()