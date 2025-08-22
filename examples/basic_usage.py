#!/usr/bin/env python3
"""
Basic usage examples for the AI Agent Workflow framework
"""

import asyncio
import os
from dotenv import load_dotenv

from src.agents import (
    AgentConfig,
    ConversationalAgent,
    ReactiveAgent,
    PlannerAgent
)
from src.tools import (
    CalculatorTool,
    WebSearchTool,
    FileReadTool,
    FileWriteTool
)


async def example_conversational_agent():
    """Example of using a conversational agent"""
    print("\n=== Conversational Agent Example ===")
    
    # Configure the agent
    config = AgentConfig(
        name="Assistant",
        description="A helpful conversational AI assistant",
        model="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=500
    )
    
    # Create the agent
    agent = ConversationalAgent(config)
    
    # Have a conversation
    messages = [
        "Hello! What can you help me with?",
        "Can you explain what machine learning is?",
        "What are some practical applications?"
    ]
    
    for message in messages:
        print(f"\nUser: {message}")
        response = await agent.run(message)
        print(f"Assistant: {response.content}")
    
    # Show conversation history
    print("\n--- Conversation History ---")
    history = agent.get_conversation_history()
    print(f"Total messages: {len(history)}")


async def example_reactive_agent():
    """Example of using a reactive agent with tools"""
    print("\n=== Reactive Agent Example ===")
    
    # Configure the agent
    config = AgentConfig(
        name="ToolUser",
        description="An agent that can use tools to help with tasks",
        model="gpt-3.5-turbo",
        temperature=0.3,
        verbose=True
    )
    
    # Create the agent
    agent = ReactiveAgent(config)
    
    # Add tools
    agent.add_langchain_tool(CalculatorTool())
    agent.add_langchain_tool(WebSearchTool())
    
    # Ask the agent to do calculations
    tasks = [
        "What is the square root of 144 plus 25?",
        "Calculate the compound interest on $1000 at 5% for 10 years",
        "Search for information about the latest AI developments"
    ]
    
    for task in tasks:
        print(f"\nTask: {task}")
        response = await agent.run(task)
        print(f"Result: {response.content}")
        if response.metadata.get("tools_used"):
            print(f"Tools used: {response.metadata['tools_used']}")


async def example_planner_agent():
    """Example of using a planner agent"""
    print("\n=== Planner Agent Example ===")
    
    # Configure the agent
    config = AgentConfig(
        name="Planner",
        description="An agent that creates and executes plans",
        model="gpt-3.5-turbo",
        temperature=0.2
    )
    
    # Create the agent
    agent = PlannerAgent(config)
    
    # Create a plan
    goal = "Build a simple web scraper that collects news headlines"
    print(f"\nGoal: {goal}")
    
    response = await agent.run(goal)
    print(f"\nPlan created:\n{response.content}")
    
    # Execute the plan (simulation)
    if agent.current_plan:
        print("\n--- Executing Plan ---")
        execution_result = await agent.act({"type": "execute_plan"})
        print(f"Execution complete: {execution_result['completed_tasks']}/{execution_result['total_tasks']} tasks completed")


async def example_file_operations():
    """Example of using file operation tools"""
    print("\n=== File Operations Example ===")
    
    # Create a reactive agent with file tools
    config = AgentConfig(
        name="FileManager",
        description="An agent that can read and write files",
        model="gpt-3.5-turbo",
        temperature=0.3
    )
    
    agent = ReactiveAgent(config)
    
    # Add file tools with restricted access to examples directory
    examples_dir = os.path.dirname(os.path.abspath(__file__))
    agent.add_langchain_tool(FileReadTool(base_dir=examples_dir))
    agent.add_langchain_tool(FileWriteTool(base_dir=examples_dir))
    
    # File operations
    tasks = [
        "Write a file called 'test_output.txt' with the content 'Hello from AI Agent!'",
        "Read the contents of the file 'test_output.txt'",
        "Append ' This is additional content.' to the file 'test_output.txt'"
    ]
    
    for task in tasks:
        print(f"\nTask: {task}")
        response = await agent.run(task)
        print(f"Result: {response.content[:200]}...")  # Truncate long outputs


async def main():
    """Run all examples"""
    # Load environment variables
    load_dotenv()
    
    # Check for API keys
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not found in environment variables")
        print("Please set it in your .env file to run these examples")
        return
    
    try:
        # Run examples
        await example_conversational_agent()
        await example_reactive_agent()
        await example_planner_agent()
        await example_file_operations()
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        print("Make sure you have set up your API keys in the .env file")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())