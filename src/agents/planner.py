from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from .base import BaseAgent, AgentConfig, AgentResponse, AgentState


class TaskStatus(str, Enum):
    """Status of a task in the plan"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class Task(BaseModel):
    """A single task in a plan"""
    id: int = Field(..., description="Unique task ID")
    name: str = Field(..., description="Task name")
    description: str = Field(..., description="Detailed task description")
    dependencies: List[int] = Field(default_factory=list, description="IDs of tasks this depends on")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current task status")
    result: Optional[str] = Field(None, description="Result of completed task")


class Plan(BaseModel):
    """A plan consisting of multiple tasks"""
    goal: str = Field(..., description="Overall goal of the plan")
    tasks: List[Task] = Field(..., description="List of tasks to accomplish the goal")
    
    def get_ready_tasks(self) -> List[Task]:
        """Get tasks that are ready to execute (no pending dependencies)"""
        completed_ids = {t.id for t in self.tasks if t.status == TaskStatus.COMPLETED}
        ready_tasks = []
        
        for task in self.tasks:
            if task.status == TaskStatus.PENDING:
                if all(dep_id in completed_ids for dep_id in task.dependencies):
                    ready_tasks.append(task)
        
        return ready_tasks


class PlannerAgent(BaseAgent):
    """An agent that creates and executes plans to accomplish complex goals"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.current_plan: Optional[Plan] = None
        self.execution_agents: Dict[str, BaseAgent] = {}
        
    async def think(self, input_data: Union[str, Dict[str, Any]]) -> AgentResponse:
        """Create a plan for the given goal"""
        try:
            # Extract goal
            if isinstance(input_data, dict):
                goal = input_data.get("goal", str(input_data))
            else:
                goal = str(input_data)
            
            # Create plan
            self.logger.info("Creating plan", goal=goal)
            plan = await self._create_plan(goal)
            self.current_plan = plan
            
            # Format plan as string
            plan_str = self._format_plan(plan)
            
            return AgentResponse(
                content=plan_str,
                success=True,
                metadata={
                    "goal": goal,
                    "task_count": len(plan.tasks),
                    "plan": plan.model_dump()
                }
            )
            
        except Exception as e:
            self.logger.error("Error creating plan", error=str(e))
            return AgentResponse(
                content=f"Failed to create plan: {str(e)}",
                success=False,
                error=str(e),
                state=AgentState.ERROR
            )
    
    async def act(self, action: Dict[str, Any]) -> Any:
        """Execute the current plan or a specific task"""
        action_type = action.get("type", "execute_plan")
        
        if action_type == "execute_plan":
            return await self._execute_plan()
        elif action_type == "execute_task":
            task_id = action.get("task_id")
            return await self._execute_task(task_id)
        else:
            return {"error": f"Unknown action type: {action_type}"}
    
    async def _create_plan(self, goal: str) -> Plan:
        """Create a plan using LLM"""
        # Create output parser
        parser = PydanticOutputParser(pydantic_object=Plan)
        
        # Create prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are a planning agent that breaks down complex goals into actionable tasks.
Create a detailed plan with specific tasks that can be executed to achieve the goal.
Each task should be clear and actionable. Identify dependencies between tasks.

{parser.get_format_instructions()}"""),
            ("user", "Create a plan for the following goal: {goal}")
        ])
        
        # Create LLM
        llm = ChatOpenAI(
            model=self.config.model,
            temperature=0.3,  # Lower temperature for more structured output
            max_tokens=self.config.max_tokens,
        )
        
        # Generate plan
        chain = prompt | llm | parser
        plan = await chain.ainvoke({"goal": goal})
        
        return plan
    
    async def _execute_plan(self) -> Dict[str, Any]:
        """Execute all tasks in the current plan"""
        if not self.current_plan:
            return {"error": "No plan to execute"}
        
        results = []
        max_iterations = self.config.max_iterations
        iteration = 0
        
        while iteration < max_iterations:
            # Get ready tasks
            ready_tasks = self.current_plan.get_ready_tasks()
            
            if not ready_tasks:
                # Check if all tasks are completed
                if all(t.status == TaskStatus.COMPLETED for t in self.current_plan.tasks):
                    break
                else:
                    # Some tasks failed or blocked
                    break
            
            # Execute ready tasks
            for task in ready_tasks:
                task.status = TaskStatus.IN_PROGRESS
                result = await self._execute_single_task(task)
                results.append(result)
                
                if result["success"]:
                    task.status = TaskStatus.COMPLETED
                    task.result = result.get("output", "")
                else:
                    task.status = TaskStatus.FAILED
                    task.result = result.get("error", "Unknown error")
            
            iteration += 1
        
        # Create summary
        completed_tasks = [t for t in self.current_plan.tasks if t.status == TaskStatus.COMPLETED]
        failed_tasks = [t for t in self.current_plan.tasks if t.status == TaskStatus.FAILED]
        
        return {
            "success": len(failed_tasks) == 0,
            "completed_tasks": len(completed_tasks),
            "failed_tasks": len(failed_tasks),
            "total_tasks": len(self.current_plan.tasks),
            "results": results
        }
    
    async def _execute_task(self, task_id: int) -> Dict[str, Any]:
        """Execute a specific task by ID"""
        if not self.current_plan:
            return {"error": "No plan available"}
        
        task = next((t for t in self.current_plan.tasks if t.id == task_id), None)
        if not task:
            return {"error": f"Task {task_id} not found"}
        
        return await self._execute_single_task(task)
    
    async def _execute_single_task(self, task: Task) -> Dict[str, Any]:
        """Execute a single task"""
        self.logger.info("Executing task", task_id=task.id, task_name=task.name)
        
        # For now, simulate task execution
        # In a real implementation, this would delegate to appropriate agents
        return {
            "success": True,
            "task_id": task.id,
            "task_name": task.name,
            "output": f"Completed: {task.description}"
        }
    
    def _format_plan(self, plan: Plan) -> str:
        """Format plan as readable string"""
        lines = [f"Plan for: {plan.goal}", "=" * 50]
        
        for task in plan.tasks:
            deps_str = f" (depends on: {task.dependencies})" if task.dependencies else ""
            status_str = f" [{task.status.value}]"
            lines.append(f"{task.id}. {task.name}{deps_str}{status_str}")
            lines.append(f"   {task.description}")
            if task.result:
                lines.append(f"   Result: {task.result}")
            lines.append("")
        
        return "\n".join(lines)
    
    def add_execution_agent(self, name: str, agent: BaseAgent) -> None:
        """Add an agent that can execute specific types of tasks"""
        self.execution_agents[name] = agent
        self.logger.info("Execution agent added", agent_name=name)