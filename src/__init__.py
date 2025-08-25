"""
AI Agent Hosting Platform

A comprehensive platform for building, hosting, and managing distributed multi-agent systems 
with visual workflow creation and Agent-to-Agent (A2A) communication capabilities.
"""
import sys
from pathlib import Path

# Ensure src is in path for absolute imports
src_path = str(Path(__file__).parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

__version__ = "1.0.0"
__author__ = "AI Agent Platform Team"