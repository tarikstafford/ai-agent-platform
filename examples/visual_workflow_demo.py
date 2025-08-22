#!/usr/bin/env python3
"""
Demonstration of Visual Workflow Agents using Langflow integration
This shows how to create and use agents built with the visual workflow builder
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from langflow_integration import LangflowServer, WorkflowBuilder, LangflowAgent
    from agents import AgentConfig
    LANGFLOW_AVAILABLE = True
except ImportError as e:
    print(f"Langflow integration not available: {e}")
    LANGFLOW_AVAILABLE = False


async def demo_visual_workflows():
    """Demonstrate visual workflow creation and execution"""
    print("=== Visual Workflow Agent Demo ===\n")
    
    if not LANGFLOW_AVAILABLE:
        print("❌ Langflow integration not available")
        print("To use visual workflows, install Langflow:")
        print("  pip install langflow")
        return
    
    # Initialize workflow builder
    builder = WorkflowBuilder()
    print("🔧 Initializing Langflow server...")
    
    success = await builder.initialize()
    if not success:
        print("❌ Failed to initialize Langflow server")
        print("Make sure you have Langflow installed:")
        print("  pip install langflow")
        return
    
    print("✅ Langflow server initialized")
    print(f"🌐 Visual builder available at: {builder.get_builder_url()}")
    
    # Show available templates
    print(f"\n📋 Available workflow templates:")
    templates = builder.get_workflow_templates()
    
    for name, template in templates.items():
        print(f"  • {template['name']}: {template['description']}")
    
    # Create a simple chat workflow from template
    print(f"\n🎨 Creating simple chat workflow...")
    flow_id = builder.create_from_template("simple_chat", "demo_chat_agent")
    
    if not flow_id:
        print("❌ Failed to create workflow")
        return
    
    print(f"✅ Workflow created with ID: {flow_id}")
    
    # Create an agent from the workflow
    print(f"\n🤖 Creating agent from visual workflow...")
    
    config = AgentConfig(
        name="VisualChatAgent",
        description="Agent created from visual workflow",
        model="langflow-workflow",
        temperature=0.7,
        max_tokens=1000
    )
    
    # Create LangflowAgent
    agent = LangflowAgent(config, flow_id=flow_id)
    
    print(f"✅ Visual workflow agent created")
    
    # Test the agent
    print(f"\n💬 Testing visual workflow agent...")
    
    test_messages = [
        "Hello! How are you?",
        "Can you tell me about artificial intelligence?",
        "What can you help me with?"
    ]
    
    for message in test_messages:
        print(f"\n👤 User: {message}")
        
        try:
            response = await agent.run(message)
            
            if response.success:
                print(f"🤖 Agent: {response.content}")
                print(f"   ⏱️  Response time: {response.metadata.get('duration', 'N/A')}")
            else:
                print(f"❌ Error: {response.error}")
        
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
    
    # Show workflow summary
    print(f"\n📊 Workflow Agent Summary:")
    summary = agent.get_workflow_summary()
    
    for key, value in summary.items():
        print(f"  • {key}: {value}")
    
    # Demonstrate workflow testing
    print(f"\n🧪 Testing workflow directly...")
    
    test_result = await builder.test_workflow(flow_id, {
        "input": "Test message for workflow"
    })
    
    if test_result["success"]:
        print(f"✅ Workflow test successful")
        print(f"   Result: {test_result['result']}")
    else:
        print(f"❌ Workflow test failed: {test_result.get('error')}")
    
    # Show component information
    print(f"\n🧩 Available workflow components:")
    components = builder.get_available_components()
    
    for category, items in components.items():
        print(f"  📦 {category.title()}:")
        for item in items[:2]:  # Show first 2 items per category
            print(f"    • {item['name']}: {item['description']}")
    
    print(f"\n🎯 Visual Workflow Features:")
    print("✅ Drag-and-drop workflow creation")
    print("✅ Pre-built component library")
    print("✅ Multiple workflow templates")
    print("✅ Visual debugging and testing")
    print("✅ Export/import workflow definitions")
    print("✅ Integration with existing agent platform")
    
    print(f"\n🌐 Next steps:")
    print("1. Open the visual builder in your browser:")
    print(f"   {builder.get_builder_url()}")
    print("2. Create custom workflows using drag-and-drop")
    print("3. Test workflows with sample inputs")
    print("4. Create agents from your visual workflows")
    print("5. Deploy and manage through the dashboard")


async def demo_workflow_management():
    """Demonstrate workflow management features"""
    print(f"\n=== Workflow Management Demo ===")
    
    if not LANGFLOW_AVAILABLE:
        return
    
    builder = WorkflowBuilder()
    await builder.initialize()
    
    # Create multiple workflows
    print(f"\n📝 Creating multiple workflow examples...")
    
    workflow_configs = [
        ("simple_chat", "customer_support", "Customer Support Bot"),
        ("rag_agent", "knowledge_base", "Knowledge Base Assistant"),
        ("tool_agent", "task_helper", "Task Helper Agent")
    ]
    
    created_workflows = []
    
    for template, name, description in workflow_configs:
        print(f"   Creating: {description}")
        flow_id = builder.create_from_template(template, name)
        
        if flow_id:
            created_workflows.append({
                "id": flow_id,
                "name": name,
                "description": description
            })
            print(f"   ✅ Created workflow: {name} ({flow_id})")
        else:
            print(f"   ❌ Failed to create: {name}")
    
    # List all workflows
    print(f"\n📋 Available workflows:")
    flows = builder.langflow_server.get_flows()
    
    for flow in flows.get("flows", []):
        print(f"   • {flow.get('name', 'Unnamed')} - {flow.get('id', 'No ID')}")
    
    # Test workflow validation
    print(f"\n🔍 Workflow validation example:")
    
    # Create a sample workflow for validation
    sample_workflow = {
        "name": "Test Workflow",
        "description": "Sample for validation",
        "nodes": [
            {"id": "input", "type": "TextInput"},
            {"id": "llm", "type": "OpenAI"},
            {"id": "output", "type": "TextOutput"}
        ],
        "edges": [
            {"source": "input", "target": "llm"},
            {"source": "llm", "target": "output"}
        ]
    }
    
    validation = builder.validate_workflow(sample_workflow)
    print(f"   Validation result: {'✅ Valid' if validation['valid'] else '❌ Invalid'}")
    
    if validation["errors"]:
        print("   Errors:")
        for error in validation["errors"]:
            print(f"     • {error}")
    
    if validation["warnings"]:
        print("   Warnings:")
        for warning in validation["warnings"]:
            print(f"     • {warning}")
    
    print(f"\n🔄 Workflow management completed")


async def main():
    """Main demo function"""
    try:
        print("🚀 Starting Visual Workflow Demo\n")
        
        await demo_visual_workflows()
        await demo_workflow_management()
        
        print(f"\n✅ Demo completed successfully!")
        print(f"\nTo explore visual workflows:")
        print("1. Start the platform: python run_server.py")
        print("2. Open dashboard: http://127.0.0.1:8000/api/dashboard/ui")
        print("3. Select 'Visual Workflow' agent type")
        print("4. Click 'Open Visual Builder'")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())