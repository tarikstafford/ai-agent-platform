from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
from typing import Dict, Any
import structlog

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