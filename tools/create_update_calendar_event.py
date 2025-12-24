"""Tool to create or update calendar events."""

from tools.calendar_auth import get_calendar_service
from tools.calendar_utils import (
    parse_datetime_input,
    format_datetime_for_api,
    get_default_calendar_id,
    validate_time_range
)


def create_update_calendar_event(
    title: str,
    start_time: str,
    end_time: str,
    location: str | None = None,
    description: str | None = None,
    calendar_id: str | None = None,
    event_id: str | None = None,
    attendees: list[str] | None = None
) -> str:
    """Create a new calendar event or update an existing one.
    
    Use this tool when the user wants to schedule a meeting, appointment, or event.
    Can create new events or update existing ones by providing the event_id.
    
    Args:
        title: Event title/summary
        start_time: Start time (supports formats like "tomorrow 2pm", "2024-01-15T14:30:00", etc.)
        end_time: End time (same format as start_time)
        location: Optional location/venue for the event
        description: Optional description or notes for the event
        calendar_id: Optional calendar ID (defaults to 'primary')
        event_id: Optional event ID for updating existing events
        attendees: Optional list of email addresses to invite to the event
        
    Returns:
        Formatted string with event details including event ID and link
        
    Raises:
        ValueError: If time format is invalid or start_time >= end_time
    """
    try:
        # Parse datetime inputs
        start_dt = parse_datetime_input(start_time)
        end_dt = parse_datetime_input(end_time)
        
        # Validate time range
        if not validate_time_range(start_dt, end_dt):
            return f"Error: Start time ({start_time}) must be before end time ({end_time})"
        
        # Get calendar service
        service = get_calendar_service()
        
        # Use provided calendar_id or default to 'primary'
        cal_id = calendar_id if calendar_id else get_default_calendar_id()
        
        # Build event body
        event_body = {
            'summary': title,
            'start': {
                'dateTime': format_datetime_for_api(start_dt),
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': format_datetime_for_api(end_dt),
                'timeZone': 'UTC'
            }
        }
        
        # Add optional fields
        if location:
            event_body['location'] = location
        if description:
            event_body['description'] = description
        if attendees:
            # Convert list of email strings to Google Calendar API format
            event_body['attendees'] = [{'email': email.strip()} for email in attendees if email.strip()]
        
        # Create or update event
        # Send invitations to attendees if any are provided
        send_updates = 'all' if attendees else 'none'
        
        if event_id:
            # Update existing event
            try:
                event = service.events().update(
                    calendarId=cal_id,
                    eventId=event_id,
                    body=event_body,
                    sendUpdates=send_updates
                ).execute()
                action = "Updated"
            except Exception as e:
                return f"Error updating event: {str(e)}. Event ID '{event_id}' may not exist."
        else:
            # Create new event
            try:
                event = service.events().insert(
                    calendarId=cal_id,
                    body=event_body,
                    sendUpdates=send_updates
                ).execute()
                action = "Created"
            except Exception as e:
                return f"Error creating event: {str(e)}"
        
        # Format response
        event_id_result = event.get('id', 'N/A')
        event_link = event.get('htmlLink', 'N/A')
        start_formatted = event['start'].get('dateTime', event['start'].get('date', 'N/A'))
        end_formatted = event['end'].get('dateTime', event['end'].get('date', 'N/A'))
        
        result = f"✓ {action} calendar event:\n"
        result += f"  Title: {title}\n"
        result += f"  Start: {start_formatted}\n"
        result += f"  End: {end_formatted}\n"
        if location:
            result += f"  Location: {location}\n"
        if description:
            result += f"  Description: {description[:100]}{'...' if len(description) > 100 else ''}\n"
        if attendees:
            attendee_emails = [email.strip() for email in attendees if email.strip()]
            result += f"  Attendees: {', '.join(attendee_emails)}\n"
        result += f"  Event ID: {event_id_result}\n"
        if event_link != 'N/A':
            result += f"  Link: {event_link}"
        
        return result
        
    except ValueError as e:
        return f"Error: Invalid time format - {str(e)}"
    except FileNotFoundError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error creating/updating calendar event: {str(e)}"

