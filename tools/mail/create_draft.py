"""Tool to create a draft email via Gmail."""

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langchain_core.tools import tool
import base64
from .mail_auth import get_gmail_service


@tool
def create_draft(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    is_html: bool = False
) -> str:
    """Create a draft email via Gmail.
    
    Use this tool when the user wants to compose an email. This creates a draft that can be reviewed
    and sent later using the send_draft tool.
    
    Args:
        to: Recipient email address(es) - comma-separated for multiple recipients
        subject: Email subject line
        body: Email body content
        cc: Optional CC recipient(s) - comma-separated for multiple
        bcc: Optional BCC recipient(s) - comma-separated for multiple
        is_html: If True, creates email as HTML format (default: False for plain text)
        
    Returns:
        Success message with draft ID and details, or error message
    """
    try:
        # Validate required fields
        if not to or not to.strip():
            return "Error: Recipient email address (to) is required."
        if not subject or not subject.strip():
            return "Error: Email subject is required."
        if not body or not body.strip():
            return "Error: Email body is required."
        
        # Get Gmail service - wrap in try/except to catch auth errors early
        try:
            service = get_gmail_service()
        except FileNotFoundError as e:
            return f"Gmail authentication error: {str(e)}. Please ensure credentials.json exists and gmail_token.json is set up."
        except RuntimeError as e:
            return f"Gmail authentication error: {str(e)}"
        except Exception as e:
            return f"Gmail service initialization error: {str(e)}"
        
        # Create MIME message following official Gmail API pattern
        if is_html:
            message = MIMEText(body, 'html')
        else:
            message = MIMEText(body, 'plain')
        
        message['to'] = to
        message['subject'] = subject
        
        if cc:
            message['cc'] = cc
        if bcc:
            message['bcc'] = bcc
        
        # Encode message as base64url-safe string (official Gmail API pattern)
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Create draft message object
        draft_message = {'raw': raw_message}
        
        # Create the draft
        try:
            draft = service.users().drafts().create(
                userId='me',
                body={'message': draft_message}
            ).execute()
            
            draft_id = draft.get('id', 'Unknown')
            message_id = draft.get('message', {}).get('id', 'Unknown')
            
            result = f"✓ Draft created successfully!\n"
            result += f"  Draft ID: {draft_id}\n"
            result += f"  To: {to}\n"
            if cc:
                result += f"  CC: {cc}\n"
            if bcc:
                result += f"  BCC: {bcc}\n"
            result += f"  Subject: {subject}\n"
            result += f"  Message ID: {message_id}\n"
            result += f"\nUse the Draft ID with send_draft tool to send this email."
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            # Provide helpful error messages
            if 'invalid' in error_msg.lower() or 'malformed' in error_msg.lower():
                return f"Error creating draft: Invalid email address format. Please check the recipient email address(es). Details: {error_msg}"
            elif 'quota' in error_msg.lower() or 'limit' in error_msg.lower():
                return f"Error creating draft: Gmail quota exceeded. Please try again later. Details: {error_msg}"
            else:
                return f"Error creating draft: {error_msg}"
        
    except Exception as e:
        return f"Error preparing draft: {str(e)}"

