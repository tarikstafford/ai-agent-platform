"""
A2A Message Trace System

This module provides message tracing capabilities for the A2A communication layer,
enabling debugging and monitoring of inter-agent message flows.
"""

import asyncio
import json
import re
import sqlite3
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field, asdict
from pathlib import Path
import os

import structlog
from .protocol import A2AMessage, A2AMessageType

logger = structlog.get_logger()


class TraceEventType(str, Enum):
    """Types of trace events"""
    SENT = "sent"
    RECEIVED = "received"
    ROUTED = "routed"
    RETRY = "retry"
    DELIVERED = "delivered"
    FAILED = "failed"
    ACKNOWLEDGED = "acknowledged"
    TIMEOUT = "timeout"


@dataclass
class TraceEvent:
    """Individual trace event record"""
    trace_id: str  # correlation_id or message_id
    message_id: str
    event_type: TraceEventType
    timestamp: datetime = field(default_factory=datetime.now)
    sender_id: Optional[str] = None
    recipient_id: Optional[str] = None
    agent_path: List[str] = field(default_factory=list)  # Message routing path
    message_type: Optional[str] = None
    status_code: Optional[int] = None
    payload_preview: Optional[str] = None  # Masked and truncated payload
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['event_type'] = self.event_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TraceEvent':
        """Create from dictionary"""
        # Convert timestamp string back to datetime
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        # Convert event_type string back to enum
        if isinstance(data.get('event_type'), str):
            data['event_type'] = TraceEventType(data['event_type'])
        
        return cls(**data)


@dataclass
class MessageTrace:
    """Complete trace for a correlation ID or message"""
    trace_id: str
    events: List[TraceEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def duration_ms(self) -> Optional[int]:
        """Calculate total duration in milliseconds"""
        if len(self.events) < 2:
            return None
        
        first_event = min(self.events, key=lambda e: e.timestamp)
        last_event = max(self.events, key=lambda e: e.timestamp)
        
        duration = (last_event.timestamp - first_event.timestamp).total_seconds() * 1000
        return int(duration)
    
    @property
    def hop_count(self) -> int:
        """Count unique agents in the message path"""
        agents = set()
        for event in self.events:
            if event.sender_id:
                agents.add(event.sender_id)
            if event.recipient_id:
                agents.add(event.recipient_id)
            agents.update(event.agent_path)
        return len(agents)
    
    @property
    def final_status(self) -> str:
        """Get final status of the trace"""
        if not self.events:
            return "unknown"
        
        # Sort events by timestamp
        sorted_events = sorted(self.events, key=lambda e: e.timestamp)
        last_event = sorted_events[-1]
        
        # Map event types to status
        status_mapping = {
            TraceEventType.DELIVERED: "delivered",
            TraceEventType.ACKNOWLEDGED: "acknowledged", 
            TraceEventType.FAILED: "failed",
            TraceEventType.TIMEOUT: "timeout"
        }
        
        return status_mapping.get(last_event.event_type, "in_progress")
    
    @property
    def retry_count(self) -> int:
        """Count retry events"""
        return sum(1 for event in self.events if event.event_type == TraceEventType.RETRY)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "trace_id": self.trace_id,
            "events": [event.to_dict() for event in self.events],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "summary": {
                "duration_ms": self.duration_ms,
                "hop_count": self.hop_count,
                "final_status": self.final_status,
                "retry_count": self.retry_count,
                "event_count": len(self.events)
            }
        }


class PayloadMasker:
    """Handles masking of sensitive data in payloads"""
    
    def __init__(self, mask_keys: Optional[List[str]] = None, max_payload_size: int = 500):
        # Default sensitive keys to mask
        self.mask_keys = mask_keys or [
            'api_key', 'password', 'token', 'secret', 'key', 'auth',
            'authorization', 'credential', 'private', 'confidential'
        ]
        self.max_payload_size = max_payload_size
        
        # Compile regex patterns for sensitive keys
        self.mask_patterns = [
            re.compile(rf'"{key}":\s*"[^"]*"', re.IGNORECASE) 
            for key in self.mask_keys
        ]
    
    def mask_payload(self, payload: Any) -> str:
        """Mask sensitive data and truncate payload"""
        try:
            # Convert to JSON string
            if isinstance(payload, dict):
                payload_str = json.dumps(payload, default=str)
            elif isinstance(payload, str):
                payload_str = payload
            else:
                payload_str = str(payload)
            
            # Apply masking
            for pattern in self.mask_patterns:
                # Replace sensitive values with [MASKED]
                payload_str = pattern.sub(
                    lambda m: m.group(0).replace(m.group(0).split('"')[3], '[MASKED]'),
                    payload_str
                )
            
            # Truncate if too long
            if len(payload_str) > self.max_payload_size:
                payload_str = payload_str[:self.max_payload_size] + "...[TRUNCATED]"
            
            return payload_str
            
        except Exception as e:
            logger.warning("Error masking payload", error=str(e))
            return "[PAYLOAD_MASK_ERROR]"


class TraceStorage:
    """SQLite-based storage for trace events"""
    
    def __init__(self, db_path: str = "data/a2a_traces.db"):
        self.db_path = db_path
        self.logger = logger.bind(component="trace_storage")
        
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS trace_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trace_id TEXT NOT NULL,
                        message_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        sender_id TEXT,
                        recipient_id TEXT,
                        agent_path TEXT,  -- JSON array
                        message_type TEXT,
                        status_code INTEGER,
                        payload_preview TEXT,
                        metadata TEXT,  -- JSON object
                        error_message TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indices for better query performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_trace_id ON trace_events(trace_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_message_id ON trace_events(message_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON trace_events(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sender_id ON trace_events(sender_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_recipient_id ON trace_events(recipient_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON trace_events(event_type)")
                
                conn.commit()
                
        except Exception as e:
            self.logger.error("Database initialization error", error=str(e))
            raise
    
    async def store_event(self, event: TraceEvent):
        """Store a single trace event"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO trace_events (
                        trace_id, message_id, event_type, timestamp,
                        sender_id, recipient_id, agent_path, message_type,
                        status_code, payload_preview, metadata, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.trace_id,
                    event.message_id,
                    event.event_type.value,
                    event.timestamp.isoformat(),
                    event.sender_id,
                    event.recipient_id,
                    json.dumps(event.agent_path),
                    event.message_type,
                    event.status_code,
                    event.payload_preview,
                    json.dumps(event.metadata),
                    event.error_message
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error("Error storing trace event", 
                            trace_id=event.trace_id,
                            message_id=event.message_id,
                            error=str(e))
            raise
    
    async def get_trace(self, trace_id: str) -> Optional[MessageTrace]:
        """Get complete trace for a trace ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM trace_events 
                    WHERE trace_id = ?
                    ORDER BY timestamp ASC
                """, (trace_id,))
                
                rows = cursor.fetchall()
                if not rows:
                    return None
                
                # Convert rows to TraceEvent objects
                events = []
                for row in rows:
                    event = TraceEvent(
                        trace_id=row['trace_id'],
                        message_id=row['message_id'],
                        event_type=TraceEventType(row['event_type']),
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        sender_id=row['sender_id'],
                        recipient_id=row['recipient_id'],
                        agent_path=json.loads(row['agent_path']) if row['agent_path'] else [],
                        message_type=row['message_type'],
                        status_code=row['status_code'],
                        payload_preview=row['payload_preview'],
                        metadata=json.loads(row['metadata']) if row['metadata'] else {},
                        error_message=row['error_message']
                    )
                    events.append(event)
                
                # Create trace with first and last timestamps
                first_timestamp = min(events, key=lambda e: e.timestamp).timestamp
                last_timestamp = max(events, key=lambda e: e.timestamp).timestamp
                
                return MessageTrace(
                    trace_id=trace_id,
                    events=events,
                    created_at=first_timestamp,
                    updated_at=last_timestamp
                )
                
        except Exception as e:
            self.logger.error("Error retrieving trace", trace_id=trace_id, error=str(e))
            return None
    
    async def list_traces(
        self,
        limit: int = 100,
        offset: int = 0,
        agent_id: Optional[str] = None,
        message_type: Optional[str] = None,
        time_range_hours: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List recent traces with optional filtering"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Build query conditions
                conditions = []
                params = []
                
                if agent_id:
                    conditions.append("(sender_id = ? OR recipient_id = ?)")
                    params.extend([agent_id, agent_id])
                
                if message_type:
                    conditions.append("message_type = ?")
                    params.append(message_type)
                
                if time_range_hours:
                    cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
                    conditions.append("timestamp >= ?")
                    params.append(cutoff_time.isoformat())
                
                where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
                
                # Get trace summaries
                query = f"""
                    SELECT 
                        trace_id,
                        MIN(timestamp) as first_event,
                        MAX(timestamp) as last_event,
                        COUNT(*) as event_count,
                        GROUP_CONCAT(DISTINCT sender_id) as senders,
                        GROUP_CONCAT(DISTINCT recipient_id) as recipients,
                        GROUP_CONCAT(DISTINCT message_type) as message_types
                    FROM trace_events
                    {where_clause}
                    GROUP BY trace_id
                    ORDER BY MAX(timestamp) DESC
                    LIMIT ? OFFSET ?
                """
                
                params.extend([limit, offset])
                cursor = conn.execute(query, params)
                
                traces = []
                for row in cursor.fetchall():
                    traces.append({
                        "trace_id": row['trace_id'],
                        "first_event": row['first_event'],
                        "last_event": row['last_event'],
                        "event_count": row['event_count'],
                        "senders": row['senders'].split(',') if row['senders'] else [],
                        "recipients": row['recipients'].split(',') if row['recipients'] else [],
                        "message_types": row['message_types'].split(',') if row['message_types'] else []
                    })
                
                return traces
                
        except Exception as e:
            self.logger.error("Error listing traces", error=str(e))
            return []
    
    async def cleanup_expired_traces(self, retention_days: int = 7):
        """Clean up traces older than retention period"""
        try:
            cutoff_time = datetime.now() - timedelta(days=retention_days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM trace_events 
                    WHERE timestamp < ?
                """, (cutoff_time.isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    self.logger.info("Cleaned up expired traces", 
                                   deleted_count=deleted_count,
                                   retention_days=retention_days)
                
                return deleted_count
                
        except Exception as e:
            self.logger.error("Error cleaning up traces", error=str(e))
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get trace storage statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total events
                cursor = conn.execute("SELECT COUNT(*) FROM trace_events")
                total_events = cursor.fetchone()[0]
                
                # Unique traces
                cursor = conn.execute("SELECT COUNT(DISTINCT trace_id) FROM trace_events")
                unique_traces = cursor.fetchone()[0]
                
                # Events by type
                cursor = conn.execute("""
                    SELECT event_type, COUNT(*) as count 
                    FROM trace_events 
                    GROUP BY event_type
                """)
                events_by_type = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Recent activity (last 24 hours)
                cutoff_time = datetime.now() - timedelta(hours=24)
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM trace_events 
                    WHERE timestamp >= ?
                """, (cutoff_time.isoformat(),))
                recent_events = cursor.fetchone()[0]
                
                # Database size
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                return {
                    "total_events": total_events,
                    "unique_traces": unique_traces,
                    "recent_events_24h": recent_events,
                    "events_by_type": events_by_type,
                    "database_size_bytes": db_size,
                    "database_path": self.db_path
                }
                
        except Exception as e:
            self.logger.error("Error getting trace stats", error=str(e))
            return {}


class A2ATracer:
    """Main tracing system for A2A communications"""
    
    def __init__(
        self,
        storage: Optional[TraceStorage] = None,
        masker: Optional[PayloadMasker] = None,
        enabled: bool = True
    ):
        self.enabled = enabled
        self.storage = storage or TraceStorage()
        self.masker = masker or PayloadMasker()
        self.logger = logger.bind(component="a2a_tracer")
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.running = False
        
        # Configuration
        self.retention_days = int(os.getenv('A2A_TRACE_RETENTION_DAYS', '7'))
        self.cleanup_interval_hours = int(os.getenv('A2A_TRACE_CLEANUP_HOURS', '24'))
    
    async def start(self):
        """Start the tracer background tasks"""
        if not self.enabled or self.running:
            return
        
        self.running = True
        
        # Start cleanup task
        self.background_tasks.append(
            asyncio.create_task(self._cleanup_loop())
        )
        
        self.logger.info("A2A tracer started", 
                        retention_days=self.retention_days,
                        cleanup_interval_hours=self.cleanup_interval_hours)
    
    async def stop(self):
        """Stop the tracer"""
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        self.background_tasks.clear()
        
        self.logger.info("A2A tracer stopped")
    
    async def trace_message_sent(
        self, 
        message: A2AMessage, 
        recipient_path: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Trace when a message is sent"""
        if not self.enabled:
            return
        
        trace_id = message.correlation_id or message.id
        
        event = TraceEvent(
            trace_id=trace_id,
            message_id=message.id,
            event_type=TraceEventType.SENT,
            sender_id=message.sender_id,
            recipient_id=message.recipient_id,
            agent_path=recipient_path or [],
            message_type=message.type.value if hasattr(message.type, 'value') else str(message.type),
            status_code=200,  # Successful send
            payload_preview=self.masker.mask_payload(message.payload),
            metadata=metadata or {}
        )
        
        await self.storage.store_event(event)
        
        self.logger.debug("Message sent traced", 
                         trace_id=trace_id,
                         message_id=message.id,
                         recipient=message.recipient_id)
    
    async def trace_message_received(
        self,
        message: A2AMessage,
        receiver_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Trace when a message is received"""
        if not self.enabled:
            return
        
        trace_id = message.correlation_id or message.id
        
        event = TraceEvent(
            trace_id=trace_id,
            message_id=message.id,
            event_type=TraceEventType.RECEIVED,
            sender_id=message.sender_id,
            recipient_id=receiver_id,
            message_type=message.type.value if hasattr(message.type, 'value') else str(message.type),
            status_code=200,
            payload_preview=self.masker.mask_payload(message.payload),
            metadata=metadata or {}
        )
        
        await self.storage.store_event(event)
        
        self.logger.debug("Message received traced",
                         trace_id=trace_id,
                         message_id=message.id,
                         sender=message.sender_id)
    
    async def trace_message_routed(
        self,
        message: A2AMessage,
        from_agent: str,
        to_agent: str,
        routing_info: Optional[Dict[str, Any]] = None
    ):
        """Trace when a message is routed through an intermediate agent"""
        if not self.enabled:
            return
        
        trace_id = message.correlation_id or message.id
        
        event = TraceEvent(
            trace_id=trace_id,
            message_id=message.id,
            event_type=TraceEventType.ROUTED,
            sender_id=from_agent,
            recipient_id=to_agent,
            agent_path=[from_agent, to_agent],
            message_type=message.type.value if hasattr(message.type, 'value') else str(message.type),
            status_code=200,
            metadata=routing_info or {}
        )
        
        await self.storage.store_event(event)
        
        self.logger.debug("Message routed traced",
                         trace_id=trace_id,
                         message_id=message.id,
                         from_agent=from_agent,
                         to_agent=to_agent)
    
    async def trace_message_retry(
        self,
        message: A2AMessage,
        attempt_number: int,
        error_info: Optional[str] = None
    ):
        """Trace when a message delivery is retried"""
        if not self.enabled:
            return
        
        trace_id = message.correlation_id or message.id
        
        event = TraceEvent(
            trace_id=trace_id,
            message_id=message.id,
            event_type=TraceEventType.RETRY,
            sender_id=message.sender_id,
            recipient_id=message.recipient_id,
            message_type=message.type.value if hasattr(message.type, 'value') else str(message.type),
            status_code=408,  # Request Timeout
            metadata={"attempt_number": attempt_number},
            error_message=error_info
        )
        
        await self.storage.store_event(event)
        
        self.logger.debug("Message retry traced",
                         trace_id=trace_id,
                         message_id=message.id,
                         attempt=attempt_number)
    
    async def trace_message_delivered(
        self,
        message: A2AMessage,
        delivery_info: Optional[Dict[str, Any]] = None
    ):
        """Trace when a message is successfully delivered"""
        if not self.enabled:
            return
        
        trace_id = message.correlation_id or message.id
        
        event = TraceEvent(
            trace_id=trace_id,
            message_id=message.id,
            event_type=TraceEventType.DELIVERED,
            sender_id=message.sender_id,
            recipient_id=message.recipient_id,
            message_type=message.type.value if hasattr(message.type, 'value') else str(message.type),
            status_code=200,
            metadata=delivery_info or {}
        )
        
        await self.storage.store_event(event)
        
        self.logger.debug("Message delivered traced",
                         trace_id=trace_id,
                         message_id=message.id)
    
    async def trace_message_failed(
        self,
        message: A2AMessage,
        error_message: str,
        status_code: int = 500
    ):
        """Trace when a message delivery fails"""
        if not self.enabled:
            return
        
        trace_id = message.correlation_id or message.id
        
        event = TraceEvent(
            trace_id=trace_id,
            message_id=message.id,
            event_type=TraceEventType.FAILED,
            sender_id=message.sender_id,
            recipient_id=message.recipient_id,
            message_type=message.type.value if hasattr(message.type, 'value') else str(message.type),
            status_code=status_code,
            error_message=error_message
        )
        
        await self.storage.store_event(event)
        
        self.logger.debug("Message failed traced",
                         trace_id=trace_id,
                         message_id=message.id,
                         error=error_message)
    
    async def trace_message_acknowledged(
        self,
        message: A2AMessage,
        ack_info: Optional[Dict[str, Any]] = None
    ):
        """Trace when a message is acknowledged"""
        if not self.enabled:
            return
        
        trace_id = message.correlation_id or message.id
        
        event = TraceEvent(
            trace_id=trace_id,
            message_id=message.id,
            event_type=TraceEventType.ACKNOWLEDGED,
            sender_id=message.recipient_id,  # Ack comes from recipient
            recipient_id=message.sender_id,  # Back to original sender
            message_type=message.type.value if hasattr(message.type, 'value') else str(message.type),
            status_code=200,
            metadata=ack_info or {}
        )
        
        await self.storage.store_event(event)
        
        self.logger.debug("Message acknowledged traced",
                         trace_id=trace_id,
                         message_id=message.id)
    
    async def get_trace(self, trace_id: str) -> Optional[MessageTrace]:
        """Get complete trace for a correlation ID"""
        return await self.storage.get_trace(trace_id)
    
    async def list_traces(
        self,
        limit: int = 100,
        offset: int = 0,
        agent_id: Optional[str] = None,
        message_type: Optional[str] = None,
        time_range_hours: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List recent traces with filtering"""
        return await self.storage.list_traces(
            limit=limit,
            offset=offset,
            agent_id=agent_id,
            message_type=message_type,
            time_range_hours=time_range_hours
        )
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get tracing statistics"""
        storage_stats = await self.storage.get_stats()
        
        return {
            "enabled": self.enabled,
            "retention_days": self.retention_days,
            "cleanup_interval_hours": self.cleanup_interval_hours,
            "storage": storage_stats
        }
    
    async def _cleanup_loop(self):
        """Background cleanup task"""
        while self.running:
            try:
                await asyncio.sleep(self.cleanup_interval_hours * 3600)
                
                if self.running:  # Check again after sleep
                    deleted_count = await self.storage.cleanup_expired_traces(self.retention_days)
                    
                    if deleted_count > 0:
                        self.logger.info("Trace cleanup completed",
                                       deleted_count=deleted_count,
                                       retention_days=self.retention_days)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in cleanup loop", error=str(e))
                await asyncio.sleep(3600)  # Wait 1 hour before retrying


# Global tracer instance
_global_tracer: Optional[A2ATracer] = None


def get_tracer() -> Optional[A2ATracer]:
    """Get the global tracer instance"""
    return _global_tracer


def set_tracer(tracer: A2ATracer):
    """Set the global tracer instance"""
    global _global_tracer
    _global_tracer = tracer


def init_tracing(
    enabled: bool = True,
    db_path: str = "data/a2a_traces.db",
    retention_days: int = 7
) -> A2ATracer:
    """Initialize the global tracing system"""
    storage = TraceStorage(db_path)
    masker = PayloadMasker()
    tracer = A2ATracer(storage=storage, masker=masker, enabled=enabled)
    tracer.retention_days = retention_days
    
    set_tracer(tracer)
    return tracer