#!/usr/bin/env python3
"""
A2A Communication Demo

This example demonstrates Agent-to-Agent communication capabilities,
including task delegation, collaboration, and agent discovery.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents import ConversationalAgent, ReactiveAgent, AgentConfig
from a2a.protocol import AgentCapability
from tools import CalculatorTool, WebSearchTool
import structlog

logger = structlog.get_logger()


async def create_demo_agents():
    """Create a set of demo agents with different capabilities"""
    
    # Agent 1: Math Specialist
    math_config = AgentConfig(
        name="MathBot",
        description="Specialized in mathematical calculations",
        model="gpt-3.5-turbo",
        a2a_enabled=True,
        a2a_capabilities=["calculation", "analysis", "problem_solving"]
    )
    
    math_agent = ReactiveAgent(math_config, agent_id="math_bot_001")
    math_agent.add_langchain_tool(CalculatorTool())
    
    # Register task handlers
    async def handle_calculation(task_data):
        expression = task_data.get("expression", "")
        if not expression:
            raise ValueError("No expression provided")
        
        # Use the calculator tool
        calc_tool = CalculatorTool()
        result = calc_tool.execute(expression)
        return {"result": result, "expression": expression}
    
    math_agent.register_task_handler("calculation", handle_calculation)
    
    # Agent 2: Research Specialist
    research_config = AgentConfig(
        name="ResearchBot",
        description="Specialized in web research and information gathering",
        model="gpt-3.5-turbo",
        a2a_enabled=True,
        a2a_capabilities=["web_search", "research", "information_gathering"]
    )
    
    research_agent = ReactiveAgent(research_config, agent_id="research_bot_001")
    research_agent.add_langchain_tool(WebSearchTool())
    
    # Register task handlers
    async def handle_research(task_data):
        query = task_data.get("query", "")
        if not query:
            raise ValueError("No search query provided")
        
        # Use the web search tool
        search_tool = WebSearchTool()
        results = search_tool.execute(query)
        return {"results": results, "query": query}
    
    research_agent.register_task_handler("research", handle_research)
    
    # Agent 3: Coordinator Agent
    coordinator_config = AgentConfig(
        name="CoordinatorBot",
        description="Coordinates tasks between different specialized agents",
        model="gpt-4",
        a2a_enabled=True,
        a2a_capabilities=["coordination", "planning", "task_management"]
    )
    
    coordinator_agent = ConversationalAgent(coordinator_config, agent_id="coordinator_001")
    
    # Register task handlers
    async def handle_coordination(task_data):
        task_description = task_data.get("task_description", "")
        return {"status": "coordinating", "task": task_description}
    
    coordinator_agent.register_task_handler("coordination", handle_coordination)
    
    return {
        "math_agent": math_agent,
        "research_agent": research_agent,
        "coordinator_agent": coordinator_agent
    }


async def demo_agent_discovery(agents):
    """Demonstrate agent discovery capabilities"""
    print("\n=== Agent Discovery Demo ===")
    
    coordinator = agents["coordinator_agent"]
    
    # Start A2A communication for all agents
    for name, agent in agents.items():
        await agent.start_a2a_communication()
        print(f"✅ Started A2A communication for {name}")
    
    # Wait a moment for discovery to happen
    await asyncio.sleep(2)
    
    # Discover agents with calculation capability
    print(f"\n🔍 Discovering agents with 'calculation' capability...")
    calc_agents = await coordinator.discover_agents(["calculation"])
    
    for agent_info in calc_agents:
        print(f"  • Found: {agent_info['name']} - {agent_info['capabilities']}")
    
    # Discover all agents
    print(f"\n🔍 Discovering all available agents...")
    all_agents = await coordinator.discover_agents()
    
    for agent_info in all_agents:
        print(f"  • {agent_info['name']}: {agent_info['status']} - {agent_info['capabilities']}")
    
    return calc_agents, all_agents


async def demo_task_delegation(agents):
    """Demonstrate task delegation between agents"""
    print("\n=== Task Delegation Demo ===")
    
    coordinator = agents["coordinator_agent"]
    math_agent = agents["math_agent"]
    
    # Delegate calculation task
    print(f"\n📊 Delegating calculation task...")
    
    success = await coordinator.delegate_task_to_agent(
        agent_id=math_agent.agent_id,
        task_type="calculation",
        task_data={"expression": "15 * 7 + 25"}
    )
    
    if success:
        print("✅ Task delegation successful!")
    else:
        print("❌ Task delegation failed!")
    
    # Wait for task completion
    await asyncio.sleep(3)
    
    # Delegate research task
    research_agent = agents["research_agent"]
    
    print(f"\n🔍 Delegating research task...")
    
    success = await coordinator.delegate_task_to_agent(
        agent_id=research_agent.agent_id,
        task_type="research",
        task_data={"query": "latest developments in artificial intelligence"}
    )
    
    if success:
        print("✅ Research task delegation successful!")
    else:
        print("❌ Research task delegation failed!")


async def demo_collaboration(agents):
    """Demonstrate multi-agent collaboration"""
    print("\n=== Multi-Agent Collaboration Demo ===")
    
    coordinator = agents["coordinator_agent"]
    
    # Initiate collaboration
    print(f"\n🤝 Initiating collaboration...")
    
    participant_ids = [
        agents["math_agent"].agent_id,
        agents["research_agent"].agent_id
    ]
    
    collaboration_id = await coordinator.collaborate_with_agents(
        agent_ids=participant_ids,
        collaboration_title="Mathematical Research Project",
        collaboration_description="Combine mathematical analysis with research capabilities"
    )
    
    print(f"✅ Collaboration initiated with ID: {collaboration_id}")
    
    # Wait for agents to join
    await asyncio.sleep(2)
    
    print("📋 Collaboration participants should receive join requests...")


async def demo_direct_messaging(agents):
    """Demonstrate direct messaging between agents"""
    print("\n=== Direct Messaging Demo ===")
    
    math_agent = agents["math_agent"]
    research_agent = agents["research_agent"]
    
    # Send information request
    print(f"\n💬 Sending info request from Math agent to Research agent...")
    
    message_id = await math_agent.send_message_to_agent(
        recipient_id=research_agent.agent_id,
        message_type="info_request",
        payload={"requested_info": "available_capabilities"}
    )
    
    print(f"✅ Message sent with ID: {message_id}")
    
    # Send status request
    print(f"\n📊 Requesting status from Research agent...")
    
    message_id = await math_agent.send_message_to_agent(
        recipient_id=research_agent.agent_id,
        message_type="status_request",
        payload={}
    )
    
    print(f"✅ Status request sent with ID: {message_id}")


async def demo_ping_agents(agents):
    """Demonstrate pinging agents to check availability"""
    print("\n=== Agent Ping Demo ===")
    
    coordinator = agents["coordinator_agent"]
    
    for name, agent in agents.items():
        if agent != coordinator:
            print(f"\n🏓 Pinging {name}...")
            
            if hasattr(coordinator, 'a2a_communicator') and coordinator.a2a_communicator:
                success = await coordinator.a2a_communicator.ping_agent(agent.agent_id, timeout=5)
                
                if success:
                    print(f"✅ {name} is responsive")
                else:
                    print(f"❌ {name} is not responsive")
            else:
                print(f"❌ A2A communicator not available")


async def demo_complex_workflow(agents):
    """Demonstrate a complex workflow involving multiple agents"""
    print("\n=== Complex Multi-Agent Workflow Demo ===")
    
    coordinator = agents["coordinator_agent"]
    math_agent = agents["math_agent"]
    research_agent = agents["research_agent"]
    
    print(f"\n🎯 Complex Workflow: Research + Mathematical Analysis")
    print("  1. Research agent finds information about AI performance metrics")
    print("  2. Math agent calculates statistical analysis")
    print("  3. Coordinator synthesizes results")
    
    # Step 1: Research task
    print(f"\n📚 Step 1: Research Phase...")
    research_success = await coordinator.delegate_task_to_agent(
        agent_id=research_agent.agent_id,
        task_type="research",
        task_data={
            "query": "machine learning model accuracy metrics 2024",
            "focus": "statistical_performance"
        }
    )
    
    if research_success:
        print("✅ Research task delegated")
    
    # Wait for research to complete
    await asyncio.sleep(3)
    
    # Step 2: Mathematical analysis
    print(f"\n🔢 Step 2: Mathematical Analysis...")
    math_success = await coordinator.delegate_task_to_agent(
        agent_id=math_agent.agent_id,
        task_type="calculation",
        task_data={
            "expression": "(95.2 + 87.8 + 92.1 + 89.4) / 4",  # Average accuracy calculation
            "description": "Calculate average accuracy from research data"
        }
    )
    
    if math_success:
        print("✅ Mathematical analysis task delegated")
    
    # Wait for calculation to complete
    await asyncio.sleep(2)
    
    # Step 3: Coordination summary
    print(f"\n📋 Step 3: Coordinator Summary...")
    coordination_result = await coordinator.run(
        "Based on the research and mathematical analysis performed by specialist agents, "
        "provide a summary of AI model performance insights."
    )
    
    print(f"🎯 Coordinator Summary: {coordination_result.content[:200]}...")


async def display_agent_stats(agents):
    """Display communication statistics for all agents"""
    print("\n=== Agent Communication Statistics ===")
    
    for name, agent in agents.items():
        print(f"\n📊 {name} Statistics:")
        
        if hasattr(agent, 'a2a_communicator') and agent.a2a_communicator:
            stats = agent.a2a_communicator.get_stats()
            
            print(f"  Messages Sent: {stats.get('messages_sent', 0)}")
            print(f"  Messages Received: {stats.get('messages_received', 0)}")
            print(f"  Known Agents: {stats.get('known_agents', 0)}")
            print(f"  Pending Deliveries: {stats.get('pending_deliveries', 0)}")
            print(f"  Pending Responses: {stats.get('pending_responses', 0)}")
        else:
            print("  A2A communication not available")
        
        # Task management stats
        if hasattr(agent, 'task_manager') and agent.task_manager:
            task_stats = agent.task_manager.get_task_stats()
            print(f"  Active Tasks: {task_stats.get('active_tasks', 0)}")
            print(f"  Success Rate: {task_stats.get('success_rate', 0):.1%}")
        
        # Discovery stats
        if hasattr(agent, 'a2a_discovery') and agent.a2a_discovery:
            discovered = agent.a2a_discovery.get_all_discovered_agents()
            print(f"  Discovered Agents: {len(discovered)}")


async def main():
    """Main demo function"""
    print("🚀 Starting A2A Communication Demo")
    print("="*50)
    
    agents = {}  # Initialize agents dictionary
    
    try:
        # Create demo agents
        print("\n👥 Creating demo agents...")
        agents = await create_demo_agents()
        
        for name, agent in agents.items():
            print(f"  ✅ Created {name}: {agent.config.name}")
        
        # Run demos
        await demo_agent_discovery(agents)
        await demo_ping_agents(agents)
        await demo_direct_messaging(agents)
        await demo_task_delegation(agents)
        await demo_collaboration(agents)
        await demo_complex_workflow(agents)
        
        # Display final statistics
        await display_agent_stats(agents)
        
        print(f"\n✅ A2A Communication Demo Completed Successfully!")
        print("\n🎯 Key Features Demonstrated:")
        print("  • Agent Discovery and Capability Matching")
        print("  • Direct Agent-to-Agent Messaging")
        print("  • Task Delegation and Execution")
        print("  • Multi-Agent Collaboration")
        print("  • Complex Multi-Step Workflows")
        print("  • Real-time Agent Status Monitoring")
        
        print(f"\n🌐 Access the A2A Dashboard:")
        print("  1. Start the platform: python run_server.py")
        print("  2. Open A2A dashboard: http://127.0.0.1:8000/api/dashboard/a2a")
        print("  3. Monitor agent communications in real-time")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up...")
        try:
            if agents:  # Check if agents dictionary is populated
                for name, agent in agents.items():
                    if hasattr(agent, 'stop_a2a_communication'):
                        await agent.stop_a2a_communication()
                        print(f"  ✅ Stopped A2A communication for {name}")
        except Exception as e:
            print(f"  ⚠️  Cleanup warning: {e}")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())