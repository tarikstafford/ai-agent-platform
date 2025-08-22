#!/usr/bin/env python3
"""
Server runner for the AI Agent Platform
"""

import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from hosting.server import main
except ImportError as e:
    print("❌ Import error:", e)
    print("\n🔧 Dependencies not installed. Please run:")
    print("   python setup_platform.py")
    print("   or")
    print("   pip install -r requirements.txt")
    sys.exit(1)

if __name__ == "__main__":
    main()