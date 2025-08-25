from flask import Flask
from flask_cors import CORS
import asyncio
import threading
from typing import Optional

import sys
from pathlib import Path

# Add src to path if not already there
src_path = str(Path(__file__).parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from hosting import AgentManager
from .routes import agents_bp, dashboard_bp
from .websockets import setup_websocket_handlers
from ..a2a.message_store import start_message_store
from ..config.message_inspector import get_config

# Import Langflow routes if available
try:
    from .langflow_routes import langflow_bp
    LANGFLOW_ROUTES_AVAILABLE = True
except ImportError:
    langflow_bp = None
    LANGFLOW_ROUTES_AVAILABLE = False

# Import A2A routes
try:
    from .a2a_routes import a2a_bp
    A2A_ROUTES_AVAILABLE = True
except ImportError:
    a2a_bp = None
    A2A_ROUTES_AVAILABLE = False


def create_app(config: Optional[dict] = None) -> Flask:
    """Create Flask application with agent management"""
    app = Flask(__name__)
    
    # Enable CORS for dashboard
    CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])
    
    # Configuration
    app.config.update(config or {})
    app.config.setdefault('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Initialize agent manager
    agent_manager = AgentManager()
    app.agent_manager = agent_manager
    
    # Register blueprints
    app.register_blueprint(agents_bp, url_prefix='/api/agents')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    
    # Register Langflow blueprint if available
    if LANGFLOW_ROUTES_AVAILABLE:
        app.register_blueprint(langflow_bp, url_prefix='/api/langflow')
    
    # Register A2A blueprint if available
    if A2A_ROUTES_AVAILABLE:
        app.register_blueprint(a2a_bp)
    
    # Setup WebSocket handlers
    setup_websocket_handlers(app)
    
    # Create event loop for async operations
    loop = asyncio.new_event_loop()
    
    def run_async_loop():
        asyncio.set_event_loop(loop)
        loop.run_forever()
    
    thread = threading.Thread(target=run_async_loop, daemon=True)
    thread.start()
    app.async_loop = loop
    
    # Initialize message store and saved agents on app creation
    def startup():
        """Initialize on startup"""
        # Initialize message store with configuration
        inspector_config = get_config()
        message_store_config = inspector_config.to_message_store_config()
        
        # Start message store
        future = asyncio.run_coroutine_threadsafe(
            start_message_store(message_store_config), 
            app.async_loop
        )
        try:
            message_store = future.result(timeout=10)
            app.message_store = message_store
            app.logger.info("Message store initialized")
        except Exception as e:
            app.logger.error(f"Failed to initialize message store: {e}")
        
        # Load any saved agents
        future = asyncio.run_coroutine_threadsafe(
            agent_manager.load_saved_agents(), 
            app.async_loop
        )
        try:
            future.result(timeout=10)
        except Exception as e:
            app.logger.error(f"Failed to load saved agents: {e}")
    
    # Call startup immediately
    startup()
    
    @app.teardown_appcontext
    def close_db(error):
        """Cleanup on teardown"""
        pass
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {"status": "healthy", "service": "ai-agent-platform"}
    
    return app


def run_app(host: str = "127.0.0.1", port: int = 8000, debug: bool = False):
    """Run the Flask application"""
    app = create_app()
    app.run(host=host, port=port, debug=debug, threaded=True)