"""State schemas for Deep Agents using Pydantic."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from langchain_core.messages import BaseMessage


class PlanStep(BaseModel):
    """A single step in the agent's plan."""
    
    id: str = Field(..., description="Unique identifier for this step")
    description: str = Field(..., description="Human-readable description of the step")
    status: Literal["pending", "in_progress", "completed", "failed"] = Field(
        default="pending",
        description="Current status of the step"
    )
    result: Optional[str] = Field(
        default=None,
        description="Result or output from executing this step"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if step failed"
    )
    tool_calls: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Tool calls made during this step"
    )


class AgentState(BaseModel):
    """Main state schema for the Deep Agent.
    
    Separates working scratch from final output for clarity.
    """
    
    # Core conversation state
    messages: List[BaseMessage] = Field(
        default_factory=list,
        description="Conversation message history"
    )
    
    # Planning state
    plan: List[PlanStep] = Field(
        default_factory=list,
        description="Current execution plan with steps"
    )
    plan_created_at: Optional[datetime] = Field(
        default=None,
        description="When the plan was created"
    )
    plan_updated_at: Optional[datetime] = Field(
        default=None,
        description="Last time the plan was updated"
    )
    
    # Working scratch (temporary data during execution)
    current_task: Optional[str] = Field(
        default=None,
        description="Current task being worked on"
    )
    intermediate_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="Temporary results stored during execution"
    )
    artifacts: Dict[str, str] = Field(
        default_factory=dict,
        description="Paths to intermediate artifacts (key: artifact_name, value: file_path)"
    )
    
    # Final output
    final_response: Optional[str] = Field(
        default=None,
        description="Final response to the user"
    )
    citations: List[str] = Field(
        default_factory=list,
        description="Sources or citations for the response"
    )
    
    # Metadata
    task_id: str = Field(
        default_factory=lambda: f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        description="Unique identifier for this task"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When this state was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp"
    )
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()
    
    def add_plan_step(self, description: str) -> PlanStep:
        """Add a new step to the plan."""
        step = PlanStep(
            id=f"step_{len(self.plan) + 1}",
            description=description
        )
        self.plan.append(step)
        self.plan_updated_at = datetime.now()
        return step
    
    def get_step(self, step_id: str) -> Optional[PlanStep]:
        """Get a plan step by ID."""
        return next((s for s in self.plan if s.id == step_id), None)
    
    def mark_step_completed(self, step_id: str, result: Optional[str] = None) -> None:
        """Mark a plan step as completed."""
        step = self.get_step(step_id)
        if step:
            step.status = "completed"
            step.result = result
            self.plan_updated_at = datetime.now()
            self.update_timestamp()
    
    def mark_step_failed(self, step_id: str, error: str) -> None:
        """Mark a plan step as failed."""
        step = self.get_step(step_id)
        if step:
            step.status = "failed"
            step.error = error
            self.plan_updated_at = datetime.now()
            self.update_timestamp()
    
    def is_plan_complete(self) -> bool:
        """Check if all plan steps are completed or failed."""
        if not self.plan:
            return False
        return all(step.status in ("completed", "failed") for step in self.plan)

