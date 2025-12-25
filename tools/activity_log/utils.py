"""Utility functions for activity logging."""

import csv
from datetime import datetime, timedelta
import pytz
from dateutil import parser as date_parser

from .config import ACTIVITY_LOG_FILE, CSV_HEADERS


def migrate_csv_if_needed():
    """Migrate existing CSV to include new columns if needed."""
    if not ACTIVITY_LOG_FILE.exists():
        return
    
    # Read existing CSV
    rows = []
    with open(ACTIVITY_LOG_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        old_headers = list(reader.fieldnames or [])
        
        # Check if migration is needed (compare as lists)
        if old_headers == CSV_HEADERS:
            return  # Already migrated
        
        # Read all rows
        for row in reader:
            rows.append(row)
    
    # Write back with new headers
    with open(ACTIVITY_LOG_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for row in rows:
            # Ensure all new columns exist (default to empty string)
            new_row = {header: row.get(header, "") for header in CSV_HEADERS}
            writer.writerow(new_row)


def ensure_log_file_exists():
    """Ensure the activity log CSV file exists with headers."""
    if not ACTIVITY_LOG_FILE.exists():
        with open(ACTIVITY_LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
    else:
        # Migrate existing CSV if needed
        migrate_csv_if_needed()


def parse_date_input(date_str: str) -> datetime:
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


def format_activity_output(activities: list[dict], header: str) -> str:
    """Format a list of activities for display.
    
    Args:
        activities: List of activity dictionaries
        header: Header string for the output
        
    Returns:
        Formatted string with activities
    """
    if not activities:
        return f"No activities found."
    
    result = [f"{header}\n"]
    for i, activity in enumerate(activities, 1):
        line = f"{i}. [{activity['date']} {activity['time']}] {activity['message']}"
        # Add metadata if present
        metadata_parts = []
        if activity.get("related_people"):
            metadata_parts.append(f"People: {activity['related_people']}")
        if activity.get("related_places"):
            metadata_parts.append(f"Places: {activity['related_places']}")
        if activity.get("related_topics"):
            metadata_parts.append(f"Topics: {activity['related_topics']}")
        if metadata_parts:
            line += f" ({', '.join(metadata_parts)})"
        result.append(line)
    
    return "\n".join(result)

