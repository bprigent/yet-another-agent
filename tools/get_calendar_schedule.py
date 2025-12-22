"""Tool to get calendar schedule for a time window."""

from datetime import datetime, timedelta
from tools.calendar_auth import get_calendar_service
from tools.calendar_utils import (
    parse_datetime_input,
    format_datetime_for_api,
    get_default_calendar_id
)


def get_calendar_schedule(
    start_date: str,
    end_date: str,
    calendar_id: str | None = None,
    include_availability: bool = False
) -> str:
    """Get all calendar events in a given time range.
    
    Use this tool when the user asks about their schedule, upcoming events, or what's on their calendar.
    Can optionally include availability blocks (free time between events).
    
    Args:
        start_date: Start date/time (supports "today", "tomorrow", ISO dates, etc.)
        end_date: End date/time (same format as start_date)
        calendar_id: Optional calendar ID (defaults to 'primary')
        include_availability: If True, also returns free time blocks between events
        
    Returns:
        Formatted string with list of events and optionally availability blocks
    """
    try:
        # Parse datetime inputs
        start_dt = parse_datetime_input(start_date)
        end_dt = parse_datetime_input(end_date)
        
        # Set time boundaries for full day coverage
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Validate time range
        if start_dt >= end_dt:
            return f"Error: Start date ({start_date}) must be before end date ({end_date})"
        
        # Get calendar service
        service = get_calendar_service()
        
        # Use provided calendar_id or default to 'primary'
        cal_id = calendar_id if calendar_id else get_default_calendar_id()
        
        # Fetch events from API
        events_result = service.events().list(
            calendarId=cal_id,
            timeMin=format_datetime_for_api(start_dt),
            timeMax=format_datetime_for_api(end_dt),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return f"No events found between {start_date} and {end_date}."
        
        # Process events
        event_list = []
        busy_intervals = []
        
        for event in events:
            # Get event details
            event_id = event.get('id', 'N/A')
            summary = event.get('summary', 'No title')
            start = event.get('start', {})
            end = event.get('end', {})
            location = event.get('location', '')
            description = event.get('description', '')
            
            # Handle dateTime vs date (all-day events)
            start_time_str = start.get('dateTime', start.get('date', 'N/A'))
            end_time_str = end.get('dateTime', end.get('date', 'N/A'))
            
            # Parse times for availability calculation
            if 'dateTime' in start:
                try:
                    start_event_dt = parse_datetime_input(start_time_str)
                    end_event_dt = parse_datetime_input(end_time_str)
                    busy_intervals.append((start_event_dt, end_event_dt))
                except:
                    pass
            
            # Format event for display
            event_str = f"  • {summary}"
            if start_time_str != 'N/A':
                event_str += f"\n    Time: {start_time_str} - {end_time_str}"
            if location:
                event_str += f"\n    Location: {location}"
            if description and len(description) < 100:
                event_str += f"\n    {description[:100]}"
            
            event_list.append(event_str)
        
        # Build result
        result = f"Found {len(events)} event(s) between {start_date} and {end_date}:\n\n"
        result += "\n".join(event_list)
        
        # Add availability blocks if requested
        if include_availability and busy_intervals:
            # Sort intervals by start time
            busy_intervals.sort(key=lambda x: x[0])
            
            # Find free time blocks
            free_blocks = []
            current_time = start_dt
            
            for busy_start, busy_end in busy_intervals:
                if current_time < busy_start:
                    # Free time before this busy period
                    free_blocks.append((current_time, busy_start))
                # Update current_time to end of busy period
                if busy_end > current_time:
                    current_time = busy_end
            
            # Check for free time after last event
            if current_time < end_dt:
                free_blocks.append((current_time, end_dt))
            
            if free_blocks:
                result += "\n\nAvailable time blocks:\n"
                for free_start, free_end in free_blocks:
                    duration = free_end - free_start
                    hours = duration.total_seconds() / 3600
                    result += f"  • {format_datetime_for_api(free_start)} - {format_datetime_for_api(free_end)} ({hours:.1f} hours)\n"
            else:
                result += "\n\nNo free time blocks found in this range."
        
        return result
        
    except ValueError as e:
        return f"Error: Invalid date format - {str(e)}"
    except FileNotFoundError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error retrieving calendar schedule: {str(e)}"

