#!/usr/bin/env python3
"""
Setup script for AI Agent Platform
Installs dependencies and configures environment
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9+ is required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def main():
    """Main setup function"""
    print("🚀 AI Agent Platform Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    commands = [
        ("pip install --upgrade pip", "Upgrading pip"),
        ("pip install -r requirements.txt", "Installing dependencies"),
    ]
    
    for cmd, desc in commands:
        if not run_command(cmd, desc):
            print(f"❌ Setup failed at: {desc}")
            sys.exit(1)
    
    # Create directories
    print("📁 Creating directories...")
    dirs = ["data", "logs", "agent_configs"]
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"   Created: {dir_name}/")
    
    # Setup environment file
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if not env_file.exists() and env_example.exists():
        print("📝 Creating .env file from template...")
        with open(env_example) as src, open(env_file, "w") as dst:
            dst.write(src.read())
        print("   Please edit .env and add your API keys")
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Edit .env file and add your API keys:")
    print("   - OPENAI_API_KEY=your_openai_key")
    print("   - ANTHROPIC_API_KEY=your_anthropic_key (optional)")
    print("\n2. Start the platform:")
    print("   python run_server.py")
    print("\n3. Access dashboard:")
    print("   http://127.0.0.1:8000/api/dashboard/ui")
    print("\n4. Test with examples:")
    print("   python examples/platform_demo.py")

if __name__ == "__main__":
    main()