"""Planning utilities for Deep Agents - plan storage and management."""

from pathlib import Path
from typing import Optional, List
from agents.state import AgentState, PlanStep
from logging_config import get_logger

logger = get_logger(__name__)

# Directory for storing plans
PLANS_DIR = Path(__file__).parent.parent / "memories" / "plans"
PLANS_DIR.mkdir(parents=True, exist_ok=True)


def save_plan(state: AgentState) -> str:
    """Save the current plan to filesystem for inspection and debugging.
    
    Args:
        state: The agent state containing the plan
        
    Returns:
        Path to the saved plan file
    """
    plan_file = PLANS_DIR / f"{state.task_id}.txt"
    
    plan_content = f"Task ID: {state.task_id}\n"
    plan_content += f"Created: {state.created_at.isoformat()}\n"
    plan_content += f"Updated: {state.updated_at.isoformat()}\n"
    plan_content += f"Current Task: {state.current_task or 'None'}\n"
    
    if state.plan_created_at:
        plan_content += f"Plan Created: {state.plan_created_at.isoformat()}\n"
    if state.plan_updated_at:
        plan_content += f"Plan Updated: {state.plan_updated_at.isoformat()}\n"
    
    plan_content += "\n" + "=" * 80 + "\n"
    plan_content += "PLAN STEPS\n"
    plan_content += "=" * 80 + "\n\n"
    
    if not state.plan:
        plan_content += "No plan steps defined yet.\n"
    else:
        for i, step in enumerate(state.plan, 1):
            status_icon = {
                "pending": "⏳",
                "in_progress": "🔄",
                "completed": "✅",
                "failed": "❌"
            }.get(step.status, "❓")
            
            plan_content += f"{i}. {status_icon} [{step.status.upper()}] {step.description}\n"
            plan_content += f"   ID: {step.id}\n"
            
            if step.result:
                result_preview = step.result[:200] + "..." if len(step.result) > 200 else step.result
                plan_content += f"   Result: {result_preview}\n"
            
            if step.error:
                plan_content += f"   Error: {step.error}\n"
            
            if step.tool_calls:
                plan_content += f"   Tool Calls: {len(step.tool_calls)}\n"
                for tool_call in step.tool_calls:
                    tool_name = tool_call.get("name", "unknown")
                    plan_content += f"     - {tool_name}\n"
            
            plan_content += "\n"
    
    # Add intermediate results section
    if state.intermediate_results:
        plan_content += "\n" + "=" * 80 + "\n"
        plan_content += "INTERMEDIATE RESULTS\n"
        plan_content += "=" * 80 + "\n\n"
        for key, value in state.intermediate_results.items():
            value_str = str(value)[:200] + "..." if len(str(value)) > 200 else str(value)
            plan_content += f"{key}: {value_str}\n"
    
    # Add artifacts section
    if state.artifacts:
        plan_content += "\n" + "=" * 80 + "\n"
        plan_content += "ARTIFACTS\n"
        plan_content += "=" * 80 + "\n\n"
        for name, path in state.artifacts.items():
            plan_content += f"{name}: {path}\n"
    
    # Add final response if available
    if state.final_response:
        plan_content += "\n" + "=" * 80 + "\n"
        plan_content += "FINAL RESPONSE\n"
        plan_content += "=" * 80 + "\n\n"
        plan_content += state.final_response + "\n"
    
    plan_file.write_text(plan_content, encoding="utf-8")
    logger.info(f"Plan saved to {plan_file.relative_to(PLANS_DIR.parent.parent)}")
    
    return str(plan_file)


def load_plan(task_id: str) -> Optional[str]:
    """Load a saved plan by task ID.
    
    Args:
        task_id: The task ID to load
        
    Returns:
        Plan content as string, or None if not found
    """
    plan_file = PLANS_DIR / f"{task_id}.txt"
    if plan_file.exists():
        content = plan_file.read_text(encoding="utf-8")
        logger.debug(f"Loaded plan for task {task_id}")
        return content
    logger.warning(f"Plan not found for task {task_id}")
    return None


def list_recent_plans(limit: int = 10) -> List[str]:
    """List recent plan files.
    
    Args:
        limit: Maximum number of plans to return
        
    Returns:
        List of task IDs
    """
    plans = sorted(PLANS_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    task_ids = [p.stem for p in plans[:limit]]
    logger.debug(f"Found {len(task_ids)} recent plans")
    return task_ids


def delete_plan(task_id: str) -> bool:
    """Delete a saved plan.
    
    Args:
        task_id: The task ID to delete
        
    Returns:
        True if deleted, False if not found
    """
    plan_file = PLANS_DIR / f"{task_id}.txt"
    if plan_file.exists():
        plan_file.unlink()
        logger.info(f"Deleted plan for task {task_id}")
        return True
    logger.warning(f"Plan not found for task {task_id}")
    return False

