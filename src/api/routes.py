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


@agents_bp.route('/create-from-prompt', methods=['POST'])
def create_agent_from_prompt():
    """Create an agent based on a natural language prompt"""
    try:
        data = request.get_json()
        
        if 'prompt' not in data:
            return jsonify({"error": "Missing 'prompt' field", "success": False}), 400
        
        prompt = data['prompt']
        name = data.get('name')
        agent_type = data.get('type')
        model = data.get('model', 'gpt-3.5-turbo')
        temperature = data.get('temperature', 0.7)
        
        # Analyze prompt to determine agent configuration
        agent_config = analyze_prompt_and_create_config(
            prompt=prompt,
            suggested_name=name,
            suggested_type=agent_type,
            model=model,
            temperature=temperature
        )
        
        manager = current_app.agent_manager
        agent_id = run_async(manager.create_agent(
            agent_type=agent_config['type'],
            config=agent_config['config'],
            tools=agent_config.get('tools', []),
            name=agent_config['name'],
            description=agent_config.get('description', ''),
            tags=agent_config.get('tags', ['prompt-created']),
            auto_start=data.get('auto_start', True)
        ))
        
        return jsonify({
            "agent_id": agent_id,
            "success": True,
            "message": "Agent created successfully from prompt",
            "generated_config": {
                "name": agent_config['name'],
                "type": agent_config['type'],
                "description": agent_config.get('description', ''),
                "tools": agent_config.get('tools', [])
            }
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


def analyze_prompt_and_create_config(prompt: str, suggested_name: str = None, suggested_type: str = None, model: str = 'gpt-3.5-turbo', temperature: float = 0.7) -> Dict[str, Any]:
    """Analyze a natural language prompt and create agent configuration"""
    import re
    
    prompt_lower = prompt.lower()
    
    # Determine agent type based on prompt keywords
    if suggested_type:
        agent_type = suggested_type
    elif any(word in prompt_lower for word in ['calculate', 'math', 'computation', 'search', 'web', 'tool', 'api']):
        agent_type = 'reactive'
    elif any(word in prompt_lower for word in ['plan', 'strategy', 'step', 'workflow', 'process', 'organize']):
        agent_type = 'planner' 
    else:
        agent_type = 'conversational'
    
    # Determine tools needed
    tools = []
    if 'calcul' in prompt_lower or 'math' in prompt_lower:
        tools.append('calculator')
    if 'search' in prompt_lower or 'web' in prompt_lower or 'internet' in prompt_lower:
        tools.append('web_search')
    
    # Generate agent name if not provided
    if not suggested_name:
        # Extract potential name from prompt
        if 'support' in prompt_lower:
            name = 'Support Agent'
        elif 'sales' in prompt_lower:
            name = 'Sales Agent'
        elif 'research' in prompt_lower:
            name = 'Research Agent'
        elif 'assistant' in prompt_lower:
            name = 'Assistant Agent'
        elif 'customer' in prompt_lower:
            name = 'Customer Agent'
        elif 'help' in prompt_lower:
            name = 'Helper Agent'
        else:
            name = f'{agent_type.title()} Agent'
    else:
        name = suggested_name
    
    # Create description from prompt (first 200 chars)
    description = prompt[:200] + '...' if len(prompt) > 200 else prompt
    
    # Determine capabilities for A2A
    a2a_capabilities = []
    if 'support' in prompt_lower:
        a2a_capabilities.extend(['customer_support', 'issue_resolution'])
    if 'sales' in prompt_lower:
        a2a_capabilities.extend(['sales_assistance', 'product_information'])
    if 'research' in prompt_lower:
        a2a_capabilities.extend(['research', 'data_analysis'])
    if 'calcul' in prompt_lower or 'math' in prompt_lower:
        a2a_capabilities.append('mathematical_computation')
    if 'search' in prompt_lower:
        a2a_capabilities.append('web_search')
    
    # Create enhanced system prompt
    system_prompt = f"""You are an AI agent created to: {prompt}

Key responsibilities:
- Follow the user's original requirements closely
- Be helpful, accurate, and professional
- Use available tools when appropriate
- Communicate clearly and concisely

Original creation prompt: {prompt}"""

    config = {
        'name': name,
        'type': agent_type,
        'config': {
            'name': name,
            'description': description,
            'model': model,
            'temperature': temperature,
            'max_tokens': 2000,
            'max_iterations': 10,
            'timeout_seconds': 300,
            'tools': tools,
            'memory_enabled': True,
            'verbose': False,
            'a2a_enabled': True,
            'a2a_capabilities': a2a_capabilities,
            'system_prompt': system_prompt
        },
        'tools': tools,
        'description': description,
        'tags': ['prompt-created', agent_type],
    }
    
    return config


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
@dashboard_bp.route('/')
@dashboard_bp.route('/ui')
@dashboard_bp.route('/ui/')
@dashboard_bp.route('/ui/<path:path>')
def dashboard_ui(path=''):
    """Serve dashboard UI"""
    from flask import send_from_directory
    import os
    
    # Serve the new unified dashboard HTML
    dashboard_dir = os.path.join(os.path.dirname(__file__), '..', 'dashboard', 'static')
    return send_from_directory(dashboard_dir, 'main-dashboard.html')


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