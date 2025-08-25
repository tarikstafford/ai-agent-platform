"""
Tests for A2A Message Tracing System
"""

import pytest
import asyncio
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path

# Import the tracing components
from src.a2a.traces import (
    TraceEvent, TraceEventType, MessageTrace, PayloadMasker,
    TraceStorage, A2ATracer, init_tracing
)
from src.a2a.protocol import A2AMessage, A2AMessageType


class TestTraceEvent:
    """Test TraceEvent data model"""
    
    def test_trace_event_creation(self):
        """Test basic trace event creation"""
        event = TraceEvent(
            trace_id="test-trace-123",
            message_id="msg-456",
            event_type=TraceEventType.SENT,
            sender_id="agent-1",
            recipient_id="agent-2",
            message_type="ping"
        )
        
        assert event.trace_id == "test-trace-123"
        assert event.message_id == "msg-456"
        assert event.event_type == TraceEventType.SENT
        assert event.sender_id == "agent-1"
        assert event.recipient_id == "agent-2"
        assert event.message_type == "ping"
        assert isinstance(event.timestamp, datetime)
    
    def test_trace_event_serialization(self):
        """Test trace event to/from dict conversion"""
        event = TraceEvent(
            trace_id="test-123",
            message_id="msg-456",
            event_type=TraceEventType.DELIVERED,
            metadata={"retry_count": 2}
        )
        
        # Test to_dict
        data = event.to_dict()
        assert data["trace_id"] == "test-123"
        assert data["event_type"] == "delivered"
        assert data["metadata"] == {"retry_count": 2}
        assert "timestamp" in data
        
        # Test from_dict
        restored = TraceEvent.from_dict(data)
        assert restored.trace_id == event.trace_id
        assert restored.event_type == event.event_type
        assert restored.metadata == event.metadata


class TestMessageTrace:
    """Test MessageTrace data model"""
    
    def test_empty_trace(self):
        """Test trace with no events"""
        trace = MessageTrace(trace_id="empty-trace")
        
        assert trace.trace_id == "empty-trace"
        assert trace.duration_ms is None
        assert trace.hop_count == 0
        assert trace.final_status == "unknown"
        assert trace.retry_count == 0
    
    def test_trace_with_events(self):
        """Test trace metrics calculation"""
        base_time = datetime.now()
        
        events = [
            TraceEvent(
                trace_id="trace-123",
                message_id="msg-1",
                event_type=TraceEventType.SENT,
                timestamp=base_time,
                sender_id="agent-1"
            ),
            TraceEvent(
                trace_id="trace-123", 
                message_id="msg-1",
                event_type=TraceEventType.RETRY,
                timestamp=base_time + timedelta(milliseconds=100),
                sender_id="agent-1"
            ),
            TraceEvent(
                trace_id="trace-123",
                message_id="msg-1", 
                event_type=TraceEventType.DELIVERED,
                timestamp=base_time + timedelta(milliseconds=250),
                recipient_id="agent-2"
            )
        ]
        
        trace = MessageTrace(trace_id="trace-123", events=events)
        
        assert trace.duration_ms == 250
        assert trace.hop_count == 2  # agent-1 and agent-2
        assert trace.final_status == "delivered"
        assert trace.retry_count == 1
    
    def test_trace_serialization(self):
        """Test trace to_dict conversion with summary"""
        events = [
            TraceEvent(
                trace_id="trace-123",
                message_id="msg-1",
                event_type=TraceEventType.FAILED,
                error_message="Connection timeout"
            )
        ]
        
        trace = MessageTrace(trace_id="trace-123", events=events)
        data = trace.to_dict()
        
        assert data["trace_id"] == "trace-123"
        assert len(data["events"]) == 1
        assert data["summary"]["final_status"] == "failed"
        assert data["summary"]["event_count"] == 1


class TestPayloadMasker:
    """Test payload masking functionality"""
    
    def test_mask_sensitive_keys(self):
        """Test masking of sensitive data"""
        masker = PayloadMasker()
        
        payload = {
            "api_key": "secret-123",
            "username": "john",
            "password": "sensitive-data",
            "normal_field": "visible-data"
        }
        
        masked = masker.mask_payload(payload)
        
        assert "secret-123" not in masked
        assert "sensitive-data" not in masked
        assert "[MASKED]" in masked
        assert "john" in masked
        assert "visible-data" in masked
    
    def test_payload_truncation(self):
        """Test payload truncation for large payloads"""
        masker = PayloadMasker(max_payload_size=50)
        
        large_payload = {"data": "x" * 100}
        masked = masker.mask_payload(large_payload)
        
        assert len(masked) <= 70  # 50 + truncation marker
        assert "[TRUNCATED]" in masked


class TestTraceStorage:
    """Test SQLite-based trace storage"""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            storage = TraceStorage(tmp.name)
            yield storage
            # Cleanup
            Path(tmp.name).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_event(self, temp_storage):
        """Test storing and retrieving trace events"""
        event = TraceEvent(
            trace_id="test-trace",
            message_id="msg-123",
            event_type=TraceEventType.SENT,
            sender_id="agent-1",
            recipient_id="agent-2",
            payload_preview='{"test": "data"}',
            metadata={"retry": False}
        )
        
        # Store event
        await temp_storage.store_event(event)
        
        # Retrieve trace
        trace = await temp_storage.get_trace("test-trace")
        
        assert trace is not None
        assert trace.trace_id == "test-trace"
        assert len(trace.events) == 1
        
        retrieved_event = trace.events[0]
        assert retrieved_event.message_id == "msg-123"
        assert retrieved_event.event_type == TraceEventType.SENT
        assert retrieved_event.sender_id == "agent-1"
        assert retrieved_event.payload_preview == '{"test": "data"}'
        assert retrieved_event.metadata == {"retry": False}
    
    @pytest.mark.asyncio
    async def test_list_traces(self, temp_storage):
        """Test listing traces with filtering"""
        # Create multiple trace events
        events = [
            TraceEvent(
                trace_id=f"trace-{i}",
                message_id=f"msg-{i}",
                event_type=TraceEventType.SENT,
                sender_id="agent-1",
                message_type="ping" if i % 2 == 0 else "task_request"
            )
            for i in range(5)
        ]
        
        for event in events:
            await temp_storage.store_event(event)
        
        # Test basic listing
        traces = await temp_storage.list_traces(limit=10)
        assert len(traces) == 5
        
        # Test filtering by message type
        ping_traces = await temp_storage.list_traces(
            limit=10,
            agent_id="agent-1"
        )
        assert len(ping_traces) >= 5
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_traces(self, temp_storage):
        """Test cleanup of expired traces"""
        # Create old event
        old_time = datetime.now() - timedelta(days=10)
        old_event = TraceEvent(
            trace_id="old-trace",
            message_id="old-msg",
            event_type=TraceEventType.SENT,
            timestamp=old_time
        )
        
        # Create new event
        new_event = TraceEvent(
            trace_id="new-trace", 
            message_id="new-msg",
            event_type=TraceEventType.SENT
        )
        
        await temp_storage.store_event(old_event)
        await temp_storage.store_event(new_event)
        
        # Cleanup with 7 day retention
        deleted_count = await temp_storage.cleanup_expired_traces(retention_days=7)
        
        assert deleted_count == 1
        
        # Verify new trace still exists
        new_trace = await temp_storage.get_trace("new-trace")
        assert new_trace is not None
        
        # Verify old trace was deleted
        old_trace = await temp_storage.get_trace("old-trace")
        assert old_trace is None


class TestA2ATracer:
    """Test the main A2A tracer functionality"""
    
    @pytest.fixture
    def temp_tracer(self):
        """Create temporary tracer for testing"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tracer = A2ATracer(
                storage=TraceStorage(tmp.name),
                enabled=True
            )
            yield tracer
            # Cleanup
            Path(tmp.name).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_trace_message_lifecycle(self, temp_tracer):
        """Test tracing a complete message lifecycle"""
        # Create test message
        message = A2AMessage(
            type=A2AMessageType.PING,
            sender_id="agent-1",
            recipient_id="agent-2",
            payload={"test": "data"},
            correlation_id="corr-123"
        )
        
        # Trace message lifecycle
        await temp_tracer.trace_message_sent(message)
        await temp_tracer.trace_message_received(message, "agent-2")
        await temp_tracer.trace_message_delivered(message)
        
        # Retrieve and verify trace
        trace = await temp_tracer.get_trace("corr-123")
        
        assert trace is not None
        assert len(trace.events) == 3
        
        event_types = [e.event_type for e in trace.events]
        assert TraceEventType.SENT in event_types
        assert TraceEventType.RECEIVED in event_types
        assert TraceEventType.DELIVERED in event_types
    
    @pytest.mark.asyncio
    async def test_trace_message_failure(self, temp_tracer):
        """Test tracing message failures and retries"""
        message = A2AMessage(
            type=A2AMessageType.TASK_REQUEST,
            sender_id="agent-1",
            recipient_id="agent-2",
            correlation_id="fail-123"
        )
        
        # Trace failure scenario
        await temp_tracer.trace_message_sent(message)
        await temp_tracer.trace_message_retry(message, 1, "Connection timeout")
        await temp_tracer.trace_message_failed(message, "Agent unreachable", 404)
        
        trace = await temp_tracer.get_trace("fail-123")
        
        assert trace is not None
        assert trace.final_status == "failed"
        assert trace.retry_count == 1
        
        # Check error information
        failed_event = next(
            e for e in trace.events if e.event_type == TraceEventType.FAILED
        )
        assert failed_event.error_message == "Agent unreachable"
        assert failed_event.status_code == 404
    
    @pytest.mark.asyncio
    async def test_disabled_tracer(self, temp_tracer):
        """Test that disabled tracer doesn't store events"""
        temp_tracer.enabled = False
        
        message = A2AMessage(
            type=A2AMessageType.PING,
            sender_id="agent-1",
            correlation_id="disabled-123"
        )
        
        await temp_tracer.trace_message_sent(message)
        
        # Should not find any trace
        trace = await temp_tracer.get_trace("disabled-123")
        assert trace is None


class TestTracingIntegration:
    """Test tracing system integration"""
    
    def test_init_tracing(self):
        """Test tracer initialization"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tracer = init_tracing(
                enabled=True,
                db_path=tmp.name,
                retention_days=14
            )
            
            assert tracer is not None
            assert tracer.enabled is True
            assert tracer.retention_days == 14
            
            # Cleanup
            Path(tmp.name).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_tracer_stats(self):
        """Test tracer statistics collection"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tracer = A2ATracer(
                storage=TraceStorage(tmp.name),
                enabled=True
            )
            
            # Add some test events
            message = A2AMessage(
                type=A2AMessageType.PING,
                sender_id="test-agent",
                correlation_id="stats-test"
            )
            await tracer.trace_message_sent(message)
            await tracer.trace_message_delivered(message)
            
            # Get stats
            stats = await tracer.get_stats()
            
            assert stats["enabled"] is True
            assert "storage" in stats
            assert stats["storage"]["total_events"] >= 2
            
            # Cleanup
            Path(tmp.name).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__])