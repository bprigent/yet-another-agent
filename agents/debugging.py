"""Debugging and inspection utilities for agent plans and execution."""

from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from agents.planning import PLANS_DIR, load_plan, list_recent_plans
from logging_config import get_logger

logger = get_logger(__name__)


def inspect_plan(task_id: str) -> Dict[str, Any]:
    """Inspect a saved plan and return structured information.
    
    Args:
        task_id: The task ID to inspect
        
    Returns:
        Dictionary with plan information including:
        - task_id: str
        - exists: bool
        - content: str (if exists)
        - steps: List[Dict] (parsed steps)
        - summary: Dict (statistics)
    """
    plan_file = PLANS_DIR / f"{task_id}.txt"
    
    result = {
        "task_id": task_id,
        "exists": plan_file.exists(),
        "content": None,
        "steps": [],
        "summary": {
            "total_steps": 0,
            "completed": 0,
            "failed": 0,
            "pending": 0,
            "in_progress": 0
        }
    }
    
    if not plan_file.exists():
        logger.warning(f"Plan not found for task {task_id}")
        return result
    
    # Load plan content
    content = load_plan(task_id)
    result["content"] = content
    
    # Parse steps from content (simple parsing)
    lines = content.split("\n")
    in_steps_section = False
    
    for line in lines:
        if "PLAN STEPS" in line:
            in_steps_section = True
            continue
        
        if in_steps_section and line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
            # Parse step line: "1. ✅ [COMPLETED] Description"
            parts = line.split("]", 1)
            if len(parts) == 2:
                status_part = parts[0]
                description = parts[1].strip()
                
                # Extract status
                if "[COMPLETED]" in status_part:
                    status = "completed"
                    result["summary"]["completed"] += 1
                elif "[FAILED]" in status_part:
                    status = "failed"
                    result["summary"]["failed"] += 1
                elif "[IN_PROGRESS]" in status_part:
                    status = "in_progress"
                    result["summary"]["in_progress"] += 1
                else:
                    status = "pending"
                    result["summary"]["pending"] += 1
                
                result["steps"].append({
                    "description": description,
                    "status": status
                })
                result["summary"]["total_steps"] += 1
    
    return result


def get_plan_summary(task_id: str) -> str:
    """Get a human-readable summary of a plan.
    
    Args:
        task_id: The task ID to summarize
        
    Returns:
        Formatted summary string
    """
    info = inspect_plan(task_id)
    
    if not info["exists"]:
        return f"Plan {task_id} not found."
    
    summary = info["summary"]
    total = summary["total_steps"]
    
    if total == 0:
        return f"Plan {task_id} exists but has no steps."
    
    completion_rate = (summary["completed"] / total * 100) if total > 0 else 0
    
    result = f"Plan Summary: {task_id}\n"
    result += f"  Total Steps: {total}\n"
    result += f"  ✅ Completed: {summary['completed']}\n"
    result += f"  ❌ Failed: {summary['failed']}\n"
    result += f"  🔄 In Progress: {summary['in_progress']}\n"
    result += f"  ⏳ Pending: {summary['pending']}\n"
    result += f"  Completion Rate: {completion_rate:.1f}%"
    
    return result


def compare_plans(task_ids: List[str]) -> str:
    """Compare multiple plans and return a comparison summary.
    
    Args:
        task_ids: List of task IDs to compare
        
    Returns:
        Formatted comparison string
    """
    if not task_ids:
        return "No task IDs provided."
    
    summaries = []
    for task_id in task_ids:
        info = inspect_plan(task_id)
        if info["exists"]:
            summaries.append((task_id, info["summary"]))
    
    if not summaries:
        return "No valid plans found to compare."
    
    result = "Plan Comparison:\n"
    result += "=" * 80 + "\n"
    
    for task_id, summary in summaries:
        total = summary["total_steps"]
        completion = (summary["completed"] / total * 100) if total > 0 else 0
        result += f"\n{task_id}:\n"
        result += f"  Steps: {total} | Completed: {summary['completed']} ({completion:.1f}%) | "
        result += f"Failed: {summary['failed']} | Pending: {summary['pending']}\n"
    
    return result


def find_plans_by_pattern(pattern: str, limit: int = 10) -> List[str]:
    """Find plans matching a pattern in their content.
    
    Args:
        pattern: String pattern to search for
        limit: Maximum number of results to return
        
    Returns:
        List of task IDs matching the pattern
    """
    matches = []
    
    for plan_file in sorted(PLANS_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            content = plan_file.read_text(encoding="utf-8")
            if pattern.lower() in content.lower():
                matches.append(plan_file.stem)
                if len(matches) >= limit:
                    break
        except Exception as e:
            logger.warning(f"Error reading plan {plan_file}: {e}")
            continue
    
    return matches


def get_recent_plan_stats(days: int = 7) -> Dict[str, Any]:
    """Get statistics about recent plans.
    
    Args:
        days: Number of days to look back
        
    Returns:
        Dictionary with statistics
    """
    cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
    
    plans = []
    for plan_file in PLANS_DIR.glob("*.txt"):
        if plan_file.stat().st_mtime >= cutoff:
            info = inspect_plan(plan_file.stem)
            if info["exists"]:
                plans.append(info)
    
    if not plans:
        return {
            "total_plans": 0,
            "total_steps": 0,
            "avg_completion_rate": 0.0,
            "total_completed": 0,
            "total_failed": 0
        }
    
    total_steps = sum(p["summary"]["total_steps"] for p in plans)
    total_completed = sum(p["summary"]["completed"] for p in plans)
    total_failed = sum(p["summary"]["failed"] for p in plans)
    
    completion_rates = []
    for plan in plans:
        total = plan["summary"]["total_steps"]
        if total > 0:
            rate = plan["summary"]["completed"] / total
            completion_rates.append(rate)
    
    avg_completion = (sum(completion_rates) / len(completion_rates) * 100) if completion_rates else 0.0
    
    return {
        "total_plans": len(plans),
        "total_steps": total_steps,
        "avg_completion_rate": avg_completion,
        "total_completed": total_completed,
        "total_failed": total_failed,
        "period_days": days
    }

