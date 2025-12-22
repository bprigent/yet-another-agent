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
        
        # Get calendar service - wrap in try/except to catch auth errors early
        try:
            service = get_calendar_service()
        except FileNotFoundError as e:
            return f"Calendar authentication error: {str(e)}. Please ensure credentials.json exists and token.json is set up."
        except RuntimeError as e:
            return f"Calendar authentication error: {str(e)}"
        except Exception as e:
            return f"Calendar service initialization error: {str(e)}"
        
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


def get_event_id_from_name(
    event_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    calendar_id: str | None = None,
    exact_match: bool = False
) -> str:
    """Get event ID(s) by searching for events with a matching name/title.
    
    Use this tool when you need to find an event ID to delete or update an event by its name.
    Searches for events matching the given name and returns their IDs.
    
    Args:
        event_name: The name/title of the event to search for
        start_date: Optional start date to limit search range (defaults to today)
        end_date: Optional end date to limit search range (defaults to 1 year from start_date)
        calendar_id: Optional calendar ID (defaults to 'primary')
        exact_match: If True, only returns events with exact name match (case-insensitive)
                    If False, returns events where name contains the search term
        
    Returns:
        Formatted string with matching event IDs and details, or error message
    """
    try:
        # Get calendar service - wrap in try/except to catch auth errors early
        try:
            service = get_calendar_service()
        except FileNotFoundError as e:
            return f"Calendar authentication error: {str(e)}. Please ensure credentials.json exists and token.json is set up."
        except RuntimeError as e:
            return f"Calendar authentication error: {str(e)}"
        except Exception as e:
            return f"Calendar service initialization error: {str(e)}"
        
        # Use provided calendar_id or default to 'primary'
        cal_id = calendar_id if calendar_id else get_default_calendar_id()
        
        # Set default date range if not provided
        if start_date is None:
            from datetime import datetime, timedelta
            import pytz
            start_date = "today"
        
        # Parse datetime inputs
        start_dt = parse_datetime_input(start_date)
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if end_date is None:
            # Default to 1 year from start_date
            from datetime import timedelta
            end_dt = start_dt + timedelta(days=365)
        else:
            end_dt = parse_datetime_input(end_date)
        
        end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        
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
        
        # Search for matching events
        matching_events = []
        event_name_lower = event_name.lower().strip()
        
        for event in events:
            summary = event.get('summary', '')
            summary_lower = summary.lower()
            
            # Check for match
            if exact_match:
                if summary_lower == event_name_lower:
                    matching_events.append(event)
            else:
                if event_name_lower in summary_lower:
                    matching_events.append(event)
        
        if not matching_events:
            match_type = "exact match" if exact_match else "partial match"
            return f"No events found with {match_type} for '{event_name}' between {start_date} and {end_date}."
        
        # Format results
        if len(matching_events) == 1:
            event = matching_events[0]
            event_id = event.get('id', 'N/A')
            summary = event.get('summary', 'No title')
            start = event.get('start', {})
            start_time_str = start.get('dateTime', start.get('date', 'N/A'))
            
            result = f"Found event: '{summary}'\n"
            result += f"  Event ID: {event_id}\n"
            result += f"  Start: {start_time_str}\n"
            result += f"\nUse this Event ID to delete or update the event."
            return result
        else:
            # Multiple matches
            result = f"Found {len(matching_events)} matching event(s) for '{event_name}':\n\n"
            for i, event in enumerate(matching_events, 1):
                event_id = event.get('id', 'N/A')
                summary = event.get('summary', 'No title')
                start = event.get('start', {})
                start_time_str = start.get('dateTime', start.get('date', 'N/A'))
                
                result += f"{i}. '{summary}'\n"
                result += f"   Event ID: {event_id}\n"
                result += f"   Start: {start_time_str}\n\n"
            
            result += "Please specify which event you want to delete by providing more details (date, time, etc.) or use the Event ID directly."
            return result
        
    except ValueError as e:
        return f"Error: Invalid date format - {str(e)}"
    except FileNotFoundError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error finding event by name: {str(e)}"


def delete_calendar_event(
    event_id: str | None = None,
    event_name: str | None = None,
    start_date: str | None = None,
    calendar_id: str | None = None
) -> str:
    """Delete a calendar event by ID or by name.
    
    Use this tool when the user wants to cancel or delete a calendar event.
    Can delete by event ID (recommended) or by searching for event name.
    
    Args:
        event_id: Event ID to delete (preferred method)
        event_name: Event name to search for and delete (will delete first match if multiple found)
        start_date: Optional start date to limit search when using event_name
        calendar_id: Optional calendar ID (defaults to 'primary')
        
    Returns:
        Success message with deleted event details, or error message
    """
    try:
        # Get calendar service - wrap in try/except to catch auth errors early
        try:
            service = get_calendar_service()
        except FileNotFoundError as e:
            return f"Calendar authentication error: {str(e)}. Please ensure credentials.json exists and token.json is set up."
        except RuntimeError as e:
            return f"Calendar authentication error: {str(e)}"
        except Exception as e:
            return f"Calendar service initialization error: {str(e)}"
        
        # Use provided calendar_id or default to 'primary'
        cal_id = calendar_id if calendar_id else get_default_calendar_id()
        
        # If event_name provided but no event_id, search for the event
        if event_name and not event_id:
            # Use get_event_id_from_name to find the event
            search_result = get_event_id_from_name(
                event_name=event_name,
                start_date=start_date,
                calendar_id=calendar_id,
                exact_match=False
            )
            
            # Extract event ID from the result
            if "Event ID:" in search_result:
                # Parse the event ID from the result
                lines = search_result.split('\n')
                for line in lines:
                    if 'Event ID:' in line:
                        event_id = line.split('Event ID:')[1].strip()
                        break
                
                if not event_id:
                    return f"Could not extract event ID from search result. {search_result}"
            else:
                # No event found or multiple events found
                return search_result
        
        if not event_id:
            return "Error: Either event_id or event_name must be provided."
        
        # Get event details before deleting (for confirmation message)
        try:
            event = service.events().get(
                calendarId=cal_id,
                eventId=event_id
            ).execute()
            
            event_summary = event.get('summary', 'Untitled Event')
            start = event.get('start', {})
            start_time_str = start.get('dateTime', start.get('date', 'N/A'))
        except Exception as e:
            return f"Error retrieving event details: {str(e)}. Event ID '{event_id}' may not exist."
        
        # Delete the event
        try:
            service.events().delete(
                calendarId=cal_id,
                eventId=event_id
            ).execute()
            
            result = f"✓ Deleted calendar event:\n"
            result += f"  Title: {event_summary}\n"
            result += f"  Start: {start_time_str}\n"
            result += f"  Event ID: {event_id}"
            
            return result
            
        except Exception as e:
            return f"Error deleting event: {str(e)}. Event ID '{event_id}' may not exist or you may not have permission to delete it."
        
    except ValueError as e:
        return f"Error: Invalid input - {str(e)}"
    except FileNotFoundError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error deleting calendar event: {str(e)}"

