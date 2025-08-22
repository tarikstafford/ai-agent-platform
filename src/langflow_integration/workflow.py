import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import structlog

logger = structlog.get_logger()


class WorkflowManager:
    """Manages Langflow workflow templates and storage"""
    
    def __init__(self, workflows_dir: str = "./workflows"):
        self.workflows_dir = Path(workflows_dir)
        self.workflows_dir.mkdir(exist_ok=True)
        self.logger = logger.bind(component="workflow_manager")
    
    def save_workflow(self, workflow_data: Dict[str, Any], name: str) -> bool:
        """Save a workflow to disk"""
        try:
            workflow_file = self.workflows_dir / f"{name}.json"
            with open(workflow_file, 'w') as f:
                json.dump(workflow_data, f, indent=2)
            
            self.logger.info("Workflow saved", name=name, file=str(workflow_file))
            return True
            
        except Exception as e:
            self.logger.error("Error saving workflow", name=name, error=str(e))
            return False
    
    def load_workflow(self, name: str) -> Optional[Dict[str, Any]]:
        """Load a workflow from disk"""
        try:
            workflow_file = self.workflows_dir / f"{name}.json"
            if not workflow_file.exists():
                return None
            
            with open(workflow_file, 'r') as f:
                workflow_data = json.load(f)
            
            self.logger.info("Workflow loaded", name=name)
            return workflow_data
            
        except Exception as e:
            self.logger.error("Error loading workflow", name=name, error=str(e))
            return None
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all available workflows"""
        workflows = []
        
        try:
            for workflow_file in self.workflows_dir.glob("*.json"):
                try:
                    with open(workflow_file, 'r') as f:
                        workflow_data = json.load(f)
                    
                    workflows.append({
                        "name": workflow_file.stem,
                        "file": str(workflow_file),
                        "title": workflow_data.get("name", workflow_file.stem),
                        "description": workflow_data.get("description", ""),
                        "created": workflow_file.stat().st_ctime,
                        "modified": workflow_file.stat().st_mtime
                    })
                    
                except Exception as e:
                    self.logger.warning("Error reading workflow file", file=str(workflow_file), error=str(e))
        
        except Exception as e:
            self.logger.error("Error listing workflows", error=str(e))
        
        return sorted(workflows, key=lambda x: x["modified"], reverse=True)
    
    def delete_workflow(self, name: str) -> bool:
        """Delete a workflow"""
        try:
            workflow_file = self.workflows_dir / f"{name}.json"
            if workflow_file.exists():
                workflow_file.unlink()
                self.logger.info("Workflow deleted", name=name)
                return True
            return False
            
        except Exception as e:
            self.logger.error("Error deleting workflow", name=name, error=str(e))
            return False
    
    def get_template_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get predefined workflow templates"""
        templates = {
            "simple_chat": {
                "name": "Simple Chat Agent",
                "description": "Basic conversational agent with OpenAI",
                "data": {
                    "nodes": [
                        {
                            "id": "input",
                            "type": "TextInput",
                            "position": {"x": 100, "y": 100},
                            "data": {"name": "user_input"}
                        },
                        {
                            "id": "openai",
                            "type": "OpenAI",
                            "position": {"x": 300, "y": 100},
                            "data": {
                                "model": "gpt-3.5-turbo",
                                "temperature": 0.7
                            }
                        },
                        {
                            "id": "output",
                            "type": "TextOutput", 
                            "position": {"x": 500, "y": 100},
                            "data": {"name": "response"}
                        }
                    ],
                    "edges": [
                        {"source": "input", "target": "openai"},
                        {"source": "openai", "target": "output"}
                    ]
                }
            },
            
            "rag_agent": {
                "name": "RAG Knowledge Agent",
                "description": "Retrieval-augmented generation with vector search",
                "data": {
                    "nodes": [
                        {
                            "id": "input",
                            "type": "TextInput",
                            "position": {"x": 50, "y": 100},
                            "data": {"name": "query"}
                        },
                        {
                            "id": "embeddings",
                            "type": "OpenAIEmbeddings",
                            "position": {"x": 200, "y": 50},
                            "data": {}
                        },
                        {
                            "id": "vectordb",
                            "type": "Chroma",
                            "position": {"x": 200, "y": 150},
                            "data": {"collection_name": "knowledge_base"}
                        },
                        {
                            "id": "retriever",
                            "type": "VectorStoreRetriever",
                            "position": {"x": 350, "y": 100},
                            "data": {"search_kwargs": {"k": 3}}
                        },
                        {
                            "id": "prompt",
                            "type": "PromptTemplate",
                            "position": {"x": 500, "y": 100},
                            "data": {
                                "template": "Context: {context}\n\nQuestion: {question}\n\nAnswer:"
                            }
                        },
                        {
                            "id": "llm",
                            "type": "OpenAI",
                            "position": {"x": 650, "y": 100},
                            "data": {"model": "gpt-3.5-turbo"}
                        },
                        {
                            "id": "output",
                            "type": "TextOutput",
                            "position": {"x": 800, "y": 100},
                            "data": {"name": "answer"}
                        }
                    ],
                    "edges": [
                        {"source": "input", "target": "retriever"},
                        {"source": "embeddings", "target": "vectordb"},
                        {"source": "vectordb", "target": "retriever"},
                        {"source": "retriever", "target": "prompt"},
                        {"source": "input", "target": "prompt"},
                        {"source": "prompt", "target": "llm"},
                        {"source": "llm", "target": "output"}
                    ]
                }
            },
            
            "tool_agent": {
                "name": "Tool-Using Agent",
                "description": "Agent with calculator and search tools",
                "data": {
                    "nodes": [
                        {
                            "id": "input",
                            "type": "TextInput",
                            "position": {"x": 50, "y": 200},
                            "data": {"name": "task"}
                        },
                        {
                            "id": "calculator",
                            "type": "Calculator",
                            "position": {"x": 200, "y": 100},
                            "data": {}
                        },
                        {
                            "id": "search",
                            "type": "SerpAPI",
                            "position": {"x": 200, "y": 300},
                            "data": {}
                        },
                        {
                            "id": "agent",
                            "type": "ZeroShotAgent",
                            "position": {"x": 400, "y": 200},
                            "data": {
                                "tools": ["calculator", "search"]
                            }
                        },
                        {
                            "id": "executor",
                            "type": "AgentExecutor",
                            "position": {"x": 550, "y": 200},
                            "data": {}
                        },
                        {
                            "id": "output",
                            "type": "TextOutput",
                            "position": {"x": 700, "y": 200},
                            "data": {"name": "result"}
                        }
                    ],
                    "edges": [
                        {"source": "calculator", "target": "agent"},
                        {"source": "search", "target": "agent"},
                        {"source": "input", "target": "executor"},
                        {"source": "agent", "target": "executor"},
                        {"source": "executor", "target": "output"}
                    ]
                }
            }
        }
        
        return templates
    
    def create_from_template(self, template_name: str, name: str) -> Optional[Dict[str, Any]]:
        """Create a workflow from a template"""
        templates = self.get_template_workflows()
        
        if template_name not in templates:
            self.logger.error("Template not found", template=template_name)
            return None
        
        template = templates[template_name]
        workflow_data = template["data"].copy()
        workflow_data["name"] = name
        workflow_data["description"] = f"Created from {template['name']} template"
        
        if self.save_workflow(workflow_data, name):
            return workflow_data
        
        return None