"""REST API for agent management"""

# Import routes directly, but import create_app lazily to avoid circular imports
from .routes import agents_bp, dashboard_bp

def create_app(*args, **kwargs):
    """Lazy import wrapper for create_app to avoid circular imports"""
    from .app import create_app as _create_app
    return _create_app(*args, **kwargs)

__all__ = [
    "create_app",
    "agents_bp", 
    "dashboard_bp",
]