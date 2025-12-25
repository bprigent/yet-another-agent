"""Tool to summarize calendar events in natural language."""

from datetime import datetime, timedelta
from collections import defaultdict
from .calendar_auth import get_calendar_service
from .calendar_utils import (
    parse_time_range,
    format_datetime_for_api,
    get_default_calendar_id
)


def summarize_calendar(
    time_range: str,
    include_locations: bool = True,
    group_by_day: bool = True,
    calendar_id: str | None = None
) -> str:
    """Generate a natural language summary of calendar events.
    
    Produces a high-level overview of upcoming events, perfect for quick check-ins
    or understanding overall schedule density.
    
    Args:
        time_range: Time range to summarize ("today", "tomorrow", "this_week", "next_week", or date range)
        include_locations: If True, includes location information in summary
        group_by_day: If True, groups events by day
        calendar_id: Optional calendar ID (defaults to 'primary')
        
    Returns:
        Natural language summary of calendar events
    """
    try:
        # Parse time range
        start_dt, end_dt = parse_time_range(time_range)
        
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
            return f"Your calendar is free for {time_range}. No events scheduled."
        
        # Process events
        events_by_day = defaultdict(list)
        total_duration = timedelta(0)
        earliest_event = None
        latest_event = None
        
        for event in events:
            summary = event.get('summary', 'No title')
            start = event.get('start', {})
            end = event.get('end', {})
            location = event.get('location', '')
            
            start_time_str = start.get('dateTime', start.get('date', 'N/A'))
            end_time_str = end.get('dateTime', end.get('date', 'N/A'))
            
            # Parse event times
            event_start_dt = None
            event_end_dt = None
            
            if 'dateTime' in start:
                try:
                    from .calendar_utils import parse_datetime_input
                    event_start_dt = parse_datetime_input(start_time_str)
                    event_end_dt = parse_datetime_input(end_time_str)
                    duration = event_end_dt - event_start_dt
                    total_duration += duration
                    
                    if earliest_event is None or event_start_dt < earliest_event:
                        earliest_event = event_start_dt
                    if latest_event is None or event_end_dt > latest_event:
                        latest_event = event_end_dt
                except:
                    pass
            
            event_info = {
                'title': summary,
                'start': start_time_str,
                'end': end_time_str,
                'location': location,
                'start_dt': event_start_dt
            }
            
            # Group by day if requested
            if group_by_day and event_start_dt:
                day_key = event_start_dt.date()
                events_by_day[day_key].append(event_info)
            else:
                # Use a single "all" key
                events_by_day['all'].append(event_info)
        
        # Determine busyness level
        num_events = len(events)
        days_in_range = (end_dt.date() - start_dt.date()).days + 1
        events_per_day = num_events / days_in_range if days_in_range > 0 else num_events
        
        if events_per_day < 2:
            busyness = "light"
        elif events_per_day < 4:
            busyness = "moderate"
        else:
            busyness = "busy"
        
        # Build summary
        result = f"📅 Calendar Summary for {time_range}:\n\n"
        result += f"You have {num_events} event(s) scheduled"
        if days_in_range > 1:
            result += f" over {days_in_range} day(s)"
        result += f" ({busyness} schedule).\n"
        
        # Add duration info if available
        if total_duration.total_seconds() > 0:
            total_hours = total_duration.total_seconds() / 3600
            result += f"Total scheduled time: {total_hours:.1f} hours\n"
        
        # Add earliest/latest event info
        if earliest_event and latest_event:
            result += f"Earliest event: {format_datetime_for_api(earliest_event)}\n"
            result += f"Latest event: {format_datetime_for_api(latest_event)}\n"
        
        result += "\n"
        
        # Group by day if requested
        if group_by_day and events_by_day:
            # Sort days
            sorted_days = sorted([d for d in events_by_day.keys() if d != 'all'])
            
            for day in sorted_days:
                day_events = events_by_day[day]
                day_name = day.strftime("%A, %B %d, %Y")
                result += f"\n{day_name} ({len(day_events)} event(s)):\n"
                
                for event_info in day_events:
                    result += f"  • {event_info['title']}\n"
                    if event_info['start'] != 'N/A':
                        result += f"    {event_info['start']}"
                        if event_info['end'] != 'N/A':
                            result += f" - {event_info['end']}"
                        result += "\n"
                    if include_locations and event_info['location']:
                        result += f"    📍 {event_info['location']}\n"
        else:
            # List all events
            result += "Events:\n"
            for event_info in events_by_day.get('all', []):
                result += f"  • {event_info['title']}\n"
                if event_info['start'] != 'N/A':
                    result += f"    {event_info['start']}"
                    if event_info['end'] != 'N/A':
                        result += f" - {event_info['end']}"
                    result += "\n"
                if include_locations and event_info['location']:
                    result += f"    📍 {event_info['location']}\n"
        
        return result
        
    except ValueError as e:
        return f"Error: Invalid time range format - {str(e)}"
    except FileNotFoundError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error summarizing calendar: {str(e)}"

