"""Tool to get unread emails."""

from typing import List, Dict
from langchain_core.tools import tool
from .mail_auth import get_gmail_service
from email.utils import parseaddr
import base64


@tool
def get_unread_emails(max_results: int = 10) -> str:
    """Get unread emails with their ID, subject line, and sender details.
    
    Use this tool when the user asks about unread emails, new messages, or wants to check their inbox.
    
    Args:
        max_results: Maximum number of unread emails to return (default: 10, max: 50)
        
    Returns:
        Formatted string with list of unread emails including:
        - Email ID (for use with other email tools)
        - Subject line
        - Sender name and email address
        - Date received
    """
    try:
        # Validate max_results
        if max_results < 1:
            max_results = 10
        if max_results > 50:
            max_results = 50
        
        # Get Gmail service - wrap in try/except to catch auth errors early
        try:
            service = get_gmail_service()
        except FileNotFoundError as e:
            return f"Gmail authentication error: {str(e)}. Please ensure credentials.json exists and gmail_token.json is set up."
        except RuntimeError as e:
            return f"Gmail authentication error: {str(e)}"
        except Exception as e:
            return f"Gmail service initialization error: {str(e)}"
        
        # Query for unread messages in INBOX (following official Gmail API pattern)
        query = 'is:unread'
        
        # List messages with labelIds for INBOX (official Gmail API pattern)
        try:
            results = service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return "No unread emails found."
            
            # Get details for each message
            email_list = []
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
                    
                except Exception as e:
                    # If we can't get details for a specific message, skip it
                    email_list.append(f"Email ID: {msg_id}\n  Error retrieving details: {str(e)}\n")
                    continue
            
            # Build result
            result = f"Found {len(email_list)} unread email(s):\n\n"
            result += "\n".join(email_list)
            result += f"\n\nUse the Email ID to get more details or summarize a specific email."
            
            return result
            
        except Exception as e:
            return f"Error retrieving unread emails: {str(e)}"
        
    except Exception as e:
        return f"Error getting unread emails: {str(e)}"

