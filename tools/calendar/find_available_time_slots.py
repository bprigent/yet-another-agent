"""Tool to find available time slots in calendar."""

from datetime import datetime, timedelta
from .calendar_auth import get_calendar_service
from .calendar_utils import (
    parse_datetime_input,
    format_datetime_for_api,
    get_default_calendar_id,
    parse_working_hours
)


def find_available_time_slots(
    duration_minutes: int,
    earliest_start: str,
    latest_end: str,
    working_hours: str | None = None,
    exclude_all_day_events: bool = True,
    calendar_id: str | None = None
) -> str:
    """Find available time slots of specified duration in calendar.
    
    Analyzes the calendar schedule and returns free time slots that match the constraints.
    Useful for finding when the user can schedule meetings, workouts, or other activities.
    
    Args:
        duration_minutes: Required duration of the time slot in minutes
        earliest_start: Earliest acceptable start time (supports "today", ISO dates, etc.)
        latest_end: Latest acceptable end time (same format as earliest_start)
        working_hours: Optional working hours constraint (e.g., "09:00-17:00")
        exclude_all_day_events: If True, ignores all-day events when calculating availability
        calendar_id: Optional calendar ID (defaults to 'primary')
        
    Returns:
        Formatted string with list of available time slots
    """
    try:
        # Validate duration
        if duration_minutes <= 0:
            return "Error: Duration must be positive (greater than 0 minutes)"
        
        # Parse datetime inputs
        earliest_dt = parse_datetime_input(earliest_start)
        latest_dt = parse_datetime_input(latest_end)
        
        # Validate time range
        if earliest_dt >= latest_dt:
            return f"Error: Earliest start ({earliest_start}) must be before latest end ({latest_end})"
        
        # Check if duration fits in range
        duration_td = timedelta(minutes=duration_minutes)
        if (latest_dt - earliest_dt) < duration_td:
            return f"Error: Duration ({duration_minutes} minutes) is longer than the available time range"
        
        # Parse working hours if provided
        working_hours_tuple = None
        if working_hours:
            try:
                working_hours_tuple = parse_working_hours(working_hours)
            except ValueError as e:
                return f"Error: Invalid working hours format - {str(e)}"
        
        # Get calendar service
        service = get_calendar_service()
        
        # Use provided calendar_id or default to 'primary'
        cal_id = calendar_id if calendar_id else get_default_calendar_id()
        
        # Fetch events from API
        events_result = service.events().list(
            calendarId=cal_id,
            timeMin=format_datetime_for_api(earliest_dt),
            timeMax=format_datetime_for_api(latest_dt),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Build busy intervals
        busy_intervals = []
        for event in events:
            start = event.get('start', {})
            end = event.get('end', {})
            
            # Skip all-day events if requested
            if exclude_all_day_events and 'date' in start:
                continue
            
            # Only process events with dateTime (not all-day)
            if 'dateTime' in start:
                try:
                    start_dt = parse_datetime_input(start.get('dateTime'))
                    end_dt = parse_datetime_input(end.get('dateTime'))
                    busy_intervals.append((start_dt, end_dt))
                except:
                    pass
        
        # Sort intervals by start time
        busy_intervals.sort(key=lambda x: x[0])
        
        # Find available slots
        available_slots = []
        current_time = earliest_dt
        
        # Iterate through each day in the range
        current_date = earliest_dt.date()
        end_date = latest_dt.date()
        
        while current_date <= end_date:
            # Determine day boundaries
            day_start = datetime.combine(current_date, datetime.min.time())
            day_start = earliest_dt if current_date == earliest_dt.date() else day_start
            day_end = datetime.combine(current_date, datetime.max.time())
            day_end = latest_dt if current_date == latest_dt.date() else day_end
            
            # Apply working hours constraint if provided
            if working_hours_tuple:
                (start_hour, start_minute), (end_hour, end_minute) = working_hours_tuple
                day_start = max(day_start, datetime.combine(current_date, datetime.min.time().replace(hour=start_hour, minute=start_minute)))
                day_end = min(day_end, datetime.combine(current_date, datetime.min.time().replace(hour=end_hour, minute=end_minute)))
            
            # Get busy intervals for this day
            day_busy = [(s, e) for s, e in busy_intervals if s.date() == current_date]
            
            # Find free slots on this day
            check_time = max(current_time, day_start)
            for busy_start, busy_end in day_busy:
                if check_time < busy_start:
                    # Potential free slot before busy period
                    slot_end = min(busy_start, day_end)
                    if (slot_end - check_time) >= duration_td:
                        available_slots.append((check_time, slot_end))
                check_time = max(check_time, busy_end)
            
            # Check for free time after last busy event on this day
            if check_time < day_end:
                slot_end = min(day_end, latest_dt)
                if (slot_end - check_time) >= duration_td:
                    available_slots.append((check_time, slot_end))
            
            # Move to next day
            current_date += timedelta(days=1)
            if current_date <= end_date:
                current_time = datetime.combine(current_date, datetime.min.time())
        
        # Filter and format slots
        valid_slots = []
        for slot_start, slot_end in available_slots:
            # Ensure slot fits duration
            if (slot_end - slot_start) >= duration_td:
                # Create slot with exact duration
                actual_end = slot_start + duration_td
                if actual_end <= slot_end:
                    valid_slots.append((slot_start, actual_end))
        
        # Format result
        if not valid_slots:
            result = f"No available {duration_minutes}-minute slots found between {earliest_start} and {latest_end}."
            if working_hours:
                result += f"\n(Within working hours: {working_hours})"
            result += "\n\nSuggestions:"
            result += f"\n  • Try a shorter duration (e.g., {duration_minutes // 2} minutes)"
            result += f"\n  • Expand the time range"
            if working_hours:
                result += "\n  • Remove working hours constraint"
            return result
        
        result = f"Found {len(valid_slots)} available {duration_minutes}-minute slot(s):\n\n"
        for i, (slot_start, slot_end) in enumerate(valid_slots, 1):
            result += f"{i}. {format_datetime_for_api(slot_start)} - {format_datetime_for_api(slot_end)}\n"
        
        if working_hours:
            result += f"\n(Filtered by working hours: {working_hours})"
        
        return result
        
    except ValueError as e:
        return f"Error: Invalid input - {str(e)}"
    except FileNotFoundError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error finding available time slots: {str(e)}"

