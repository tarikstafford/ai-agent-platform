"""
A2A Protocol REST API Routes

This module provides REST API endpoints for Agent-to-Agent communication,
task delegation, and collaboration management.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

from flask import Blueprint, request, jsonify
import structlog

# Import A2A components
from ..a2a.protocol import (
    A2AMessage, A2AMessageType, A2ARequest, A2AResponse,
    TaskDelegation, CollaborationRequest, AgentProfile
)
from ..a2a.tasks import TaskManager, CollaborationManager

logger = structlog.get_logger()

a2a_bp = Blueprint('a2a', __name__, url_prefix='/api/a2a')


def get_agent_registry():
    """Get the agent registry instance"""
    from flask import current_app
    return getattr(current_app, 'agent_registry', None)


def get_agent_manager():
    """Get the agent manager instance"""
    from flask import current_app
    return getattr(current_app, 'agent_manager', None)


@a2a_bp.route('/status', methods=['GET'])
def get_a2a_status():
    """Get A2A system status"""
    try:
        registry = get_agent_registry()
        if not registry:
            return jsonify({"error": "Agent registry not available"}), 500
        
        # Get agents with A2A capabilities
        a2a_enabled_agents = []
        for agent_reg in registry.list_agents():
            if hasattr(agent_reg.config, 'a2a_enabled') and agent_reg.config.a2a_enabled:
                agent = registry.running_agents.get(agent_reg.id)
                if agent and hasattr(agent, 'a2a_communicator'):
                    a2a_stats = agent.a2a_communicator.get_stats() if agent.a2a_communicator else {}
                    a2a_enabled_agents.append({
                        "agent_id": agent_reg.id,
                        "name": agent_reg.name,
                        "status": agent_reg.status.value,
                        "a2a_stats": a2a_stats
                    })
        
        return jsonify({
            "a2a_enabled": True,
            "total_agents": len(registry.list_agents()),
            "a2a_enabled_agents": len(a2a_enabled_agents),
            "agents": a2a_enabled_agents,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error("Error getting A2A status", error=str(e))
        return jsonify({"error": str(e)}), 500


@a2a_bp.route('/agents/discover', methods=['POST'])
async def discover_agents():
    """Discover agents with specific capabilities"""
    try:
        data = request.get_json() or {}
        required_capabilities = data.get('required_capabilities', [])
        timeout = data.get('timeout', 30)
        requester_id = data.get('requester_id')
        
        if not requester_id:
            return jsonify({"error": "requester_id is required"}), 400
        
        registry = get_agent_registry()
        if not registry:
            return jsonify({"error": "Agent registry not available"}), 500
        
        # Get the requesting agent
        requester_agent = registry.running_agents.get(requester_id)
        if not requester_agent or not hasattr(requester_agent, 'a2a_discovery'):
            return jsonify({"error": "Agent not found or A2A not enabled"}), 404
        
        # Perform discovery
        discovered_agents = await requester_agent.discover_agents(required_capabilities)
        
        return jsonify({
            "success": True,
            "discovered_agents": discovered_agents,
            "count": len(discovered_agents),
            "required_capabilities": required_capabilities,
            "timeout": timeout
        })
    
    except Exception as e:
        logger.error("Error in agent discovery", error=str(e))
        return jsonify({"error": str(e)}), 500


@a2a_bp.route('/messages/send', methods=['POST'])
async def send_message():
    """Send A2A message between agents"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request data is required"}), 400
        
        sender_id = data.get('sender_id')
        recipient_id = data.get('recipient_id')
        message_type = data.get('message_type')
        payload = data.get('payload', {})
        
        if not all([sender_id, message_type]):
            return jsonify({"error": "sender_id and message_type are required"}), 400
        
        registry = get_agent_registry()
        if not registry:
            return jsonify({"error": "Agent registry not available"}), 500
        
        # Get the sender agent
        sender_agent = registry.running_agents.get(sender_id)
        if not sender_agent or not hasattr(sender_agent, 'a2a_communicator'):
            return jsonify({"error": "Sender agent not found or A2A not enabled"}), 404
        
        # Send message
        message_id = await sender_agent.send_message_to_agent(
            recipient_id, message_type, payload
        )
        
        return jsonify({
            "success": True,
            "message_id": message_id,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "message_type": message_type
        })
    
    except Exception as e:
        logger.error("Error sending A2A message", error=str(e))
        return jsonify({"error": str(e)}), 500


@a2a_bp.route('/tasks/delegate', methods=['POST'])
async def delegate_task():
    """Delegate a task to another agent"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request data is required"}), 400
        
        requester_id = data.get('requester_id')
        task_type = data.get('task_type')
        task_data = data.get('task_data', {})
        description = data.get('description')
        required_capabilities = data.get('required_capabilities', [])
        deadline_str = data.get('deadline')
        
        if not all([requester_id, task_type]):
            return jsonify({"error": "requester_id and task_type are required"}), 400
        
        registry = get_agent_registry()
        if not registry:
            return jsonify({"error": "Agent registry not available"}), 500
        
        # Get the requester agent
        requester_agent = registry.running_agents.get(requester_id)
        if not requester_agent:
            return jsonify({"error": "Requester agent not found"}), 404
        
        # Parse deadline if provided
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str)
            except ValueError:
                return jsonify({"error": "Invalid deadline format"}), 400
        
        # Delegate task
        success = await requester_agent.delegate_task_to_agent(
            agent_id=data.get('target_agent_id', ''),  # Will be auto-selected if not provided
            task_type=task_type,
            task_data=task_data
        )
        
        return jsonify({
            "success": success,
            "task_type": task_type,
            "description": description,
            "required_capabilities": required_capabilities,
            "requester_id": requester_id
        })
    
    except Exception as e:
        logger.error("Error delegating task", error=str(e))
        return jsonify({"error": str(e)}), 500


@a2a_bp.route('/tasks/status/<task_id>', methods=['GET'])
def get_task_status(task_id: str):
    """Get status of a delegated task"""
    try:
        registry = get_agent_registry()
        if not registry:
            return jsonify({"error": "Agent registry not available"}), 500
        
        # Search for task in all agents' task managers
        for agent_reg in registry.list_agents():
            agent = registry.running_agents.get(agent_reg.id)
            if agent and hasattr(agent, 'task_manager'):
                task_status = agent.task_manager.get_task_status(task_id)
                if task_status:
                    return jsonify({
                        "success": True,
                        "task_id": task_id,
                        "status": task_status.status.value,
                        "description": task_status.description,
                        "requester_id": task_status.requester_id,
                        "assigned_agent_id": task_status.assigned_agent_id,
                        "created_at": task_status.created_at.isoformat(),
                        "started_at": task_status.started_at.isoformat() if task_status.started_at else None,
                        "completed_at": task_status.completed_at.isoformat() if task_status.completed_at else None,
                        "progress": task_status.progress,
                        "error_message": task_status.error_message
                    })
        
        return jsonify({"error": "Task not found"}), 404
    
    except Exception as e:
        logger.error("Error getting task status", error=str(e))
        return jsonify({"error": str(e)}), 500


@a2a_bp.route('/tasks/active', methods=['GET'])
def get_active_tasks():
    """Get all active tasks across agents"""
    try:
        agent_id = request.args.get('agent_id')
        registry = get_agent_registry()
        if not registry:
            return jsonify({"error": "Agent registry not available"}), 500
        
        all_tasks = []
        
        # Get tasks from specific agent or all agents
        agents_to_check = [agent_id] if agent_id else [reg.id for reg in registry.list_agents()]
        
        for agent_reg_id in agents_to_check:
            agent = registry.running_agents.get(agent_reg_id)
            if agent and hasattr(agent, 'task_manager'):
                active_tasks = agent.task_manager.get_active_tasks()
                
                for task in active_tasks:
                    all_tasks.append({
                        "task_id": task.task_id,
                        "task_type": task.task_type,
                        "status": task.status.value,
                        "description": task.description,
                        "requester_id": task.requester_id,
                        "assigned_agent_id": task.assigned_agent_id,
                        "created_at": task.created_at.isoformat(),
                        "started_at": task.started_at.isoformat() if task.started_at else None,
                        "progress": task.progress,
                        "agent_id": agent_reg_id
                    })
        
        return jsonify({
            "success": True,
            "active_tasks": all_tasks,
            "count": len(all_tasks)
        })
    
    except Exception as e:
        logger.error("Error getting active tasks", error=str(e))
        return jsonify({"error": str(e)}), 500


@a2a_bp.route('/collaborations/initiate', methods=['POST'])
async def initiate_collaboration():
    """Initiate a new collaboration between agents"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request data is required"}), 400
        
        coordinator_id = data.get('coordinator_id')
        title = data.get('title')
        description = data.get('description')
        participant_ids = data.get('participant_ids', [])
        required_capabilities = data.get('required_capabilities', [])
        
        if not all([coordinator_id, title, description]):
            return jsonify({"error": "coordinator_id, title, and description are required"}), 400
        
        registry = get_agent_registry()
        if not registry:
            return jsonify({"error": "Agent registry not available"}), 500
        
        # Get the coordinator agent
        coordinator_agent = registry.running_agents.get(coordinator_id)
        if not coordinator_agent:
            return jsonify({"error": "Coordinator agent not found"}), 404
        
        # Initiate collaboration
        collaboration_id = await coordinator_agent.collaborate_with_agents(
            agent_ids=participant_ids,
            collaboration_title=title,
            collaboration_description=description
        )
        
        return jsonify({
            "success": True,
            "collaboration_id": collaboration_id,
            "coordinator_id": coordinator_id,
            "title": title,
            "participant_ids": participant_ids,
            "required_capabilities": required_capabilities
        })
    
    except Exception as e:
        logger.error("Error initiating collaboration", error=str(e))
        return jsonify({"error": str(e)}), 500


@a2a_bp.route('/collaborations/active', methods=['GET'])
def get_active_collaborations():
    """Get all active collaborations"""
    try:
        agent_id = request.args.get('agent_id')
        registry = get_agent_registry()
        if not registry:
            return jsonify({"error": "Agent registry not available"}), 500
        
        all_collaborations = []
        
        # Get collaborations from specific agent or all agents
        agents_to_check = [agent_id] if agent_id else [reg.id for reg in registry.list_agents()]
        
        for agent_reg_id in agents_to_check:
            agent = registry.running_agents.get(agent_reg_id)
            if agent and hasattr(agent, 'collaboration_manager'):
                active_collabs = agent.collaboration_manager.get_active_collaborations()
                
                for collab in active_collabs:
                    all_collaborations.append({
                        "collaboration_id": collab.collaboration_id,
                        "title": collab.title,
                        "description": collab.description,
                        "coordinator_id": collab.coordinator_id,
                        "participants": collab.participants,
                        "status": collab.status.value,
                        "created_at": collab.created_at.isoformat(),
                        "started_at": collab.started_at.isoformat() if collab.started_at else None,
                        "agent_id": agent_reg_id
                    })
        
        return jsonify({
            "success": True,
            "active_collaborations": all_collaborations,
            "count": len(all_collaborations)
        })
    
    except Exception as e:
        logger.error("Error getting active collaborations", error=str(e))
        return jsonify({"error": str(e)}), 500


@a2a_bp.route('/collaborations/<collaboration_id>/join', methods=['POST'])
async def join_collaboration(collaboration_id: str):
    """Join an existing collaboration"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        
        if not agent_id:
            return jsonify({"error": "agent_id is required"}), 400
        
        registry = get_agent_registry()
        if not registry:
            return jsonify({"error": "Agent registry not available"}), 500
        
        # Get the agent
        agent = registry.running_agents.get(agent_id)
        if not agent or not hasattr(agent, 'collaboration_manager'):
            return jsonify({"error": "Agent not found or collaboration not enabled"}), 404
        
        # Join collaboration
        success = await agent.collaboration_manager.join_collaboration(collaboration_id)
        
        return jsonify({
            "success": success,
            "collaboration_id": collaboration_id,
            "agent_id": agent_id
        })
    
    except Exception as e:
        logger.error("Error joining collaboration", error=str(e))
        return jsonify({"error": str(e)}), 500


@a2a_bp.route('/collaborations/<collaboration_id>/leave', methods=['POST'])
async def leave_collaboration(collaboration_id: str):
    """Leave a collaboration"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        
        if not agent_id:
            return jsonify({"error": "agent_id is required"}), 400
        
        registry = get_agent_registry()
        if not registry:
            return jsonify({"error": "Agent registry not available"}), 500
        
        # Get the agent
        agent = registry.running_agents.get(agent_id)
        if not agent or not hasattr(agent, 'collaboration_manager'):
            return jsonify({"error": "Agent not found or collaboration not enabled"}), 404
        
        # Leave collaboration
        success = await agent.collaboration_manager.leave_collaboration(collaboration_id)
        
        return jsonify({
            "success": success,
            "collaboration_id": collaboration_id,
            "agent_id": agent_id
        })
    
    except Exception as e:
        logger.error("Error leaving collaboration", error=str(e))
        return jsonify({"error": str(e)}), 500


@a2a_bp.route('/agents/<agent_id>/ping', methods=['POST'])
async def ping_agent(agent_id: str):
    """Ping another agent to check availability"""
    try:
        data = request.get_json() or {}
        sender_id = data.get('sender_id')
        timeout = data.get('timeout', 10)
        
        if not sender_id:
            return jsonify({"error": "sender_id is required"}), 400
        
        registry = get_agent_registry()
        if not registry:
            return jsonify({"error": "Agent registry not available"}), 500
        
        # Get the sender agent
        sender_agent = registry.running_agents.get(sender_id)
        if not sender_agent or not hasattr(sender_agent, 'a2a_communicator'):
            return jsonify({"error": "Sender agent not found or A2A not enabled"}), 404
        
        # Ping target agent
        success = await sender_agent.a2a_communicator.ping_agent(agent_id, timeout)
        
        return jsonify({
            "success": success,
            "target_agent_id": agent_id,
            "sender_id": sender_id,
            "timeout": timeout,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error("Error pinging agent", error=str(e))
        return jsonify({"error": str(e)}), 500


@a2a_bp.route('/agents/<agent_id>/stats', methods=['GET'])
def get_agent_a2a_stats(agent_id: str):
    """Get A2A statistics for a specific agent"""
    try:
        registry = get_agent_registry()
        if not registry:
            return jsonify({"error": "Agent registry not available"}), 500
        
        # Get the agent
        agent = registry.running_agents.get(agent_id)
        if not agent:
            return jsonify({"error": "Agent not found"}), 404
        
        stats = {}
        
        # Communication stats
        if hasattr(agent, 'a2a_communicator') and agent.a2a_communicator:
            stats['communication'] = agent.a2a_communicator.get_stats()
        
        # Discovery stats
        if hasattr(agent, 'a2a_discovery') and agent.a2a_discovery:
            stats['discovery'] = {
                "discovered_agents": len(agent.a2a_discovery.get_all_discovered_agents()),
                "capability_stats": agent.a2a_discovery.get_capability_stats(),
                "own_capabilities": [cap.name for cap in agent.a2a_discovery.own_capabilities]
            }
        
        # Task management stats
        if hasattr(agent, 'task_manager') and agent.task_manager:
            stats['tasks'] = agent.task_manager.get_task_stats()
        
        # Collaboration stats
        if hasattr(agent, 'collaboration_manager') and agent.collaboration_manager:
            active_collabs = agent.collaboration_manager.get_active_collaborations()
            stats['collaborations'] = {
                "active_collaborations": len(active_collabs),
                "collaborations": [
                    {
                        "id": collab.collaboration_id,
                        "title": collab.title,
                        "status": collab.status.value,
                        "participants": len(collab.participants)
                    }
                    for collab in active_collabs
                ]
            }
        
        return jsonify({
            "success": True,
            "agent_id": agent_id,
            "a2a_enabled": hasattr(agent, 'a2a_communicator'),
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error("Error getting agent A2A stats", error=str(e))
        return jsonify({"error": str(e)}), 500


@a2a_bp.route('/network/overview', methods=['GET'])
def get_network_overview():
    """Get overview of the entire A2A network"""
    try:
        registry = get_agent_registry()
        if not registry:
            return jsonify({"error": "Agent registry not available"}), 500
        
        network_data = {
            "agents": [],
            "connections": [],
            "tasks": [],
            "collaborations": [],
            "capabilities": {}
        }
        
        # Collect data from all A2A-enabled agents
        for agent_reg in registry.list_agents():
            agent = registry.running_agents.get(agent_reg.id)
            if not agent or not hasattr(agent, 'a2a_communicator'):
                continue
            
            # Agent info
            agent_info = {
                "id": agent_reg.id,
                "name": agent_reg.name,
                "status": agent_reg.status.value,
                "capabilities": getattr(agent_reg.config, 'a2a_capabilities', []),
                "load": getattr(agent_reg.metrics, 'load', 0.0)
            }
            network_data["agents"].append(agent_info)
            
            # Capabilities
            for cap in agent_info["capabilities"]:
                if cap not in network_data["capabilities"]:
                    network_data["capabilities"][cap] = 0
                network_data["capabilities"][cap] += 1
            
            # Known connections (discovered agents)
            if hasattr(agent, 'a2a_discovery') and agent.a2a_discovery:
                known_agents = agent.a2a_discovery.get_all_discovered_agents()
                for known_agent in known_agents:
                    network_data["connections"].append({
                        "source": agent_reg.id,
                        "target": known_agent.agent_id,
                        "last_seen": known_agent.last_seen.isoformat()
                    })
            
            # Active tasks
            if hasattr(agent, 'task_manager') and agent.task_manager:
                active_tasks = agent.task_manager.get_active_tasks()
                for task in active_tasks:
                    network_data["tasks"].append({
                        "task_id": task.task_id,
                        "type": task.task_type,
                        "status": task.status.value,
                        "requester": task.requester_id,
                        "assigned_to": task.assigned_agent_id
                    })
            
            # Active collaborations
            if hasattr(agent, 'collaboration_manager') and agent.collaboration_manager:
                active_collabs = agent.collaboration_manager.get_active_collaborations()
                for collab in active_collabs:
                    network_data["collaborations"].append({
                        "id": collab.collaboration_id,
                        "title": collab.title,
                        "coordinator": collab.coordinator_id,
                        "participants": collab.participants,
                        "status": collab.status.value
                    })
        
        # Calculate network statistics
        total_agents = len(network_data["agents"])
        total_connections = len(network_data["connections"])
        total_tasks = len(network_data["tasks"])
        total_collaborations = len(network_data["collaborations"])
        
        return jsonify({
            "success": True,
            "network_data": network_data,
            "statistics": {
                "total_agents": total_agents,
                "total_connections": total_connections,
                "total_tasks": total_tasks,
                "total_collaborations": total_collaborations,
                "unique_capabilities": len(network_data["capabilities"]),
                "network_density": total_connections / max(total_agents * (total_agents - 1), 1)
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error("Error getting network overview", error=str(e))
        return jsonify({"error": str(e)}), 500