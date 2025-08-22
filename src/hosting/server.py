#!/usr/bin/env python3
"""
Main server for hosting AI agents with web dashboard
"""

import asyncio
import signal
import sys
from pathlib import Path
import click
import structlog

import sys
from pathlib import Path

# Add src to path if not already there
src_path = str(Path(__file__).parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from api.app import create_app, run_app
from hosting.manager import AgentManager

logger = structlog.get_logger()


class AgentServer:
    """Main server for hosting AI agents"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8000, debug: bool = False):
        self.host = host
        self.port = port
        self.debug = debug
        self.app = None
        self.logger = logger.bind(component="agent_server")
    
    def start(self):
        """Start the agent server"""
        self.logger.info("Starting AI Agent Server", host=self.host, port=self.port)
        
        try:
            # Create Flask app
            self.app = create_app({
                'DEBUG': self.debug,
                'HOST': self.host,
                'PORT': self.port
            })
            
            # Setup signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # Start server
            self.logger.info("Server starting", url=f"http://{self.host}:{self.port}")
            self.logger.info("Dashboard available at", url=f"http://{self.host}:{self.port}/api/dashboard/ui")
            
            self.app.run(
                host=self.host,
                port=self.port,
                debug=self.debug,
                threaded=True,
                use_reloader=False  # Disable reloader to avoid issues with threads
            )
            
        except Exception as e:
            self.logger.error("Failed to start server", error=str(e))
            sys.exit(1)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info("Received shutdown signal", signal=signum)
        self.stop()
    
    def stop(self):
        """Stop the server gracefully"""
        self.logger.info("Stopping AI Agent Server")
        
        if self.app and hasattr(self.app, 'agent_manager'):
            # Shutdown agent manager
            loop = self.app.async_loop
            if loop and not loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    self.app.agent_manager.shutdown(),
                    loop
                )
        
        sys.exit(0)


@click.command()
@click.option('--host', default='127.0.0.1', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--config-dir', help='Directory for agent configurations')
def main(host: str, port: int, debug: bool, config_dir: str):
    """Start the AI Agent Server"""
    
    # Setup logging
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Create server
    server = AgentServer(host=host, port=port, debug=debug)
    
    # Start server
    server.start()


if __name__ == '__main__':
    main()