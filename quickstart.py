#!/usr/bin/env python3
"""
Quick start script for the AI Agent Workflow framework
Run this to verify your installation and see basic capabilities
"""

import asyncio
import os
import sys

try:
    from dotenv import load_dotenv
except ImportError:
    print("Dependencies not installed. Please run:")
    print("  pip install -e .")
    print("or")
    print("  pip install -e .[dev]")
    sys.exit(1)

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from agents import AgentConfig, ConversationalAgent, ReactiveAgent
    from tools import CalculatorTool
except ImportError as e:
    print(f"Import error: {e}")
    print("\nDependencies not installed. Please run:")
    print("  pip install -e .")
    print("or")
    print("  pip install -e .[dev]")
    sys.exit(1)


async def main():
    """Quick start demonstration"""
    print("=== AI Agent Workflow Framework Quick Start ===\n")
    
    # Load environment
    load_dotenv()
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not found in environment")
        print("   You can still explore the framework, but LLM features won't work.")
        print("   To use LLM features:")
        print("   1. Copy .env.example to .env")
        print("   2. Add your OpenAI API key")
        print()
    
    print("1. Testing Calculator Tool (no API key required):")
    print("-" * 50)
    
    # Test calculator tool
    calc = CalculatorTool()
    expressions = ["2 + 2", "sqrt(16)", "pi * 2"]
    
    for expr in expressions:
        result = calc.execute(expr)
        print(f"   {result}")
    
    print("\n2. Agent Framework Structure:")
    print("-" * 50)
    print("   Available Agents:")
    print("   - ConversationalAgent: For dialogue and chat")
    print("   - ReactiveAgent: For using tools to solve problems")
    print("   - PlannerAgent: For breaking down complex tasks")
    
    print("\n   Available Tools:")
    print("   - CalculatorTool: Mathematical calculations")
    print("   - WebSearchTool: Search the web")
    print("   - FileReadTool/FileWriteTool: File operations")
    print("   - APICallerTool: Make HTTP requests")
    
    print("\n3. Example Usage:")
    print("-" * 50)
    print("   See examples/basic_usage.py for complete examples")
    print("   See examples/research_assistant.py for advanced usage")
    
    # If API key exists, show a simple demo
    if os.getenv("OPENAI_API_KEY"):
        print("\n4. Live Demo (API key detected):")
        print("-" * 50)
        
        try:
            # Create a simple agent
            config = AgentConfig(
                name="QuickStart",
                description="Quick start demo agent",
                model="gpt-3.5-turbo",
                max_tokens=150
            )
            
            agent = ConversationalAgent(config)
            response = await agent.run("Say hello and introduce yourself in one sentence.")
            print(f"   Agent: {response.content}")
            
        except Exception as e:
            print(f"   Error: {e}")
            print("   Make sure your API key is valid and you have internet connection.")
    
    print("\n✅ Framework is ready to use!")
    print("\nNext steps:")
    print("- Run examples: python examples/basic_usage.py")
    print("- Run tests: pytest tests/")
    print("- Read documentation: README.md")


if __name__ == "__main__":
    asyncio.run(main())