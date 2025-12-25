"""Tools package for the Deep Agent."""

from tools.internet_search import internet_search
from tools.core.get_current_time import get_current_time
from tools.core.get_user_ip import get_user_ip
from tools.core.get_location_from_ip import get_location_from_ip
from tools.core.calculator import calculator
from tools.calendar.create_update_calendar_event import create_update_calendar_event
from tools.calendar.get_calendar_schedule import (
    get_calendar_schedule,
    get_event_id_from_name,
    delete_calendar_event
)
from tools.calendar.find_available_time_slots import find_available_time_slots
from tools.calendar.summarize_calendar import summarize_calendar
from tools.memory_tools import (
    write_memory_file,
    read_memory_file,
    list_memory_files,
    edit_memory_file,
)
from tools.mail import (
    get_unread_emails,
    summarize_email,
    create_draft,
    send_draft,
    list_drafts,
    mark_as_read,
)

__all__ = [
    "internet_search",
    "get_current_time",
    "get_user_ip",
    "get_location_from_ip",
    "create_update_calendar_event",
    "get_calendar_schedule",
    "get_event_id_from_name",
    "delete_calendar_event",
    "find_available_time_slots",
    "summarize_calendar",
    "write_memory_file",
    "read_memory_file",
    "list_memory_files",
    "edit_memory_file",
    "calculator",
    "get_unread_emails",
    "summarize_email",
    "create_draft",
    "send_draft",
    "list_drafts",
    "mark_as_read",
]

