"""Tool for logging activities with structured results."""

import csv
from datetime import datetime
import pytz
from dateutil import parser as date_parser
from langchain_core.tools import tool
from tools.core.base_tool import ToolResult, log_tool_call, ensure_string_result
from tools.schemas import ActivityLogInput

from .config import ACTIVITY_LOG_FILE
from .utils import ensure_log_file_exists


@tool
@ensure_string_result
@log_tool_call("log_activity")
def log_activity(
    activity_message: str, 
    timestamp: str | None = None,
    related_people: str | None = None,
    related_places: str | None = None,
    related_topics: str | None = None
) -> ToolResult:
    """
    Use this tool to log significant activities, actions, or events that should be tracked. It automatically records activities in a CSV file stored in the memories directory.
    
    Args:
        activity_message: A coherent, short description of the activity (e.g., "Scheduled meeting with John for tomorrow at 2 PM")
        timestamp: Optional ISO format timestamp (YYYY-MM-DD HH:MM:SS). If not provided, the system will use current time.
        related_people: Optional comma-separated list of people related to this activity (e.g., "John Doe, Jane Smith")
        related_places: Optional comma-separated list of places related to this activity (e.g., "New York, Office")
        related_topics: Optional comma-separated list of topics related to this activity (e.g., "meeting, project planning")
    
    Returns:
        Success message confirming the activity was logged
    """
    try:
        # Validate input
        try:
            input_data = ActivityLogInput(
                activity_message=activity_message,
                timestamp=timestamp,
                related_people=related_people,
                related_places=related_places,
                related_topics=related_topics
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Validation error: {str(e)}"
            )
        
        ensure_log_file_exists()
        
        # Get current timestamp if not provided
        if input_data.timestamp:
            try:
                dt = date_parser.parse(input_data.timestamp)
                if dt.tzinfo is None:
                    dt = pytz.UTC.localize(dt)
            except Exception as e:
                # If parsing fails, use current time
                dt = datetime.now(pytz.UTC)
        else:
            dt = datetime.now(pytz.UTC)
        
        # Format components
        timestamp_str = dt.isoformat()
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M:%S")
        
        # Prepare new column values (empty string if not provided)
        related_people_str = input_data.related_people.strip() if input_data.related_people else ""
        related_places_str = input_data.related_places.strip() if input_data.related_places else ""
        related_topics_str = input_data.related_topics.strip() if input_data.related_topics else ""
        
        # Append to CSV file
        with open(ACTIVITY_LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp_str, 
                date_str, 
                time_str, 
                input_data.activity_message,
                related_people_str,
                related_places_str,
                related_topics_str
            ])
        
        formatted_msg = f"Successfully logged activity: '{input_data.activity_message}' at {date_str} {time_str}"
        if related_people_str:
            formatted_msg += f" (People: {related_people_str})"
        if related_places_str:
            formatted_msg += f" (Places: {related_places_str})"
        if related_topics_str:
            formatted_msg += f" (Topics: {related_topics_str})"
        
        return ToolResult(
            success=True,
            data={
                "activity_message": input_data.activity_message,
                "timestamp": timestamp_str,
                "date": date_str,
                "time": time_str,
                "related_people": related_people_str.split(", ") if related_people_str else [],
                "related_places": related_places_str.split(", ") if related_places_str else [],
                "related_topics": related_topics_str.split(", ") if related_topics_str else [],
                "formatted": formatted_msg
            },
            metadata={"log_file": str(ACTIVITY_LOG_FILE)}
        )
    
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Error logging activity: {str(e)}"
        )

