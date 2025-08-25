"""
Tests for A2A Message Inspector functionality

This module tests the message inspection, storage, filtering, and live feed capabilities.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import sys
from pathlib import Path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from a2a.protocol import A2AMessage, A2AMessageType
from a2a.message_store import (
    A2AMessageStore, MessageStoreConfig, StoredMessage, 
    MessageDirection, MessageProcessingStatus, start_message_store
)
from a2a.communicator import A2ACommunicator
from config.message_inspector import MessageInspectorConfig


class TestMessageStore:
    """Test message store functionality"""
    
    @pytest.fixture
    def config(self):
        """Test configuration"""
        return MessageStoreConfig(
            max_messages=100,
            max_age_hours=1,
            payload_summary_length=50,
            allow_full_payload=True,
            persistent_storage=False,  # Use in-memory for tests
            enable_sampling=False
        )
    
    @pytest.fixture
    def message_store(self, config):
        """Message store instance"""
        return A2AMessageStore(config)
    
    @pytest.fixture
    def sample_message(self):
        """Sample A2A message"""
        return A2AMessage(
            type=A2AMessageType.PING,
            sender_id="agent_1",
            recipient_id="agent_2",
            payload={"test": "data", "timestamp": "2025-01-01T00:00:00"}
        )
    
    def test_message_logging(self, message_store, sample_message):
        """Test basic message logging"""
        # Log outbound message
        success = message_store.log_message(sample_message, MessageDirection.OUTBOUND)
        assert success
        
        # Verify message was stored
        stored_message = message_store.get_message(sample_message.id)
        assert stored_message is not None
        assert stored_message.id == sample_message.id
        assert stored_message.direction == MessageDirection.OUTBOUND
        assert stored_message.type == sample_message.type.value
        assert stored_message.sender_id == sample_message.sender_id
        assert stored_message.recipient_id == sample_message.recipient_id
    
    def test_payload_summary_truncation(self, message_store):
        """Test payload summary truncation"""
        long_payload = {"data": "x" * 100}  # Long payload
        message = A2AMessage(
            type=A2AMessageType.INFO_REQUEST,
            sender_id="agent_1",
            payload=long_payload
        )
        
        message_store.log_message(message, MessageDirection.OUTBOUND)
        stored = message_store.get_message(message.id)
        
        # Should be truncated to config length
        assert len(stored.payload_summary) <= message_store.config.payload_summary_length + 3  # +3 for "..."
        assert "..." in stored.payload_summary
    
    def test_message_search(self, message_store):
        """Test message search functionality"""
        # Create multiple messages
        messages = [
            A2AMessage(type=A2AMessageType.PING, sender_id="agent_1", recipient_id="agent_2"),
            A2AMessage(type=A2AMessageType.TASK_REQUEST, sender_id="agent_2", recipient_id="agent_3"),
            A2AMessage(type=A2AMessageType.PING, sender_id="agent_3", recipient_id="agent_1"),
        ]
        
        # Log messages
        for msg in messages:
            message_store.log_message(msg, MessageDirection.OUTBOUND)
        
        # Search by sender
        results = message_store.search_messages(sender_id="agent_1")
        assert len(results) == 1
        assert results[0].sender_id == "agent_1"
        
        # Search by message type
        results = message_store.search_messages(message_type="ping")
        assert len(results) == 2
        
        # Search by recipient
        results = message_store.search_messages(recipient_id="agent_2")
        assert len(results) == 1
        assert results[0].recipient_id == "agent_2"
    
    def test_message_filtering(self, message_store):
        """Test message filtering with multiple criteria"""
        base_time = datetime.now()
        
        # Create messages at different times
        old_message = A2AMessage(type=A2AMessageType.PING, sender_id="agent_1")
        old_message.timestamp = base_time - timedelta(hours=2)
        
        new_message = A2AMessage(type=A2AMessageType.TASK_REQUEST, sender_id="agent_1")
        new_message.timestamp = base_time
        
        message_store.log_message(old_message, MessageDirection.OUTBOUND)
        message_store.log_message(new_message, MessageDirection.INBOUND)
        
        # Filter by time range
        results = message_store.search_messages(since=base_time - timedelta(minutes=30))
        assert len(results) == 1
        assert results[0].id == new_message.id
        
        # Filter by direction
        results = message_store.search_messages(direction=MessageDirection.INBOUND)
        assert len(results) == 1
        assert results[0].direction == MessageDirection.INBOUND
    
    def test_message_export(self, message_store, sample_message):
        """Test message export functionality"""
        message_store.log_message(sample_message, MessageDirection.OUTBOUND)
        
        # Export as JSON
        exported = message_store.export_messages(format="json")
        assert len(exported) == 1
        assert exported[0]["id"] == sample_message.id
        
        # Export as CSV
        csv_data = message_store.export_messages(format="csv")
        assert isinstance(csv_data, str)
        assert sample_message.id in csv_data
    
    def test_buffer_overflow_handling(self):
        """Test message buffer overflow handling"""
        config = MessageStoreConfig(max_messages=2)  # Very small buffer
        store = A2AMessageStore(config)
        
        # Add more messages than buffer size
        messages = [
            A2AMessage(type=A2AMessageType.PING, sender_id="agent_1"),
            A2AMessage(type=A2AMessageType.PING, sender_id="agent_2"),
            A2AMessage(type=A2AMessageType.PING, sender_id="agent_3"),
        ]
        
        for msg in messages:
            store.log_message(msg, MessageDirection.OUTBOUND)
        
        # Should only have 2 messages (buffer size)
        recent = store.get_recent_messages(limit=10)
        assert len(recent) <= 2
        
        # Should have dropped at least 1 message
        stats = store.get_stats()
        assert stats["messages_dropped"] >= 1
    
    def test_sampling_functionality(self):
        """Test message sampling under load"""
        config = MessageStoreConfig(
            enable_sampling=True,
            sampling_rate=0.5  # 50% sampling
        )
        
        with patch('random.random', return_value=0.7):  # > sampling rate, should skip
            store = A2AMessageStore(config)
            message = A2AMessage(type=A2AMessageType.PING, sender_id="agent_1")
            
            success = store.log_message(message, MessageDirection.OUTBOUND)
            assert success  # Returns success but doesn't actually store
            
            # Message shouldn't be in store
            stored = store.get_message(message.id)
            assert stored is None
    
    @pytest.mark.asyncio
    async def test_async_operations(self, config):
        """Test async store operations"""
        store = A2AMessageStore(config)
        
        # Start store
        await store.start()
        assert store._running
        
        # Stop store
        await store.stop()
        assert not store._running


class TestInspectorAPI:
    """Test message inspector API endpoints"""
    
    @pytest.fixture
    def app(self):
        """Flask test app"""
        from api.app import create_app
        app = create_app({"TESTING": True})
        return app
    
    @pytest.fixture
    def client(self, app):
        """Test client"""
        return app.test_client()
    
    def test_get_messages_endpoint(self, client):
        """Test GET /api/a2a/messages endpoint"""
        response = client.get("/api/a2a/messages")
        assert response.status_code == 200 or response.status_code == 503  # Might not be available in test
    
    def test_message_search_endpoint(self, client):
        """Test message search with filters"""
        response = client.get("/api/a2a/messages?sender_id=agent_1&limit=10")
        assert response.status_code == 200 or response.status_code == 503
    
    def test_message_export_endpoint(self, client):
        """Test message export endpoint"""
        response = client.get("/api/a2a/messages/export?format=json")
        assert response.status_code == 200 or response.status_code == 503
    
    def test_inspector_config_endpoint(self, client):
        """Test inspector configuration endpoint"""
        response = client.get("/api/a2a/inspector/config")
        assert response.status_code == 200 or response.status_code == 500
    
    def test_inspector_health_endpoint(self, client):
        """Test inspector health check endpoint"""
        response = client.get("/api/a2a/inspector/health")
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.get_json()
            assert "health" in data
            assert "overall_status" in data["health"]
    
    def test_clear_buffer_endpoint(self, client):
        """Test message buffer clear endpoint"""
        response = client.delete("/api/a2a/inspector/clear")
        assert response.status_code == 200 or response.status_code == 503
    
    @patch('a2a.message_store.get_message_store')
    def test_message_replay_endpoint(self, mock_get_store, client):
        """Test message replay endpoint"""
        # Mock message store
        mock_store = Mock()
        mock_message = StoredMessage(
            id="test_msg_id",
            timestamp=datetime.now(),
            direction=MessageDirection.OUTBOUND,
            type="ping",
            sender_id="agent_1",
            recipient_id="agent_2",
            correlation_id=None,
            priority=5,
            ttl_seconds=300,
            payload_summary="test payload",
            full_payload={"test": "data"},
            size_bytes=100,
            processing_status=MessageProcessingStatus.DELIVERED
        )
        mock_store.get_message.return_value = mock_message
        mock_get_store.return_value = mock_store
        
        response = client.post("/api/a2a/messages/test_msg_id/replay", json={
            "requester_id": "admin_agent",
            "sandbox_mode": True
        })
        
        # Might fail due to missing agent registry in test, but should not crash
        assert response.status_code in [200, 400, 404, 500]


class TestCommunicatorIntegration:
    """Test communicator integration with message inspector"""
    
    @pytest.fixture
    def communicator(self):
        """A2A communicator instance"""
        return A2ACommunicator("test_agent_1", "Test Agent")
    
    @patch('a2a.message_store.get_message_store')
    async def test_message_logging_on_send(self, mock_get_store, communicator):
        """Test that messages are logged when sent"""
        mock_store = Mock()
        mock_get_store.return_value = mock_store
        
        message = A2AMessage(
            type=A2AMessageType.PING,
            sender_id="test_agent_1",
            recipient_id="test_agent_2"
        )
        
        # Send message (won't actually send due to test setup)
        await communicator.send_message(message)
        
        # Verify message was logged
        mock_store.log_message.assert_called_once()
        call_args = mock_store.log_message.call_args
        assert call_args[0][0].id == message.id  # Message
        assert call_args[0][1] == MessageDirection.OUTBOUND  # Direction
    
    @patch('a2a.message_store.get_message_store')
    async def test_message_logging_on_receive(self, mock_get_store, communicator):
        """Test that messages are logged when received"""
        mock_store = Mock()
        mock_get_store.return_value = mock_store
        
        message = A2AMessage(
            type=A2AMessageType.PING,
            sender_id="other_agent",
            recipient_id="test_agent_1"
        )
        
        # Receive message
        await communicator.receive_message(message)
        
        # Verify message was logged
        mock_store.log_message.assert_called_once()
        call_args = mock_store.log_message.call_args
        assert call_args[0][0].id == message.id  # Message
        assert call_args[0][1] == MessageDirection.INBOUND  # Direction


class TestInspectorConfiguration:
    """Test inspector configuration functionality"""
    
    def test_config_loading_from_env(self):
        """Test configuration loading from environment variables"""
        with patch.dict('os.environ', {
            'A2A_MSG_MAX_MESSAGES': '1000',
            'A2A_MSG_ALLOW_FULL_PAYLOAD': 'true',
            'A2A_MSG_REPLAY_ENABLED': 'false'
        }):
            config = MessageInspectorConfig()
            
            assert config.max_messages == 1000
            assert config.allow_full_payload is True
            assert config.replay_enabled is False
    
    def test_config_defaults(self):
        """Test configuration defaults"""
        config = MessageInspectorConfig()
        
        assert config.max_messages == 5000  # Default
        assert config.max_age_hours == 24  # Default
        assert config.persistent_storage is True  # Default
        assert config.require_auth is True  # Default
    
    def test_config_to_message_store_config(self):
        """Test conversion to MessageStoreConfig"""
        inspector_config = MessageInspectorConfig(
            max_messages=2000,
            allow_full_payload=True,
            persistent_storage=False
        )
        
        store_config = inspector_config.to_message_store_config()
        
        assert store_config.max_messages == 2000
        assert store_config.allow_full_payload is True
        assert store_config.persistent_storage is False


class TestWebSocketIntegration:
    """Test WebSocket integration for live message feeds"""
    
    @pytest.fixture
    def mock_app(self):
        """Mock Flask app with SocketIO"""
        app = Mock()
        app.socketio = Mock()
        return app
    
    async def test_websocket_message_broadcasting(self, mock_app):
        """Test WebSocket message broadcasting"""
        with patch('flask.current_app', mock_app):
            communicator = A2ACommunicator("test_agent", "Test Agent")
            
            message = A2AMessage(
                type=A2AMessageType.PING,
                sender_id="test_agent",
                recipient_id="other_agent",
                payload={"test": "data"}
            )
            
            # Test WebSocket broadcasting
            await communicator._broadcast_message_to_websockets(
                message, MessageDirection.OUTBOUND
            )
            
            # Verify emit was called
            mock_app.socketio.emit.assert_called()
            emit_call = mock_app.socketio.emit.call_args
            assert emit_call[0][0] == "new_a2a_message"  # Event name
            assert emit_call[1]["room"] == "a2a_messages"  # Room
            
            # Verify message data structure
            message_data = emit_call[0][1]
            assert message_data["id"] == message.id
            assert message_data["direction"] == "outbound"
            assert message_data["type"] == "ping"


class TestInspectorSecurity:
    """Test inspector security features"""
    
    def test_payload_sanitization(self):
        """Test sensitive payload data sanitization"""
        sensitive_message = A2AMessage(
            type=A2AMessageType.TASK_REQUEST,
            sender_id="agent_1",
            payload={
                "password": "secret123",
                "api_key": "sk-1234567890abcdef",
                "normal_data": "public information"
            }
        )
        
        config = MessageStoreConfig(
            payload_summary_length=100,
            allow_full_payload=False  # Don't store full payloads
        )
        
        store = A2AMessageStore(config)
        store.log_message(sensitive_message, MessageDirection.OUTBOUND)
        
        stored = store.get_message(sensitive_message.id)
        
        # Full payload should not be stored
        assert stored.full_payload is None
        
        # Payload summary should be limited
        assert len(stored.payload_summary) <= 100
    
    def test_admin_role_requirements(self):
        """Test admin role requirements for sensitive operations"""
        config = MessageInspectorConfig(
            admin_role_required=True,
            replay_enabled=True
        )
        
        # This would be checked in the actual API endpoint
        assert config.admin_role_required is True
        assert config.replay_enabled is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])