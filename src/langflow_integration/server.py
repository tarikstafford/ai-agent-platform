import asyncio
import subprocess
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger()


class LangflowServer:
    """Manages embedded Langflow server for visual workflow building"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7860):
        self.host = host
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self.base_url = f"http://{host}:{port}"
        self.logger = logger.bind(component="langflow_server")
        
    async def start(self) -> bool:
        """Start Langflow server"""
        try:
            # Check if already running
            if self.is_running():
                self.logger.info("Langflow server already running")
                return True
            
            self.logger.info("Starting Langflow server", host=self.host, port=self.port)
            
            # Start Langflow server
            cmd = [
                "python3", "-m", "langflow", "run",
                "--host", self.host,
                "--port", str(self.port),
                "--no-open-browser"
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for server to be ready
            for i in range(30):  # Wait up to 30 seconds
                if self.is_running():
                    self.logger.info("Langflow server started successfully")
                    return True
                
                # Check if process has terminated
                if self.process.poll() is not None:
                    # Process has terminated, get error output
                    stdout, stderr = self.process.communicate()
                    self.logger.error("Langflow process terminated", 
                                    stdout=stdout, 
                                    stderr=stderr,
                                    return_code=self.process.returncode)
                    return False
                    
                await asyncio.sleep(1)
            
            # If we get here, timeout occurred
            self.logger.error("Langflow server failed to start (timeout)")
            if self.process:
                # Try to get any output
                try:
                    stdout, stderr = self.process.communicate(timeout=1)
                    self.logger.error("Process output", stdout=stdout, stderr=stderr)
                except:
                    pass
            return False
            
        except Exception as e:
            self.logger.error("Error starting Langflow server", error=str(e))
            return False
    
    def stop(self):
        """Stop Langflow server"""
        if self.process:
            self.logger.info("Stopping Langflow server")
            self.process.terminate()
            self.process.wait()
            self.process = None
    
    def is_running(self) -> bool:
        """Check if Langflow server is running"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def get_flows(self) -> Dict[str, Any]:
        """Get all flows from Langflow"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/flows")
            if response.status_code == 200:
                return response.json()
            return {"flows": []}
        except Exception as e:
            self.logger.error("Error getting flows", error=str(e))
            return {"flows": []}
    
    def create_flow(self, flow_data: Dict[str, Any]) -> Optional[str]:
        """Create a new flow in Langflow"""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/flows",
                json=flow_data
            )
            if response.status_code == 201:
                result = response.json()
                return result.get("id")
            return None
        except Exception as e:
            self.logger.error("Error creating flow", error=str(e))
            return None
    
    def get_flow(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific flow by ID"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/flows/{flow_id}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            self.logger.error("Error getting flow", flow_id=flow_id, error=str(e))
            return None
    
    def run_flow(self, flow_id: str, inputs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run a flow with given inputs"""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/flows/{flow_id}/run",
                json={"inputs": inputs}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            self.logger.error("Error running flow", flow_id=flow_id, error=str(e))
            return None
    
    def export_flow(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Export a flow as JSON"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/flows/{flow_id}/export")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            self.logger.error("Error exporting flow", flow_id=flow_id, error=str(e))
            return None
    
    def import_flow(self, flow_data: Dict[str, Any]) -> Optional[str]:
        """Import a flow from JSON"""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/flows/import",
                json=flow_data
            )
            if response.status_code == 201:
                result = response.json()
                return result.get("id")
            return None
        except Exception as e:
            self.logger.error("Error importing flow", error=str(e))
            return None