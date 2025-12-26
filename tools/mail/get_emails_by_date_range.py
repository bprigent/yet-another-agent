"""Tool to get emails between two dates with structured results."""

from typing import List, Dict
from datetime import datetime, timedelta
import pytz
from dateutil import parser as date_parser
from langchain_core.tools import tool
from .mail_auth import get_gmail_service
from email.utils import parseaddr
from tools.core.base_tool import ToolResult, log_tool_call, ensure_string_result
from tools.schemas import EmailsByDateRangeInput


def parse_date_input(date_str: str) -> datetime:
    """Parse user-friendly date strings into datetime objects.
    
    Supports various formats:
    - Relative: "today", "tomorrow", "yesterday"
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
    elif date_str == "yesterday":
        return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
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


def format_date_for_gmail_query(dt: datetime) -> str:
    """Format datetime for Gmail API query (YYYY/MM/DD format).
    
    Args:
        dt: Datetime object (timezone-aware)
        
    Returns:
        String in YYYY/MM/DD format for Gmail API
    """
    return dt.strftime("%Y/%m/%d")


@tool
@ensure_string_result
@log_tool_call("get_emails_by_date_range")
def get_emails_by_date_range(
    start_date: str,
    end_date: str,
    max_results: int = 50
) -> ToolResult:
    """Get emails between two dates with their ID, subject line, and sender details.
    
    Use this tool when the user asks about emails from a specific time period,
    wants to search emails by date range, or needs to find emails from certain dates.
    
    Args:
        start_date: Start date (supports 'today', 'yesterday', ISO format like '2024-01-15', or natural language)
        end_date: End date (same format as start_date)
        max_results: Maximum number of emails to return (default: 50, max: 500)
        
    Returns:
        Formatted string with list of emails including:
        - Email ID (for use with other email tools)
        - Subject line
        - Sender name and email address
        - Date received
    """
    try:
        # Validate input
        try:
            input_data = EmailsByDateRangeInput(
                start_date=start_date,
                end_date=end_date,
                max_results=max_results
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Validation error: {str(e)}"
            )
        
        # Parse dates
        try:
            start_dt = parse_date_input(input_data.start_date)
            end_dt = parse_date_input(input_data.end_date)
        except ValueError as e:
            return ToolResult(
                success=False,
                error=f"Date parsing error: {str(e)}"
            )
        
        # Validate date range
        if start_dt > end_dt:
            return ToolResult(
                success=False,
                error=f"Start date ({start_date}) must be before or equal to end date ({end_date})"
            )
        
        # Set end_date to end of day for inclusive range
        end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Get Gmail service - wrap in try/except to catch auth errors early
        try:
            service = get_gmail_service()
        except FileNotFoundError as e:
            return ToolResult(
                success=False,
                error=f"Gmail authentication error: {str(e)}. Please ensure credentials.json exists and gmail_token.json is set up."
            )
        except RuntimeError as e:
            return ToolResult(
                success=False,
                error=f"Gmail authentication error: {str(e)}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Gmail service initialization error: {str(e)}"
            )
        
        # Build Gmail query with date range
        # Gmail API uses after:YYYY/MM/DD and before:YYYY/MM/DD format
        start_query = format_date_for_gmail_query(start_dt)
        # For before, we need to add 1 day to make it inclusive of end_date
        end_query = format_date_for_gmail_query(end_dt + timedelta(days=1))
        
        query = f'after:{start_query} before:{end_query}'
        
        try:
            # List messages with date range query
            results = service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                q=query,
                maxResults=input_data.max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return ToolResult(
                    success=True,
                    data={
                        "emails": [],
                        "count": 0,
                        "formatted": f"No emails found between {start_date} and {end_date}."
                    },
                    metadata={
                        "start_date": start_date,
                        "end_date": end_date,
                        "max_results": input_data.max_results
                    }
                )
            
            # Get details for each message
            email_list = []
            email_data = []
            for msg in messages:
                msg_id = msg['id']
                
                # Get full message details
                try:
                    message = service.users().messages().get(
                        userId='me',
                        id=msg_id,
                        format='metadata',
                        metadataHeaders=['From', 'Subject', 'Date']
                    ).execute()
                    
                    # Extract headers
                    headers = message['payload'].get('headers', [])
                    
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                    from_header = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                    date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                    
                    # Parse sender name and email
                    sender_name, sender_email = parseaddr(from_header)
                    if not sender_name:
                        sender_name = sender_email.split('@')[0] if sender_email else 'Unknown'
                    
                    # Format email entry
                    email_entry = f"Email ID: {msg_id}\n"
                    email_entry += f"  Subject: {subject}\n"
                    email_entry += f"  From: {sender_name} <{sender_email}>\n"
                    email_entry += f"  Date: {date}\n"
                    
                    email_list.append(email_entry)
                    email_data.append({
                        "id": msg_id,
                        "subject": subject,
                        "from_name": sender_name,
                        "from_email": sender_email,
                        "date": date
                    })
                    
                except Exception as e:
                    # If we can't get details for a specific message, skip it
                    email_list.append(f"Email ID: {msg_id}\n  Error retrieving details: {str(e)}\n")
                    continue
            
            # Build formatted result
            formatted_result = f"Found {len(email_list)} email(s) between {start_date} and {end_date}:\n\n"
            formatted_result += "\n".join(email_list)
            formatted_result += f"\n\nUse the Email ID to get more details or summarize a specific email."
            
            return ToolResult(
                success=True,
                data={
                    "emails": email_data,
                    "count": len(email_data),
                    "formatted": formatted_result
                },
                metadata={
                    "start_date": start_date,
                    "end_date": end_date,
                    "max_results": input_data.max_results
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error retrieving emails: {str(e)}"
            )
        
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Error getting emails by date range: {str(e)}"
        )

