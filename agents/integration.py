"""Optional integration helpers for AgentState in main agent execution.

These utilities provide hooks for integrating AgentState and planning
into your agent execution without breaking existing functionality.
All functions are optional and can be used incrementally.
"""

from typing import Optional, Dict, Any
from agents.state import AgentState
from agents.planning import save_plan
from logging_config import get_logger, set_task_context, get_task_context
from datetime import datetime

logger = get_logger(__name__)


def create_task_state(user_message: str, task_id: Optional[str] = None) -> AgentState:
    """Create a new AgentState for a task.
    
    This is an optional helper to create state when starting a new task.
    You can use this in your message handler to track task execution.
    
    Args:
        user_message: The user's message/request
        task_id: Optional task ID (auto-generated if not provided)
        
    Returns:
        New AgentState instance
    """
    if task_id is None:
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    state = AgentState(
        current_task=user_message[:200],  # Truncate long messages
        task_id=task_id
    )
    
    # Set task context for logging
    set_task_context(task_id)
    logger.info(f"Created task state: {task_id}")
    
    return state


def save_plan_optional(state: Optional[AgentState], force: bool = False) -> Optional[str]:
    """Optionally save a plan if state is provided.
    
    This allows you to add plan saving to your agent without requiring
    state management. If state is None, this does nothing.
    
    Args:
        state: Optional AgentState instance
        force: If True, save even if plan is empty
        
    Returns:
        Plan file path if saved, None otherwise
    """
    if state is None:
        return None
    
    # Only save if there are plan steps or if forced
    if not state.plan and not force:
        return None
    
    try:
        plan_path = save_plan(state)
        logger.debug(f"Saved plan for task {state.task_id}")
        return plan_path
    except Exception as e:
        logger.warning(f"Failed to save plan: {e}")
        return None


def track_tool_call_in_state(
    state: Optional[AgentState],
    tool_name: str,
    step_description: Optional[str] = None
) -> Optional[str]:
    """Optionally track a tool call in state.
    
    If state is provided, creates or updates a plan step for this tool call.
    This allows incremental integration of state tracking.
    
    Args:
        state: Optional AgentState instance
        tool_name: Name of the tool being called
        step_description: Optional description (auto-generated if not provided)
        
    Returns:
        Step ID if state is provided, None otherwise
    """
    if state is None:
        return None
    
    # Create step description if not provided
    if step_description is None:
        step_description = f"Execute {tool_name}"
    
    # Find or create a step for this tool call
    step = None
    for existing_step in state.plan:
        if tool_name in existing_step.description and existing_step.status == "pending":
            step = existing_step
            break
    
    if step is None:
        step = state.add_plan_step(step_description)
    
    step.status = "in_progress"
    step.tool_calls.append({"name": tool_name, "timestamp": datetime.now().isoformat()})
    state.update_timestamp()
    
    return step.id


def mark_tool_complete_in_state(
    state: Optional[AgentState],
    step_id: Optional[str],
    result: Optional[str] = None,
    success: bool = True
) -> None:
    """Optionally mark a tool call as complete in state.
    
    Args:
        state: Optional AgentState instance
        step_id: Step ID from track_tool_call_in_state
        result: Optional result message
        success: Whether the tool call succeeded
    """
    if state is None or step_id is None:
        return
    
    if success:
        state.mark_step_completed(step_id, result)
    else:
        state.mark_step_failed(step_id, result or "Tool call failed")
    
    # Auto-save plan after marking complete
    save_plan_optional(state)


def cleanup_task_context() -> None:
    """Clean up task context after task completion.
    
    Call this when a task is finished to clear the logging context.
    """
    set_task_context(None)
    logger.debug("Cleared task context")


# Example integration pattern (commented out - for reference)
"""
# In your app.py message handler, you could optionally add:

from agents.integration import (
    create_task_state,
    save_plan_optional,
    track_tool_call_in_state,
    mark_tool_complete_in_state,
    cleanup_task_context
)

# At the start of message handling:
state = create_task_state(user_message)  # Optional - can be None
save_plan_optional(state)  # Save initial state

# When agent invokes tools (you'd need to hook into tool calls):
step_id = track_tool_call_in_state(state, "get_unread_emails")
# ... tool executes ...
mark_tool_complete_in_state(state, step_id, "Found 5 emails", success=True)

# At the end:
save_plan_optional(state, force=True)  # Save final state
cleanup_task_context()
"""

