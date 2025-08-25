from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
from typing import Dict, Any
import structlog

from ..a2a.message_store import get_message_store

logger = structlog.get_logger()


def setup_websocket_handlers(app: Flask) -> SocketIO:
    """Setup WebSocket handlers for real-time updates"""
    
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        logger.info("Client connected")
        emit('connected', {'status': 'connected'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        logger.info("Client disconnected")
    
    @socketio.on('join_dashboard')
    def handle_join_dashboard():
        """Join dashboard room for updates"""
        join_room('dashboard')
        logger.info("Client joined dashboard room")
        
        # Send current dashboard data
        try:
            manager = app.agent_manager
            dashboard_data = manager.get_dashboard_data()
            emit('dashboard_update', dashboard_data)
        except Exception as e:
            emit('error', {'message': str(e)})
    
    @socketio.on('leave_dashboard')
    def handle_leave_dashboard():
        """Leave dashboard room"""
        leave_room('dashboard')
        logger.info("Client left dashboard room")
    
    @socketio.on('get_agent_status')
    def handle_get_agent_status(data):
        """Get status of specific agent"""
        try:
            agent_id = data.get('agent_id')
            if not agent_id:
                emit('error', {'message': 'Missing agent_id'})
                return
            
            manager = app.agent_manager
            agent_info = manager.get_agent_info(agent_id)
            
            if agent_info:
                emit('agent_status', agent_info)
            else:
                emit('error', {'message': 'Agent not found'})
                
        except Exception as e:
            emit('error', {'message': str(e)})
    
    @socketio.on('subscribe_agent')
    def handle_subscribe_agent(data):
        """Subscribe to updates for a specific agent"""
        try:
            agent_id = data.get('agent_id')
            if not agent_id:
                emit('error', {'message': 'Missing agent_id'})
                return
            
            room = f'agent_{agent_id}'
            join_room(room)
            logger.info("Client subscribed to agent updates", agent_id=agent_id)
            
            # Send current agent status
            manager = app.agent_manager
            agent_info = manager.get_agent_info(agent_id)
            if agent_info:
                emit('agent_update', agent_info)
            
        except Exception as e:
            emit('error', {'message': str(e)})
    
    @socketio.on('unsubscribe_agent')
    def handle_unsubscribe_agent(data):
        """Unsubscribe from agent updates"""
        try:
            agent_id = data.get('agent_id')
            if not agent_id:
                emit('error', {'message': 'Missing agent_id'})
                return
            
            room = f'agent_{agent_id}'
            leave_room(room)
            logger.info("Client unsubscribed from agent updates", agent_id=agent_id)
            
        except Exception as e:
            emit('error', {'message': str(e)})
    
    # A2A Message Inspector WebSocket Handlers
    
    @socketio.on('join_a2a_messages')
    def handle_join_a2a_messages():
        """Join A2A message stream room"""
        join_room('a2a_messages')
        logger.info("Client joined A2A message stream")
        
        # Send recent messages as initial data
        try:
            message_store = get_message_store()
            if message_store:
                recent_messages = message_store.get_recent_messages(limit=20)
                emit('a2a_messages_initial', {
                    'messages': [msg.to_dict() for msg in recent_messages]
                })
        except Exception as e:
            emit('error', {'message': f'Failed to get recent messages: {str(e)}'})
    
    @socketio.on('leave_a2a_messages')
    def handle_leave_a2a_messages():
        """Leave A2A message stream room"""
        leave_room('a2a_messages')
        logger.info("Client left A2A message stream")
    
    @socketio.on('subscribe_message_filters')
    def handle_subscribe_message_filters(data):
        """Subscribe to filtered message stream"""
        try:
            # Join filtered room with specific filters
            filters = data.get('filters', {})
            filter_hash = hash(json.dumps(filters, sort_keys=True))
            room = f'a2a_filtered_{filter_hash}'
            
            join_room(room)
            logger.info("Client subscribed to filtered A2A messages", filters=filters)
            
            # Send filtered recent messages
            message_store = get_message_store()
            if message_store:
                filtered_messages = message_store.search_messages(
                    sender_id=filters.get('sender_id'),
                    recipient_id=filters.get('recipient_id'),
                    message_type=filters.get('type'),
                    limit=20
                )
                emit('a2a_filtered_initial', {
                    'messages': [msg.to_dict() for msg in filtered_messages],
                    'filters': filters
                })
                
        except Exception as e:
            emit('error', {'message': f'Failed to subscribe to filtered messages: {str(e)}'})
    
    @socketio.on('get_message_stats')
    def handle_get_message_stats():
        """Get current message store statistics"""
        try:
            message_store = get_message_store()
            if message_store:
                stats = message_store.get_stats()
                emit('message_stats', stats)
            else:
                emit('error', {'message': 'Message store not available'})
        except Exception as e:
            emit('error', {'message': f'Failed to get message stats: {str(e)}'})
    
    # Store socketio instance on app for broadcasting
    app.socketio = socketio
    
    return socketio


def broadcast_agent_update(app: Flask, agent_id: str, agent_data: Dict[str, Any]):
    """Broadcast agent update to subscribed clients"""
    if hasattr(app, 'socketio'):
        app.socketio.emit('agent_update', agent_data, room=f'agent_{agent_id}')


def broadcast_dashboard_update(app: Flask, dashboard_data: Dict[str, Any]):
    """Broadcast dashboard update to dashboard clients"""
    if hasattr(app, 'socketio'):
        app.socketio.emit('dashboard_update', dashboard_data, room='dashboard')


def broadcast_a2a_message(app: Flask, message_data: Dict[str, Any]):
    """Broadcast new A2A message to subscribed clients"""
    if hasattr(app, 'socketio'):
        # Broadcast to general A2A message stream
        app.socketio.emit('new_a2a_message', message_data, room='a2a_messages')
        
        # Also broadcast to specific filtered rooms if applicable
        # This would require implementing filter matching logic


def broadcast_message_stats_update(app: Flask, stats_data: Dict[str, Any]):
    """Broadcast message store statistics update"""
    if hasattr(app, 'socketio'):
        app.socketio.emit('message_stats_update', stats_data, room='a2a_messages')