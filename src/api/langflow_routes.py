from flask import Blueprint, request, jsonify, current_app
import asyncio
from typing import Dict, Any
import json

langflow_bp = Blueprint('langflow', __name__)


def run_async(coro):
    """Helper to run async functions in Flask"""
    loop = current_app.async_loop
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)


# Check if Langflow is available
try:
    from langflow_integration import LangflowServer, WorkflowBuilder, WorkflowManager
    LANGFLOW_AVAILABLE = True
except ImportError:
    LANGFLOW_AVAILABLE = False


def get_workflow_builder():
    """Get or create workflow builder instance"""
    if not hasattr(current_app, 'workflow_builder'):
        if not LANGFLOW_AVAILABLE:
            return None
        current_app.workflow_builder = WorkflowBuilder()
    return current_app.workflow_builder


@langflow_bp.route('/status', methods=['GET'])
def langflow_status():
    """Check Langflow integration status"""
    if not LANGFLOW_AVAILABLE:
        return jsonify({
            "available": False,
            "error": "Langflow not installed",
            "success": False
        })
    
    try:
        builder = get_workflow_builder()
        if not builder:
            return jsonify({
                "available": False,
                "error": "Workflow builder not initialized",
                "success": False
            })
        
        server_running = builder.langflow_server.is_running()
        
        return jsonify({
            "available": True,
            "server_running": server_running,
            "server_url": builder.langflow_server.base_url,
            "builder_url": builder.get_builder_url(),
            "success": True
        })
        
    except Exception as e:
        return jsonify({
            "available": False,
            "error": str(e),
            "success": False
        }), 500


@langflow_bp.route('/initialize', methods=['POST'])
def initialize_langflow():
    """Initialize Langflow server and builder"""
    if not LANGFLOW_AVAILABLE:
        return jsonify({
            "error": "Langflow not available",
            "success": False
        }), 400
    
    try:
        builder = get_workflow_builder()
        if not builder:
            return jsonify({
                "error": "Failed to create workflow builder",
                "success": False
            }), 500
        
        success = run_async(builder.initialize())
        
        if success:
            return jsonify({
                "success": True,
                "server_url": builder.langflow_server.base_url,
                "builder_url": builder.get_builder_url(),
                "message": "Langflow initialized successfully"
            })
        else:
            return jsonify({
                "error": "Failed to initialize Langflow",
                "success": False
            }), 500
            
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


@langflow_bp.route('/workflows', methods=['GET'])
def list_workflows():
    """List available workflows"""
    if not LANGFLOW_AVAILABLE:
        return jsonify({
            "error": "Langflow not available",
            "success": False
        }), 400
    
    try:
        builder = get_workflow_builder()
        if not builder:
            return jsonify({
                "error": "Workflow builder not initialized",
                "success": False
            }), 500
        
        # Get workflows from Langflow server
        flows = builder.langflow_server.get_flows()
        
        # Get local workflows
        local_workflows = builder.workflow_manager.list_workflows()
        
        return jsonify({
            "server_flows": flows.get("flows", []),
            "local_workflows": local_workflows,
            "success": True
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


@langflow_bp.route('/workflows', methods=['POST'])
def create_workflow():
    """Create a new workflow"""
    if not LANGFLOW_AVAILABLE:
        return jsonify({
            "error": "Langflow not available",
            "success": False
        }), 400
    
    try:
        data = request.get_json()
        
        if 'name' not in data:
            return jsonify({
                "error": "Missing 'name' field",
                "success": False
            }), 400
        
        builder = get_workflow_builder()
        if not builder:
            return jsonify({
                "error": "Workflow builder not initialized",
                "success": False
            }), 500
        
        name = data['name']
        description = data.get('description', '')
        template = data.get('template')
        
        if template:
            # Create from template
            flow_id = builder.create_from_template(template, name)
        else:
            # Create empty workflow
            flow_id = builder.create_workflow(name, description)
        
        if flow_id:
            return jsonify({
                "flow_id": flow_id,
                "name": name,
                "editor_config": builder.get_workflow_editor_config(flow_id),
                "success": True,
                "message": "Workflow created successfully"
            }), 201
        else:
            return jsonify({
                "error": "Failed to create workflow",
                "success": False
            }), 500
            
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


@langflow_bp.route('/workflows/<flow_id>', methods=['GET'])
def get_workflow(flow_id: str):
    """Get workflow details"""
    if not LANGFLOW_AVAILABLE:
        return jsonify({
            "error": "Langflow not available",
            "success": False
        }), 400
    
    try:
        builder = get_workflow_builder()
        if not builder:
            return jsonify({
                "error": "Workflow builder not initialized",
                "success": False
            }), 500
        
        flow_data = builder.langflow_server.get_flow(flow_id)
        
        if flow_data:
            return jsonify({
                "workflow": flow_data,
                "editor_config": builder.get_workflow_editor_config(flow_id),
                "success": True
            })
        else:
            return jsonify({
                "error": "Workflow not found",
                "success": False
            }), 404
            
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


@langflow_bp.route('/workflows/<flow_id>/test', methods=['POST'])
def test_workflow(flow_id: str):
    """Test a workflow with sample inputs"""
    if not LANGFLOW_AVAILABLE:
        return jsonify({
            "error": "Langflow not available",
            "success": False
        }), 400
    
    try:
        data = request.get_json()
        test_inputs = data.get('inputs', {})
        
        builder = get_workflow_builder()
        if not builder:
            return jsonify({
                "error": "Workflow builder not initialized",
                "success": False
            }), 500
        
        result = run_async(builder.test_workflow(flow_id, test_inputs))
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


@langflow_bp.route('/workflows/<flow_id>/export', methods=['GET'])
def export_workflow(flow_id: str):
    """Export workflow as JSON"""
    if not LANGFLOW_AVAILABLE:
        return jsonify({
            "error": "Langflow not available",
            "success": False
        }), 400
    
    try:
        builder = get_workflow_builder()
        if not builder:
            return jsonify({
                "error": "Workflow builder not initialized",
                "success": False
            }), 500
        
        exported_data = builder.langflow_server.export_flow(flow_id)
        
        if exported_data:
            return jsonify({
                "workflow_data": exported_data,
                "success": True
            })
        else:
            return jsonify({
                "error": "Failed to export workflow",
                "success": False
            }), 500
            
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


@langflow_bp.route('/templates', methods=['GET'])
def get_templates():
    """Get available workflow templates"""
    if not LANGFLOW_AVAILABLE:
        return jsonify({
            "error": "Langflow not available",
            "success": False
        }), 400
    
    try:
        builder = get_workflow_builder()
        if not builder:
            return jsonify({
                "error": "Workflow builder not initialized",
                "success": False
            }), 500
        
        templates = builder.get_workflow_templates()
        
        return jsonify({
            "templates": templates,
            "success": True
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


@langflow_bp.route('/components', methods=['GET'])
def get_components():
    """Get available workflow components"""
    if not LANGFLOW_AVAILABLE:
        return jsonify({
            "error": "Langflow not available",
            "success": False
        }), 400
    
    try:
        builder = get_workflow_builder()
        if not builder:
            return jsonify({
                "error": "Workflow builder not initialized",
                "success": False
            }), 500
        
        components = builder.get_available_components()
        
        return jsonify({
            "components": components,
            "success": True
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


# Agent creation route specifically for Langflow agents
@langflow_bp.route('/agents', methods=['POST'])
def create_langflow_agent():
    """Create a new Langflow-based agent"""
    if not LANGFLOW_AVAILABLE:
        return jsonify({
            "error": "Langflow not available",
            "success": False
        }), 400
    
    try:
        data = request.get_json()
        
        required_fields = ['name', 'flow_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "error": f"Missing required field: {field}",
                    "success": False
                }), 400
        
        # Create agent configuration
        agent_config = {
            "name": data['name'],
            "description": data.get('description', 'Langflow visual workflow agent'),
            "model": "langflow-workflow",
            "temperature": 0.7,
            "max_tokens": 2000,
            "flow_id": data['flow_id'],
            "flow_data": data.get('flow_data')
        }
        
        manager = current_app.agent_manager
        agent_id = run_async(manager.create_agent(
            agent_type="langflow",
            config=agent_config,
            name=data['name'],
            description=data.get('description', ''),
            tags=data.get('tags', ['langflow', 'visual-workflow']),
            auto_start=data.get('auto_start', True)
        ))
        
        return jsonify({
            "agent_id": agent_id,
            "flow_id": data['flow_id'],
            "success": True,
            "message": "Langflow agent created successfully"
        }), 201
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500