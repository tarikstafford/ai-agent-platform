#!/usr/bin/env python3
"""
Advanced example: Research Assistant Agent

This example demonstrates how to build a research assistant that can:
1. Search for information on a topic
2. Analyze and summarize findings
3. Save results to files
4. Create a structured report
"""

import asyncio
import os
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

from src.agents import AgentConfig, BaseAgent, AgentResponse, AgentState
from src.agents import ReactiveAgent, PlannerAgent
from src.tools import (
    WebSearchTool,
    FileWriteTool,
    FileReadTool,
    APICallerTool
)


class ResearchAssistant(BaseAgent):
    """A specialized agent for conducting research on topics"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.research_agent = self._create_research_agent()
        self.planner_agent = self._create_planner_agent()
        self.research_data: List[Dict[str, Any]] = []
        
    def _create_research_agent(self) -> ReactiveAgent:
        """Create a reactive agent with research tools"""
        config = AgentConfig(
            name="ResearchBot",
            description="Agent for gathering research data",
            model=self.config.model,
            temperature=0.3,
            verbose=self.config.verbose
        )
        
        agent = ReactiveAgent(config)
        
        # Add research tools
        agent.add_langchain_tool(WebSearchTool())
        agent.add_langchain_tool(FileWriteTool(base_dir="./research_output"))
        agent.add_langchain_tool(FileReadTool(base_dir="./research_output"))
        
        # Add API caller for accessing public APIs
        agent.add_langchain_tool(APICallerTool())
        
        return agent
    
    def _create_planner_agent(self) -> PlannerAgent:
        """Create a planner agent for research planning"""
        config = AgentConfig(
            name="ResearchPlanner",
            description="Agent for planning research tasks",
            model=self.config.model,
            temperature=0.2
        )
        return PlannerAgent(config)
    
    async def think(self, input_data: Any) -> AgentResponse:
        """Process research request"""
        try:
            if isinstance(input_data, dict):
                topic = input_data.get("topic", "")
                depth = input_data.get("depth", "basic")  # basic, intermediate, comprehensive
                output_format = input_data.get("format", "markdown")
            else:
                topic = str(input_data)
                depth = "basic"
                output_format = "markdown"
            
            self.logger.info("Starting research", topic=topic, depth=depth)
            
            # Step 1: Create research plan
            plan_response = await self.planner_agent.think({
                "goal": f"Research the topic '{topic}' with {depth} depth analysis"
            })
            
            if not plan_response.success:
                return plan_response
            
            # Step 2: Execute research tasks
            research_tasks = self._extract_research_tasks(topic, depth)
            
            for task in research_tasks:
                self.logger.info("Executing research task", task=task)
                result = await self.research_agent.run(task)
                
                if result.success:
                    self.research_data.append({
                        "task": task,
                        "result": result.content,
                        "timestamp": datetime.now()
                    })
            
            # Step 3: Generate report
            report = self._generate_report(topic, output_format)
            
            # Step 4: Save report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"research_{topic.replace(' ', '_')}_{timestamp}.md"
            
            save_result = await self.research_agent.run({
                "task": f"Save the following research report to '{filename}':\n\n{report}"
            })
            
            return AgentResponse(
                content=report,
                success=True,
                metadata={
                    "topic": topic,
                    "depth": depth,
                    "tasks_completed": len(self.research_data),
                    "report_file": filename,
                    "save_status": save_result.success
                }
            )
            
        except Exception as e:
            self.logger.error("Research error", error=str(e))
            return AgentResponse(
                content=f"Research failed: {str(e)}",
                success=False,
                error=str(e),
                state=AgentState.ERROR
            )
    
    async def act(self, action: Dict[str, Any]) -> Any:
        """Execute research actions"""
        action_type = action.get("type")
        
        if action_type == "search_more":
            query = action.get("query")
            return await self.research_agent.run(f"Search for more information about: {query}")
        
        elif action_type == "get_research_data":
            return {"data": self.research_data}
        
        elif action_type == "clear_research":
            self.research_data.clear()
            return {"status": "Research data cleared"}
        
        return {"error": f"Unknown action type: {action_type}"}
    
    def _extract_research_tasks(self, topic: str, depth: str) -> List[str]:
        """Generate research tasks based on topic and depth"""
        base_tasks = [
            f"Search for general information about {topic}",
            f"Find recent developments and news about {topic}",
        ]
        
        if depth in ["intermediate", "comprehensive"]:
            base_tasks.extend([
                f"Search for expert opinions and analysis on {topic}",
                f"Find statistics and data related to {topic}",
            ])
        
        if depth == "comprehensive":
            base_tasks.extend([
                f"Search for academic papers and research on {topic}",
                f"Find case studies and real-world applications of {topic}",
                f"Search for future predictions and trends about {topic}",
            ])
        
        return base_tasks
    
    def _generate_report(self, topic: str, format: str) -> str:
        """Generate a research report from collected data"""
        report_lines = [
            f"# Research Report: {topic}",
            f"\n**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n## Executive Summary\n",
            f"This report presents research findings on the topic of '{topic}'.",
            f"A total of {len(self.research_data)} research tasks were completed.\n",
            "## Research Findings\n"
        ]
        
        for i, data in enumerate(self.research_data, 1):
            report_lines.extend([
                f"### Finding {i}: {data['task']}",
                f"\n{data['result']}\n",
                "---\n"
            ])
        
        report_lines.extend([
            "## Conclusion\n",
            f"This research provides comprehensive insights into {topic}. ",
            "The findings above represent data gathered from multiple sources ",
            "and should be verified for accuracy in critical applications.\n",
            "\n---",
            "\n*Report generated by AI Research Assistant*"
        ])
        
        return "\n".join(report_lines)


async def example_research_session():
    """Run an example research session"""
    print("\n=== Research Assistant Example ===")
    
    # Create output directory
    os.makedirs("research_output", exist_ok=True)
    
    # Configure research assistant
    config = AgentConfig(
        name="ResearchAssistant",
        description="An AI-powered research assistant",
        model="gpt-3.5-turbo",
        temperature=0.5,
        max_tokens=2000,
        verbose=True
    )
    
    assistant = ResearchAssistant(config)
    
    # Research topics with different depths
    research_requests = [
        {
            "topic": "Quantum Computing Applications",
            "depth": "basic",
            "format": "markdown"
        },
        {
            "topic": "Climate Change Solutions",
            "depth": "intermediate",
            "format": "markdown"
        }
    ]
    
    for request in research_requests:
        print(f"\n--- Researching: {request['topic']} (Depth: {request['depth']}) ---")
        
        response = await assistant.run(request)
        
        if response.success:
            print(f"\nResearch completed successfully!")
            print(f"Report saved to: {response.metadata.get('report_file')}")
            print(f"Tasks completed: {response.metadata.get('tasks_completed')}")
            
            # Show a preview of the report
            preview_lines = response.content.split('\n')[:20]
            print("\n--- Report Preview ---")
            print('\n'.join(preview_lines))
            print("...\n[Report continues]")
        else:
            print(f"Research failed: {response.error}")


async def main():
    """Run the research assistant example"""
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in environment variables")
        return
    
    try:
        await example_research_session()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())