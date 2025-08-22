#!/bin/bash

echo "=== AI Agent Workflow Framework Installation ==="
echo

# Check Python version
python_cmd=""
if command -v python3 &> /dev/null; then
    python_cmd="python3"
elif command -v python &> /dev/null; then
    python_cmd="python"
else
    echo "Error: Python not found. Please install Python 3.9 or higher."
    exit 1
fi

echo "Using Python: $python_cmd"
$python_cmd --version
echo

# Create virtual environment
echo "Creating virtual environment..."
$python_cmd -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install package with dev dependencies
echo "Installing package with development dependencies..."
pip install -e ".[dev]"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env and add your API keys"
fi

# Install pre-commit hooks
echo "Setting up pre-commit hooks..."
pre-commit install

echo
echo "✅ Installation complete!"
echo
echo "Next steps:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate  # On Windows: venv\\Scripts\\activate"
echo "2. Add your API keys to .env file"
echo "3. Run the quickstart:"
echo "   python quickstart.py"
echo "4. Explore the examples:"
echo "   python examples/basic_usage.py"