"""Tool to summarize an email by its ID."""

from typing import Optional
from langchain_core.tools import tool
from .mail_auth import get_gmail_service
from email.utils import parseaddr
import base64
import re


def _decode_message_body(message: dict) -> str:
    """Extract and decode the message body from Gmail API response.
    
    Args:
        message: Gmail API message object
        
    Returns:
        Decoded message body as string
    """
    body = ""
    
    def extract_body(part):
        """Recursively extract body from message parts."""
        if part.get('mimeType') == 'text/plain':
            data = part.get('body', {}).get('data')
            if data:
                try:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                except Exception:
                    return ""
        elif part.get('mimeType') == 'text/html':
            data = part.get('body', {}).get('data')
            if data:
                try:
                    html_content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    # Simple HTML tag removal (basic cleanup)
                    text_content = re.sub(r'<[^>]+>', '', html_content)
                    return text_content
                except Exception:
                    return ""
        
        # Check for nested parts (multipart messages)
        if 'parts' in part:
            for subpart in part['parts']:
                result = extract_body(subpart)
                if result:
                    return result
        
        return ""
    
    payload = message.get('payload', {})
    body = extract_body(payload)
    
    # If no body found in parts, try direct body
    if not body and 'body' in payload:
        data = payload['body'].get('data')
        if data:
            try:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            except Exception:
                pass
    
    return body


@tool
def summarize_email(email_id: str, include_body: bool = True) -> str:
    """Summarize an email by its ID.
    
    Use this tool when the user wants to read or understand the content of a specific email.
    The email ID can be obtained from get_unread_emails or other email listing tools.
    
    Args:
        email_id: The Gmail message ID (obtained from get_unread_emails)
        include_body: If True, includes the full email body in the summary (default: True)
        
    Returns:
        Formatted string with email summary including:
        - Subject
        - Sender details
        - Date
        - Recipients
        - Email body (if include_body is True)
    """
    try:
        if not email_id or not email_id.strip():
            return "Error: Email ID is required."
        
        # Get Gmail service - wrap in try/except to catch auth errors early
        try:
            service = get_gmail_service()
        except FileNotFoundError as e:
            return f"Gmail authentication error: {str(e)}. Please ensure credentials.json exists and gmail_token.json is set up."
        except RuntimeError as e:
            return f"Gmail authentication error: {str(e)}"
        except Exception as e:
            return f"Gmail service initialization error: {str(e)}"
        
        # Get full message
        try:
            message = service.users().messages().get(
                userId='me',
                id=email_id,
                format='full'
            ).execute()
        except Exception as e:
            return f"Error retrieving email with ID '{email_id}': {str(e)}. The email may not exist or you may not have permission to access it."
        
        # Extract headers
        headers = message['payload'].get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        from_header = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        to_header = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown Recipient')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
        
        # Parse sender
        sender_name, sender_email = parseaddr(from_header)
        if not sender_name:
            sender_name = sender_email.split('@')[0] if sender_email else 'Unknown'
        
        # Build summary
        summary = f"Email Summary (ID: {email_id})\n"
        summary += "=" * 50 + "\n"
        summary += f"Subject: {subject}\n"
        summary += f"From: {sender_name} <{sender_email}>\n"
        summary += f"To: {to_header}\n"
        summary += f"Date: {date}\n"
        
        # Extract and include body if requested
        if include_body:
            body = _decode_message_body(message)
            if body:
                # Clean up body (remove excessive whitespace)
                body = re.sub(r'\n\s*\n\s*\n+', '\n\n', body)  # Remove excessive newlines
                body = body.strip()
                
                summary += "\n" + "=" * 50 + "\n"
                summary += "Email Body:\n"
                summary += "=" * 50 + "\n"
                summary += body
            else:
                summary += "\n" + "=" * 50 + "\n"
                summary += "Email Body: (No text content found - may be HTML-only or empty)"
        
        return summary
        
    except Exception as e:
        return f"Error summarizing email: {str(e)}"

