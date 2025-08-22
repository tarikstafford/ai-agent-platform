from typing import Dict, Any, List, Optional
import asyncio
from .server import LangflowServer
from .workflow import WorkflowManager
import structlog

logger = structlog.get_logger()


class WorkflowBuilder:
    """High-level interface for building and managing visual workflows"""
    
    def __init__(self, langflow_server: Optional[LangflowServer] = None):
        self.langflow_server = langflow_server or LangflowServer()
        self.workflow_manager = WorkflowManager()
        self.logger = logger.bind(component="workflow_builder")
    
    async def initialize(self) -> bool:
        """Initialize the workflow builder"""
        try:
            # Start Langflow server if not running
            if not self.langflow_server.is_running():
                success = await self.langflow_server.start()
                if not success:
                    self.logger.error("Failed to start Langflow server")
                    return False
            
            self.logger.info("Workflow builder initialized")
            return True
            
        except Exception as e:
            self.logger.error("Error initializing workflow builder", error=str(e))
            return False
    
    def get_builder_url(self) -> str:
        """Get the URL for the visual workflow builder"""
        return f"{self.langflow_server.base_url}/flow"
    
    def get_available_components(self) -> Dict[str, Any]:
        """Get available components for workflow building"""
        # This would typically come from Langflow's component registry
        components = {
            "inputs": [
                {
                    "type": "TextInput",
                    "name": "Text Input",
                    "description": "Accept text input from user",
                    "category": "inputs"
                },
                {
                    "type": "FileInput",
                    "name": "File Input", 
                    "description": "Accept file upload",
                    "category": "inputs"
                }
            ],
            "llms": [
                {
                    "type": "OpenAI",
                    "name": "OpenAI",
                    "description": "OpenAI language model",
                    "category": "llms"
                },
                {
                    "type": "Anthropic",
                    "name": "Anthropic Claude",
                    "description": "Anthropic Claude model",
                    "category": "llms"
                }
            ],
            "tools": [
                {
                    "type": "Calculator",
                    "name": "Calculator",
                    "description": "Perform mathematical calculations",
                    "category": "tools"
                },
                {
                    "type": "WebSearch",
                    "name": "Web Search",
                    "description": "Search the web for information",
                    "category": "tools"
                }
            ],
            "memory": [
                {
                    "type": "ConversationBuffer",
                    "name": "Conversation Memory",
                    "description": "Store conversation history",
                    "category": "memory"
                },
                {
                    "type": "VectorStore",
                    "name": "Vector Database",
                    "description": "Store and retrieve embeddings",
                    "category": "memory"
                }
            ],
            "outputs": [
                {
                    "type": "TextOutput",
                    "name": "Text Output",
                    "description": "Output text response",
                    "category": "outputs"
                },
                {
                    "type": "FileOutput",
                    "name": "File Output",
                    "description": "Output file download",
                    "category": "outputs"
                }
            ]
        }
        
        return components
    
    def create_workflow(self, name: str, description: str = "") -> Optional[str]:
        """Create a new empty workflow"""
        try:
            flow_data = {
                "name": name,
                "description": description,
                "nodes": [],
                "edges": []
            }
            
            flow_id = self.langflow_server.create_flow(flow_data)
            if flow_id:
                # Also save locally
                self.workflow_manager.save_workflow(flow_data, name)
                self.logger.info("Workflow created", name=name, flow_id=flow_id)
            
            return flow_id
            
        except Exception as e:
            self.logger.error("Error creating workflow", name=name, error=str(e))
            return None
    
    def get_workflow_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get available workflow templates"""
        return self.workflow_manager.get_template_workflows()
    
    def create_from_template(self, template_name: str, name: str) -> Optional[str]:
        """Create a workflow from a template"""
        try:
            workflow_data = self.workflow_manager.create_from_template(template_name, name)
            if not workflow_data:
                return None
            
            # Create in Langflow
            flow_id = self.langflow_server.create_flow(workflow_data)
            if flow_id:
                self.logger.info("Workflow created from template", 
                               template=template_name, name=name, flow_id=flow_id)
            
            return flow_id
            
        except Exception as e:
            self.logger.error("Error creating workflow from template", 
                            template=template_name, name=name, error=str(e))
            return None
    
    def duplicate_workflow(self, source_flow_id: str, new_name: str) -> Optional[str]:
        """Duplicate an existing workflow"""
        try:
            # Export the source workflow
            flow_data = self.langflow_server.export_flow(source_flow_id)
            if not flow_data:
                return None
            
            # Update name and create new workflow
            flow_data["name"] = new_name
            flow_data["description"] = f"Duplicate of workflow {source_flow_id}"
            
            new_flow_id = self.langflow_server.create_flow(flow_data)
            if new_flow_id:
                # Save locally too
                self.workflow_manager.save_workflow(flow_data, new_name)
                self.logger.info("Workflow duplicated", 
                               source=source_flow_id, new_id=new_flow_id)
            
            return new_flow_id
            
        except Exception as e:
            self.logger.error("Error duplicating workflow", 
                            source=source_flow_id, error=str(e))
            return None
    
    def get_workflow_editor_config(self, flow_id: str) -> Dict[str, Any]:
        """Get configuration for embedding the workflow editor"""
        return {
            "langflow_url": self.langflow_server.base_url,
            "flow_id": flow_id,
            "editor_url": f"{self.langflow_server.base_url}/flow/{flow_id}",
            "api_base": f"{self.langflow_server.base_url}/api/v1",
            "components": self.get_available_components(),
            "templates": self.get_workflow_templates()
        }
    
    def validate_workflow(self, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a workflow configuration"""
        errors = []
        warnings = []
        
        try:
            # Check required fields
            if "nodes" not in flow_data:
                errors.append("Missing 'nodes' field")
            
            if "edges" not in flow_data:
                errors.append("Missing 'edges' field")
            
            # Check nodes
            if "nodes" in flow_data:
                nodes = flow_data["nodes"]
                if not isinstance(nodes, list):
                    errors.append("'nodes' must be a list")
                else:
                    node_ids = set()
                    for i, node in enumerate(nodes):
                        if not isinstance(node, dict):
                            errors.append(f"Node {i} must be a dictionary")
                            continue
                        
                        if "id" not in node:
                            errors.append(f"Node {i} missing 'id' field")
                        else:
                            node_id = node["id"]
                            if node_id in node_ids:
                                errors.append(f"Duplicate node ID: {node_id}")
                            node_ids.add(node_id)
                        
                        if "type" not in node:
                            errors.append(f"Node {node.get('id', i)} missing 'type' field")
            
            # Check edges
            if "edges" in flow_data and "nodes" in flow_data:
                edges = flow_data["edges"]
                if not isinstance(edges, list):
                    errors.append("'edges' must be a list")
                else:
                    node_ids = {node["id"] for node in flow_data["nodes"] if "id" in node}
                    for i, edge in enumerate(edges):
                        if not isinstance(edge, dict):
                            errors.append(f"Edge {i} must be a dictionary")
                            continue
                        
                        for field in ["source", "target"]:
                            if field not in edge:
                                errors.append(f"Edge {i} missing '{field}' field")
                            elif edge[field] not in node_ids:
                                errors.append(f"Edge {i} {field} '{edge[field]}' not found in nodes")
            
            # Check for isolated nodes
            if "nodes" in flow_data and "edges" in flow_data:
                connected_nodes = set()
                for edge in flow_data["edges"]:
                    if "source" in edge:
                        connected_nodes.add(edge["source"])
                    if "target" in edge:
                        connected_nodes.add(edge["target"])
                
                for node in flow_data["nodes"]:
                    if "id" in node and node["id"] not in connected_nodes:
                        warnings.append(f"Node '{node['id']}' is not connected")
        
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def test_workflow(self, flow_id: str, test_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Test a workflow with sample inputs"""
        try:
            result = self.langflow_server.run_flow(flow_id, test_inputs)
            
            return {
                "success": result is not None,
                "result": result,
                "inputs": test_inputs
            }
            
        except Exception as e:
            self.logger.error("Error testing workflow", flow_id=flow_id, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "inputs": test_inputs
            }