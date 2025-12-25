"""Tool for reading activities by date range with structured results."""

import csv
import pytz
from dateutil import parser as date_parser
from langchain_core.tools import tool
from tools.core.base_tool import ToolResult, log_tool_call
from pydantic import BaseModel, Field

from .config import ACTIVITY_LOG_FILE
from .utils import ensure_log_file_exists, parse_date_input, format_activity_output


class ReadActivityInput(BaseModel):
    """Input schema for reading activities."""
    start_date: str = Field(..., description="Start date for the query")
    end_date: str = Field(..., description="End date for the query")


@log_tool_call("read_activity")
@tool
def read_activity(start_date: str, end_date: str) -> str:
    """
    Read activities from the activity log between two dates (inclusive).
    
    Args:
        start_date: Start date for the query (supports "today", "tomorrow", ISO format "2024-01-15", or natural language)
        end_date: End date for the query (supports "today", "tomorrow", ISO format "2024-01-15", or natural language)
    
    Returns:
        Formatted string listing all activities in the date range, or an error message
    """
    try:
        # Validate input
        try:
            input_data = ReadActivityInput(start_date=start_date, end_date=end_date)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Validation error: {str(e)}"
            ).to_string()
        
        # Ensure log file exists and is migrated
        ensure_log_file_exists()
        if not ACTIVITY_LOG_FILE.exists():
            return ToolResult(
                success=False,
                error="No activity log found. The log file does not exist yet."
            ).to_string()
        
        # Parse dates
        try:
            start_dt = parse_date_input(input_data.start_date)
            end_dt = parse_date_input(input_data.end_date)
            
            # Set end_date to end of day
            end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        except ValueError as e:
            return ToolResult(
                success=False,
                error=f"Error parsing dates: {str(e)}"
            ).to_string()
        
        # Read activities from CSV
        activities = []
        with open(ACTIVITY_LOG_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Parse the timestamp from the CSV
                    activity_timestamp = date_parser.parse(row["timestamp"])
                    if activity_timestamp.tzinfo is None:
                        activity_timestamp = pytz.UTC.localize(activity_timestamp)
                    
                    # Check if activity is within date range
                    if start_dt <= activity_timestamp <= end_dt:
                        activities.append({
                            "date": row.get("date", ""),
                            "time": row.get("time", ""),
                            "message": row.get("activity_message", ""),
                            "related_people": row.get("related_people", ""),
                            "related_places": row.get("related_places", ""),
                            "related_topics": row.get("related_topics", "")
                        })
                except Exception:
                    # Skip malformed rows
                    continue
        
        if not activities:
            return ToolResult(
                success=True,
                data={"activities": [], "count": 0},
                metadata={
                    "start_date": input_data.start_date,
                    "end_date": input_data.end_date
                }
            ).to_string()
        
        formatted_output = format_activity_output(activities, f"Activities from {input_data.start_date} to {input_data.end_date}:")
        
        return ToolResult(
            success=True,
            data={
                "activities": activities,
                "count": len(activities),
                "formatted": formatted_output
            },
            metadata={
                "start_date": input_data.start_date,
                "end_date": input_data.end_date,
                "log_file": str(ACTIVITY_LOG_FILE)
            }
        ).to_string()
    
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Error reading activities: {str(e)}"
        ).to_string()

