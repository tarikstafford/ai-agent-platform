#!/usr/bin/env python3
"""
Check if the AI Agent Platform is properly set up
"""

import sys
import os
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        ('pydantic', 'pydantic'),
        ('langchain', 'langchain'), 
        ('openai', 'openai'),
        ('flask', 'flask'),
        ('structlog', 'structlog'),
        ('httpx', 'httpx'),
        ('python-dotenv', 'dotenv'),
        ('click', 'click')
    ]
    
    missing = []
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)
    
    return missing

def check_files():
    """Check if required files exist"""
    required_files = [
        'src/hosting/__init__.py',
        'src/api/__init__.py', 
        'src/agents/__init__.py',
        'src/tools/__init__.py',
        '.env.example'
    ]
    
    missing = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing.append(file_path)
    
    return missing

def check_import():
    """Check if imports work correctly"""
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    
    try:
        from hosting.server import main
        return True, None
    except ImportError as e:
        return False, str(e)

def main():
    """Main check function"""
    print("🔍 AI Agent Platform Setup Check")
    print("=" * 40)
    
    # Check Python version
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9+ required")
        return False
    else:
        print("✅ Python version OK")
    
    # Check files
    missing_files = check_files()
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False
    else:
        print("✅ Required files present")
    
    # Check dependencies
    missing_deps = check_dependencies()
    if missing_deps:
        print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
        print("\n🔧 To fix, run:")
        print("   python setup_platform.py")
        return False
    else:
        print("✅ Dependencies installed")
    
    # Check imports
    import_ok, import_error = check_import()
    if not import_ok:
        print(f"❌ Import error: {import_error}")
        print("\n🔧 To fix, run:")
        print("   python setup_platform.py")
        return False
    else:
        print("✅ Imports working")
    
    # Check environment
    if Path('.env').exists():
        print("✅ Environment file exists")
    else:
        print("⚠️  .env file missing (will use defaults)")
    
    print("\n🎉 Platform is ready!")
    print("\n🚀 Start with:")
    print("   python run_server.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)