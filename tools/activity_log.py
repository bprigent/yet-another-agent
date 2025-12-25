"""Activity logging tools for tracking major activities."""

import csv
import os
from pathlib import Path
from datetime import datetime, timedelta
import pytz
from dateutil import parser as date_parser
from langchain_core.tools import tool


# Base directory for memories
MEMORIES_DIR = Path(__file__).parent.parent / "memories"
MEMORIES_DIR.mkdir(exist_ok=True)

# Activity log CSV file path
ACTIVITY_LOG_FILE = MEMORIES_DIR / "activity_log.csv"

# CSV column headers
CSV_HEADERS = ["timestamp", "date", "time", "activity_message"]


def _ensure_log_file_exists():
    """Ensure the activity log CSV file exists with headers."""
    if not ACTIVITY_LOG_FILE.exists():
        with open(ACTIVITY_LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)


def _parse_date_input(date_str: str) -> datetime:
    """Parse user-friendly date strings into datetime objects.
    
    Supports various formats:
    - Relative: "today", "tomorrow"
    - ISO format: "2024-01-15"
    - Natural language: "January 15, 2024"
    
    Args:
        date_str: User input string to parse
        
    Returns:
        datetime: Parsed datetime object (timezone-aware, UTC)
    """
    date_str = date_str.strip().lower()
    now = datetime.now(pytz.UTC)
    
    # Handle relative dates
    if date_str == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_str == "tomorrow":
        return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # Try dateutil parser for various formats
        try:
            result = date_parser.parse(date_str, default=now)
            # If result is naive, make it timezone-aware (UTC)
            if result.tzinfo is None:
                result = pytz.UTC.localize(result)
            return result.replace(hour=0, minute=0, second=0, microsecond=0)
        except Exception as e:
            raise ValueError(f"Could not parse date '{date_str}': {e}")


@tool
def log_activity(activity_message: str, timestamp: str | None = None) -> str:
    """
    Log a major activity with a coherent short log message and the current date and time.
    
    This tool automatically records activities in a CSV file stored in the memories directory.
    Use this tool to log significant activities, actions, or events that should be tracked.
    
    Args:
        activity_message: A coherent, short description of the activity (e.g., "Scheduled meeting with John for tomorrow at 2 PM")
        timestamp: Optional ISO format timestamp (YYYY-MM-DD HH:MM:SS). If not provided, uses current time.
    
    Returns:
        Success message confirming the activity was logged
    """
    try:
        _ensure_log_file_exists()
        
        # Get current timestamp if not provided
        if timestamp:
            try:
                dt = date_parser.parse(timestamp)
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
        
        # Append to CSV file
        with open(ACTIVITY_LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp_str, date_str, time_str, activity_message])
        
        return f"Successfully logged activity: '{activity_message}' at {date_str} {time_str}"
    
    except Exception as e:
        return f"Error logging activity: {str(e)}"


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
        # Ensure log file exists
        if not ACTIVITY_LOG_FILE.exists():
            return f"No activity log found. The log file does not exist yet."
        
        # Parse dates
        try:
            start_dt = _parse_date_input(start_date)
            end_dt = _parse_date_input(end_date)
            
            # Set end_date to end of day
            end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        except ValueError as e:
            return f"Error parsing dates: {str(e)}"
        
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
                            "date": row["date"],
                            "time": row["time"],
                            "message": row["activity_message"]
                        })
                except Exception:
                    # Skip malformed rows
                    continue
        
        if not activities:
            return f"No activities found between {start_date} and {end_date}."
        
        # Format output
        result = [f"Activities from {start_date} to {end_date}:\n"]
        for i, activity in enumerate(activities, 1):
            result.append(f"{i}. [{activity['date']} {activity['time']}] {activity['message']}")
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Error reading activities: {str(e)}"

