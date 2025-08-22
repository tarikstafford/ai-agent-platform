#!/usr/bin/env python3
"""
Demonstration of the AI Agent Platform hosting capabilities
This shows how to create, manage, and interact with hosted agents
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hosting import AgentManager
from agents import AgentConfig


async def demo_agent_platform():
    """Demonstrate the agent hosting platform"""
    print("=== AI Agent Platform Demo ===\n")
    
    # Create agent manager
    manager = AgentManager()
    
    print("1. Creating different types of agents...")
    
    # Create a conversational agent
    conv_config = {
        "name": "ChatBot",
        "description": "A friendly conversational AI",
        "model": "gpt-3.5-turbo",
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    conv_agent_id = await manager.create_agent(
        agent_type="conversational",
        config=conv_config,
        name="Friendly ChatBot",
        description="A conversational agent for customer support",
        tags=["chatbot", "support"],
        auto_start=True
    )
    print(f"✅ Created conversational agent: {conv_agent_id}")
    
    # Create a reactive agent with tools
    reactive_config = {
        "name": "TaskBot",
        "description": "An agent that can use tools",
        "model": "gpt-3.5-turbo",
        "temperature": 0.3,
        "max_tokens": 1000
    }
    
    reactive_agent_id = await manager.create_agent(
        agent_type="reactive",
        config=reactive_config,
        tools=["calculator", "web_search"],
        name="Task Assistant",
        description="An agent that can calculate and search",
        tags=["tools", "assistant"],
        auto_start=True
    )
    print(f"✅ Created reactive agent: {reactive_agent_id}")
    
    # Create a planner agent
    planner_config = {
        "name": "PlannerBot",
        "description": "An agent that creates execution plans",
        "model": "gpt-3.5-turbo",
        "temperature": 0.2,
        "max_tokens": 2000
    }
    
    planner_agent_id = await manager.create_agent(
        agent_type="planner",
        config=planner_config,
        name="Strategic Planner",
        description="An agent for project planning and task breakdown",
        tags=["planning", "strategy"],
        auto_start=True
    )
    print(f"✅ Created planner agent: {planner_agent_id}")
    
    print(f"\n2. Platform overview:")
    print("-" * 50)
    
    # Show platform statistics
    dashboard_data = manager.get_dashboard_data()
    overview = dashboard_data["overview"]
    
    print(f"Total agents: {overview['total_agents']}")
    print(f"Running agents: {overview['running_agents']}")
    print(f"Available agent types: {', '.join(dashboard_data['available_types'])}")
    print(f"Available tools: {', '.join(dashboard_data['available_tools'])}")
    
    print(f"\n3. Agent details:")
    print("-" * 50)
    
    # Show agent information
    for agent in dashboard_data["agents"]:
        print(f"Agent: {agent['name']} ({agent['id'][:8]}...)")
        print(f"  Status: {agent['status']}")
        print(f"  Type: {agent['config']['model']}")
        print(f"  Created: {agent['created_at']}")
        print()
    
    print("4. Testing agent interactions...")
    print("-" * 50)
    
    # Test conversational agent
    print("🗣️  Testing conversational agent:")
    conv_response = await manager.chat_with_agent(
        conv_agent_id, 
        "Hello! Can you introduce yourself?"
    )
    if conv_response["success"]:
        print(f"Response: {conv_response['content'][:100]}...")
    else:
        print(f"Error: {conv_response['error']}")
    
    # Test reactive agent with calculator
    print("\n🔧 Testing reactive agent with calculator:")
    calc_response = await manager.chat_with_agent(
        reactive_agent_id,
        "What is the square root of 144 plus 25?"
    )
    if calc_response["success"]:
        print(f"Response: {calc_response['content'][:100]}...")
    else:
        print(f"Error: {calc_response['error']}")
    
    # Test planner agent
    print("\n📋 Testing planner agent:")
    plan_response = await manager.chat_with_agent(
        planner_agent_id,
        "Create a plan for building a simple todo app"
    )
    if plan_response["success"]:
        print(f"Response: {plan_response['content'][:200]}...")
    else:
        print(f"Error: {plan_response['error']}")
    
    print(f"\n5. Updated platform statistics:")
    print("-" * 50)
    
    # Show updated statistics after interactions
    dashboard_data = manager.get_dashboard_data()
    overview = dashboard_data["overview"]
    
    print(f"Total requests processed: {overview['total_requests']}")
    print(f"Success rate: {overview['success_rate']:.1%}")
    print(f"Average response time: {overview['average_response_time']:.2f}s")
    
    print(f"\n6. Agent control demonstration:")
    print("-" * 50)
    
    # Demonstrate stopping and starting agents
    print(f"Stopping conversational agent...")
    await manager.stop_agent(conv_agent_id)
    
    # Show updated status
    agent_info = manager.get_agent_info(conv_agent_id)
    print(f"Agent status: {agent_info['status']}")
    
    print(f"Starting agent again...")
    await manager.start_agent(conv_agent_id)
    
    agent_info = manager.get_agent_info(conv_agent_id)
    print(f"Agent status: {agent_info['status']}")
    
    print(f"\n7. Platform hosting features:")
    print("-" * 50)
    print("✅ Agent registry and lifecycle management")
    print("✅ Multiple agent types (Conversational, Reactive, Planner)")
    print("✅ Tool integration for reactive agents")
    print("✅ Real-time metrics and monitoring")
    print("✅ Agent persistence and configuration")
    print("✅ REST API for external integration")
    print("✅ Web dashboard for management")
    
    print(f"\n8. Cleanup:")
    print("-" * 50)
    
    # Clean up agents
    print("Removing demo agents...")
    await manager.remove_agent(conv_agent_id)
    await manager.remove_agent(reactive_agent_id)
    await manager.remove_agent(planner_agent_id)
    
    print("✅ Demo completed successfully!")
    
    print(f"\nTo start the web platform:")
    print("  python run_server.py --host 127.0.0.1 --port 8000")
    print("  Then visit: http://127.0.0.1:8000/api/dashboard/ui")


async def main():
    """Main demo function"""
    try:
        # Check for API keys
        if not os.getenv("OPENAI_API_KEY"):
            print("⚠️  Warning: OPENAI_API_KEY not found")
            print("Set your API key in .env file for full functionality")
            print()
        
        await demo_agent_platform()
        
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())