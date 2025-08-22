from flask import Blueprint, request, jsonify, current_app
import asyncio
from typing import Dict, Any
import json

agents_bp = Blueprint('agents', __name__)
dashboard_bp = Blueprint('dashboard', __name__)


def run_async(coro):
    """Helper to run async functions in Flask"""
    loop = current_app.async_loop
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)


# Agent Management Routes
@agents_bp.route('/', methods=['GET'])
def list_agents():
    """List all agents"""
    try:
        manager = current_app.agent_manager
        agents = manager.list_agents()
        return jsonify({"agents": agents, "success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


@agents_bp.route('/', methods=['POST'])
def create_agent():
    """Create a new agent"""
    try:
        data = request.get_json()
        
        required_fields = ['type', 'config']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}", "success": False}), 400
        
        manager = current_app.agent_manager
        agent_id = run_async(manager.create_agent(
            agent_type=data['type'],
            config=data['config'],
            tools=data.get('tools', []),
            name=data.get('name'),
            description=data.get('description', ''),
            tags=data.get('tags', []),
            auto_start=data.get('auto_start', True)
        ))
        
        return jsonify({
            "agent_id": agent_id,
            "success": True,
            "message": "Agent created successfully"
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


@agents_bp.route('/<agent_id>', methods=['GET'])
def get_agent(agent_id: str):
    """Get agent information"""
    try:
        manager = current_app.agent_manager
        agent_info = manager.get_agent_info(agent_id)
        
        if not agent_info:
            return jsonify({"error": "Agent not found", "success": False}), 404
        
        return jsonify({"agent": agent_info, "success": True})
        
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


@agents_bp.route('/<agent_id>', methods=['DELETE'])
def delete_agent(agent_id: str):
    """Delete an agent"""
    try:
        manager = current_app.agent_manager
        success = run_async(manager.remove_agent(agent_id))
        
        if not success:
            return jsonify({"error": "Agent not found", "success": False}), 404
        
        return jsonify({"success": True, "message": "Agent deleted successfully"})
        
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


@agents_bp.route('/<agent_id>/start', methods=['POST'])
def start_agent(agent_id: str):
    """Start an agent"""
    try:
        manager = current_app.agent_manager
        success = run_async(manager.start_agent(agent_id))
        
        if not success:
            return jsonify({"error": "Failed to start agent", "success": False}), 400
        
        return jsonify({"success": True, "message": "Agent started successfully"})
        
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


@agents_bp.route('/<agent_id>/stop', methods=['POST'])
def stop_agent(agent_id: str):
    """Stop an agent"""
    try:
        manager = current_app.agent_manager
        success = run_async(manager.stop_agent(agent_id))
        
        if not success:
            return jsonify({"error": "Failed to stop agent", "success": False}), 400
        
        return jsonify({"success": True, "message": "Agent stopped successfully"})
        
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


@agents_bp.route('/<agent_id>/chat', methods=['POST'])
def chat_with_agent(agent_id: str):
    """Send a message to an agent"""
    try:
        data = request.get_json()
        
        if 'message' not in data:
            return jsonify({"error": "Missing 'message' field", "success": False}), 400
        
        manager = current_app.agent_manager
        response = run_async(manager.chat_with_agent(agent_id, data['message']))
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


@agents_bp.route('/<agent_id>/execute', methods=['POST'])
def execute_agent_task(agent_id: str):
    """Execute a structured task on an agent"""
    try:
        data = request.get_json()
        
        if 'task' not in data:
            return jsonify({"error": "Missing 'task' field", "success": False}), 400
        
        manager = current_app.agent_manager
        response = run_async(manager.execute_agent_task(agent_id, data['task']))
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


# Dashboard Routes
@dashboard_bp.route('/', methods=['GET'])
def get_dashboard_data():
    """Get dashboard overview data"""
    try:
        manager = current_app.agent_manager
        dashboard_data = manager.get_dashboard_data()
        return jsonify(dashboard_data)
        
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


@dashboard_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get detailed statistics"""
    try:
        manager = current_app.agent_manager
        stats = manager.registry.get_registry_stats()
        return jsonify({"stats": stats, "success": True})
        
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


@dashboard_bp.route('/agents/status/<status>', methods=['GET'])
def get_agents_by_status(status: str):
    """Get agents by status"""
    try:
        manager = current_app.agent_manager
        agents = manager.get_agents_by_status(status)
        return jsonify({"agents": agents, "success": True})
        
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


@dashboard_bp.route('/agents/tag/<tag>', methods=['GET'])
def get_agents_by_tag(tag: str):
    """Get agents by tag"""
    try:
        manager = current_app.agent_manager
        agents = manager.get_agents_by_tag(tag)
        return jsonify({"agents": agents, "success": True})
        
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


# Template routes for serving the dashboard
@dashboard_bp.route('/ui')
@dashboard_bp.route('/ui/')
@dashboard_bp.route('/ui/<path:path>')
def dashboard_ui(path=''):
    """Serve dashboard UI"""
    from flask import send_from_directory
    import os
    
    # Serve the static dashboard HTML
    dashboard_dir = os.path.join(os.path.dirname(__file__), '..', 'dashboard', 'static')
    return send_from_directory(dashboard_dir, 'dashboard.html')


@dashboard_bp.route('/builder')
@dashboard_bp.route('/builder/')
def workflow_builder_ui():
    """Serve visual workflow builder UI"""
    from flask import send_from_directory
    import os
    
    # Serve the workflow builder HTML
    dashboard_dir = os.path.join(os.path.dirname(__file__), '..', 'dashboard', 'static')
    return send_from_directory(dashboard_dir, 'workflow-builder.html')


@dashboard_bp.route('/a2a')
@dashboard_bp.route('/a2a/')
def a2a_dashboard_ui():
    """Serve A2A communication dashboard UI"""
    from flask import send_from_directory
    import os
    
    # Serve the A2A dashboard HTML
    dashboard_dir = os.path.join(os.path.dirname(__file__), '..', 'dashboard', 'static')
    return send_from_directory(dashboard_dir, 'a2a-dashboard.html')