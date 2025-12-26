"""Tool to create or update calendar events with structured results."""

from .calendar_auth import get_calendar_service
from .calendar_utils import (
    parse_datetime_input,
    format_datetime_for_api,
    get_default_calendar_id,
    validate_time_range
)
from tools.core.base_tool import ToolResult, log_tool_call, ensure_string_result
from tools.schemas import CalendarEventInput
from datetime import datetime
from langchain_core.tools import tool


@tool
@ensure_string_result
@log_tool_call("create_update_calendar_event")
def create_update_calendar_event(
    title: str,
    start_time: str,
    end_time: str,
    location: str | None = None,
    description: str | None = None,
    calendar_id: str | None = None,
    event_id: str | None = None,
    attendees: list[str] | None = None
) -> ToolResult:
    """
    Use this tool to create a new calendar event or update an existing one.
    
    This tool is great when the user wants to schedule a meeting, appointment, or event.
    This tool can create a new event or update an existing one by providing the event_id.
    
    Args:
        title: Event title/summary (Create a coherent and concise title on your own if Benjamin doesn't provide one, keep it short)
        start_time: Start time (supports formats like "tomorrow 2pm", "2024-01-15T14:30:00", etc.)
        end_time: End time (same format as start_time)
        location: Optional location/venue for the event (If you can infer the location from the context of this conversation with high confidence, do so.)
        description: Optional description or notes for the event (A place to add further details so that the title can stay short.)
        calendar_id: Optional calendar ID (defaults to 'primary')
        event_id: Optional event ID for updating existing events
        attendees: Optional list of email addresses to invite to the event (if Benjamin doesn't provide one)
        
    Returns:
        Formatted string with event details including event ID and link if it was created successfully
    """
    try:
        # Parse datetime inputs
        start_dt = parse_datetime_input(start_time)
        end_dt = parse_datetime_input(end_time)
        
        # Validate time range
        if not validate_time_range(start_dt, end_dt):
            return ToolResult(
                success=False,
                error=f"Start time ({start_time}) must be before end time ({end_time})"
            )
        
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
                error_msg = str(e)
                if '404' in error_msg or 'not found' in error_msg.lower():
                    return ToolResult(
                        success=False,
                        error=f"Event ID '{event_id}' not found. It may have been deleted or the ID is incorrect."
                    )
                return ToolResult(
                    success=False,
                    error=f"Error updating event: {error_msg}"
                )
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
                return ToolResult(
                    success=False,
                    error=f"Error creating event: {str(e)}"
                )
        
        # Format response
        event_id_result = event.get('id', 'N/A')
        event_link = event.get('htmlLink', 'N/A')
        start_formatted = event['start'].get('dateTime', event['start'].get('date', 'N/A'))
        end_formatted = event['end'].get('dateTime', event['end'].get('date', 'N/A'))
        
        formatted_msg = f"✓ {action} calendar event:\n"
        formatted_msg += f"  Title: {title}\n"
        formatted_msg += f"  Start: {start_formatted}\n"
        formatted_msg += f"  End: {end_formatted}\n"
        if location:
            formatted_msg += f"  Location: {location}\n"
        if description:
            formatted_msg += f"  Description: {description[:100]}{'...' if len(description) > 100 else ''}\n"
        if attendees:
            attendee_emails = [email.strip() for email in attendees if email.strip()]
            formatted_msg += f"  Attendees: {', '.join(attendee_emails)}\n"
        formatted_msg += f"  Event ID: {event_id_result}\n"
        if event_link != 'N/A':
            formatted_msg += f"  Link: {event_link}"
        
        return ToolResult(
            success=True,
            data={
                "event_id": event_id_result,
                "event_link": event_link,
                "title": title,
                "start_time": start_formatted,
                "end_time": end_formatted,
                "location": location,
                "description": description,
                "attendees": [email.strip() for email in attendees] if attendees else None,
                "action": action,
                "formatted": formatted_msg
            },
            metadata={"calendar_id": cal_id, "event_id_provided": event_id is not None}
        )
        
    except ValueError as e:
        return ToolResult(
            success=False,
            error=f"Invalid time format: {str(e)}"
        )
    except FileNotFoundError as e:
        return ToolResult(
            success=False,
            error=f"Calendar authentication error: {str(e)}"
        )
    except Exception as e:
        error_msg = str(e)
        if event_id and ('404' in error_msg or 'not found' in error_msg.lower()):
            return ToolResult(
                success=False,
                error=f"Event ID '{event_id}' not found. It may have been deleted or the ID is incorrect."
            )
        return ToolResult(
            success=False,
            error=f"Error creating/updating calendar event: {error_msg}"
        )

