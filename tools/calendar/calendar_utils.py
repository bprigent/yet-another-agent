"""Shared utilities for Google Calendar tools."""

from datetime import datetime, timedelta
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
import pytz


def parse_datetime_input(dt_str: str, default_time: str | None = None) -> datetime:
    """Parse user-friendly datetime strings into datetime objects.
    
    Supports various formats:
    - Relative: "today", "tomorrow", "next week", "next Monday"
    - ISO format: "2024-01-15T14:30:00"
    - Natural language: "January 15, 2024 2:30 PM"
    - Date only: "2024-01-15" (uses default_time if provided)
    
    Args:
        dt_str: User input string to parse
        default_time: Optional time string (HH:MM) to use if dt_str is date-only
        
    Returns:
        datetime: Parsed datetime object (timezone-aware, UTC)
        
    Raises:
        ValueError: If datetime string cannot be parsed
    """
    dt_str = dt_str.strip().lower()
    now = datetime.now(pytz.UTC)
    
    # Handle relative dates
    if dt_str == "today":
        result = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif dt_str == "tomorrow":
        result = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif dt_str.startswith("next "):
        # Handle "next week", "next monday", etc.
        if dt_str == "next week":
            # Next Monday
            days_ahead = 7 - now.weekday()
            if days_ahead == 0:  # Today is Monday
                days_ahead = 7
            result = (now + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Try to parse as relative date
            try:
                result = date_parser.parse(dt_str, default=now)
            except:
                raise ValueError(f"Could not parse relative date: {dt_str}")
    else:
        # Try dateutil parser for various formats
        try:
            result = date_parser.parse(dt_str, default=now)
        except Exception as e:
            raise ValueError(f"Could not parse datetime '{dt_str}': {e}")
    
    # If result is naive, make it timezone-aware (UTC)
    if result.tzinfo is None:
        result = pytz.UTC.localize(result)
    
    # If only date provided and default_time given, add the time
    if default_time and result.hour == 0 and result.minute == 0:
        try:
            hour, minute = map(int, default_time.split(':'))
            result = result.replace(hour=hour, minute=minute)
        except:
            pass  # Ignore if default_time parsing fails
    
    return result


def format_datetime_for_api(dt: datetime) -> str:
    """Format datetime object as RFC3339 string for Google Calendar API.
    
    Args:
        dt: Datetime object (timezone-aware or naive)
        
    Returns:
        str: RFC3339 formatted datetime string
    """
    # Ensure timezone-aware (default to UTC if naive)
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    
    # Convert to RFC3339 format
    return dt.isoformat()


def get_default_calendar_id() -> str:
    """Get the default calendar ID (primary calendar).
    
    Returns:
        str: 'primary' calendar ID
    """
    return 'primary'


def validate_time_range(start: datetime, end: datetime) -> bool:
    """Validate that start time is before end time.
    
    Args:
        start: Start datetime
        end: End datetime
        
    Returns:
        bool: True if start < end, False otherwise
    """
    return start < end


def parse_time_range(time_range: str) -> tuple[datetime, datetime]:
    """Parse a time range string into start and end datetimes.
    
    Supports:
    - "today" -> today 00:00 to 23:59
    - "tomorrow" -> tomorrow 00:00 to 23:59
    - "this_week" -> Monday 00:00 to Sunday 23:59 of current week
    - "next_week" -> Monday 00:00 to Sunday 23:59 of next week
    - Or custom date range
    
    Args:
        time_range: Time range string
        
    Returns:
        tuple[datetime, datetime]: (start_datetime, end_datetime)
    """
    time_range = time_range.strip().lower()
    now = datetime.now(pytz.UTC)
    
    if time_range == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif time_range == "tomorrow":
        tomorrow = now + timedelta(days=1)
        start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif time_range == "this_week" or time_range == "this week":
        # Monday of current week
        days_since_monday = now.weekday()
        monday = now - timedelta(days=days_since_monday)
        start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        # Sunday of current week
        sunday = start + timedelta(days=6)
        end = sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif time_range == "next_week" or time_range == "next week":
        # Monday of next week
        days_since_monday = now.weekday()
        days_until_next_monday = 7 - days_since_monday
        next_monday = now + timedelta(days=days_until_next_monday)
        start = next_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        # Sunday of next week
        next_sunday = start + timedelta(days=6)
        end = next_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        # Try to parse as date range (e.g., "2024-01-15 to 2024-01-20")
        if " to " in time_range or " - " in time_range:
            separator = " to " if " to " in time_range else " - "
            parts = time_range.split(separator, 1)
            start = parse_datetime_input(parts[0].strip())
            end = parse_datetime_input(parts[1].strip())
            # Set end to end of day
            end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            # Single date - treat as single day range
            start = parse_datetime_input(time_range)
            end = start.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return start, end


def parse_working_hours(working_hours: str) -> tuple[int, int]:
    """Parse working hours string into start and end hour/minute tuples.
    
    Format: "HH:MM-HH:MM" or "HH:MM to HH:MM"
    
    Args:
        working_hours: Working hours string (e.g., "09:00-17:00")
        
    Returns:
        tuple[tuple[int, int], tuple[int, int]]: ((start_hour, start_minute), (end_hour, end_minute))
        
    Raises:
        ValueError: If format is invalid
    """
    if " to " in working_hours:
        separator = " to "
    elif "-" in working_hours:
        separator = "-"
    else:
        raise ValueError(f"Invalid working hours format: {working_hours}. Expected 'HH:MM-HH:MM'")
    
    parts = working_hours.split(separator, 1)
    start_str = parts[0].strip()
    end_str = parts[1].strip()
    
    try:
        start_hour, start_minute = map(int, start_str.split(':'))
        end_hour, end_minute = map(int, end_str.split(':'))
        return ((start_hour, start_minute), (end_hour, end_minute))
    except Exception as e:
        raise ValueError(f"Could not parse working hours: {e}")

