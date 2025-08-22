from typing import Any, Dict, List, Optional, Union
import json
import asyncio

from agents import BaseAgent, AgentConfig, AgentResponse, AgentState
from .server import LangflowServer

import structlog
logger = structlog.get_logger()


class LangflowAgent(BaseAgent):
    """Agent that executes Langflow visual workflows"""
    
    def __init__(self, config: AgentConfig, flow_id: Optional[str] = None, flow_data: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.flow_id = flow_id
        self.flow_data = flow_data
        self.langflow_server: Optional[LangflowServer] = None
        
        # Initialize Langflow server if not provided
        if not hasattr(config, 'langflow_server'):
            self.langflow_server = LangflowServer()
        else:
            self.langflow_server = config.langflow_server
    
    async def think(self, input_data: Union[str, Dict[str, Any]]) -> AgentResponse:
        """Process input using Langflow workflow"""
        try:
            # Ensure Langflow server is running
            if not self.langflow_server.is_running():
                started = await self.langflow_server.start()
                if not started:
                    return AgentResponse(
                        content="Failed to start Langflow server",
                        success=False,
                        error="Langflow server startup failed",
                        state=AgentState.ERROR
                    )
            
            # Prepare inputs for the flow
            if isinstance(input_data, str):
                flow_inputs = {"input": input_data}
            elif isinstance(input_data, dict):
                flow_inputs = input_data
            else:
                flow_inputs = {"input": str(input_data)}
            
            # If no flow_id but have flow_data, create the flow first
            if not self.flow_id and self.flow_data:
                self.flow_id = self.langflow_server.create_flow(self.flow_data)
                if not self.flow_id:
                    return AgentResponse(
                        content="Failed to create workflow",
                        success=False,
                        error="Could not create flow in Langflow",
                        state=AgentState.ERROR
                    )
            
            if not self.flow_id:
                return AgentResponse(
                    content="No workflow configured",
                    success=False,
                    error="No flow_id or flow_data provided",
                    state=AgentState.ERROR
                )
            
            # Run the flow
            self.logger.info("Running Langflow workflow", flow_id=self.flow_id, inputs=flow_inputs)
            result = self.langflow_server.run_flow(self.flow_id, flow_inputs)
            
            if result is None:
                return AgentResponse(
                    content="Workflow execution failed",
                    success=False,
                    error="Flow execution returned no result",
                    state=AgentState.ERROR
                )
            
            # Extract the output
            output_content = self._extract_output(result)
            
            return AgentResponse(
                content=output_content,
                success=True,
                metadata={
                    "flow_id": self.flow_id,
                    "flow_result": result,
                    "model": "langflow-workflow"
                }
            )
            
        except Exception as e:
            self.logger.error("Error in Langflow agent", error=str(e))
            return AgentResponse(
                content=f"Workflow execution error: {str(e)}",
                success=False,
                error=str(e),
                state=AgentState.ERROR
            )
    
    async def act(self, action: Dict[str, Any]) -> Any:
        """Execute workflow-based actions"""
        action_type = action.get("type", "run_workflow")
        
        if action_type == "run_workflow":
            inputs = action.get("inputs", {})
            result = await self.think(inputs)
            return {
                "success": result.success,
                "content": result.content,
                "error": result.error
            }
        
        elif action_type == "get_workflow_info":
            if not self.flow_id:
                return {"error": "No workflow configured"}
            
            flow_info = self.langflow_server.get_flow(self.flow_id)
            return {"workflow": flow_info}
        
        elif action_type == "export_workflow":
            if not self.flow_id:
                return {"error": "No workflow configured"}
            
            exported = self.langflow_server.export_flow(self.flow_id)
            return {"exported_workflow": exported}
        
        elif action_type == "update_workflow":
            new_flow_data = action.get("flow_data")
            if new_flow_data:
                # Create new flow and update flow_id
                new_flow_id = self.langflow_server.create_flow(new_flow_data)
                if new_flow_id:
                    self.flow_id = new_flow_id
                    self.flow_data = new_flow_data
                    return {"success": True, "new_flow_id": new_flow_id}
                else:
                    return {"error": "Failed to create new workflow"}
            else:
                return {"error": "No flow_data provided"}
        
        return {"error": f"Unknown action type: {action_type}"}
    
    def _extract_output(self, flow_result: Dict[str, Any]) -> str:
        """Extract meaningful output from flow result"""
        try:
            # Try different common output formats
            if "outputs" in flow_result:
                outputs = flow_result["outputs"]
                if isinstance(outputs, list) and outputs:
                    return str(outputs[0])
                elif isinstance(outputs, dict):
                    # Look for common output keys
                    for key in ["result", "output", "response", "text"]:
                        if key in outputs:
                            return str(outputs[key])
                    # Return first value if no common keys found
                    if outputs:
                        return str(list(outputs.values())[0])
                return str(outputs)
            
            elif "result" in flow_result:
                return str(flow_result["result"])
            
            elif "response" in flow_result:
                return str(flow_result["response"])
            
            else:
                # Return stringified result if no standard format
                return json.dumps(flow_result, indent=2)
                
        except Exception as e:
            self.logger.error("Error extracting output", error=str(e))
            return f"Workflow completed but output extraction failed: {str(e)}"
    
    def get_workflow_summary(self) -> Dict[str, Any]:
        """Get summary of the current workflow"""
        summary = {
            "agent_type": "langflow",
            "flow_id": self.flow_id,
            "has_flow_data": bool(self.flow_data),
            "server_running": False
        }
        
        if self.langflow_server:
            summary["server_running"] = self.langflow_server.is_running()
            summary["server_url"] = self.langflow_server.base_url
            
            if self.flow_id:
                flow_info = self.langflow_server.get_flow(self.flow_id)
                if flow_info:
                    summary["workflow_name"] = flow_info.get("name", "Unknown")
                    summary["workflow_description"] = flow_info.get("description", "")
        
        return summary