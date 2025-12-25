"""Tool to create a draft email via Gmail with structured results."""

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langchain_core.tools import tool
import base64
from .mail_auth import get_gmail_service
from tools.core.base_tool import ToolResult, log_tool_call
from tools.schemas import EmailDraftInput


@log_tool_call("create_draft")
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
        # Validate input using Pydantic schema
        try:
            # Parse comma-separated emails
            to_list = [email.strip() for email in to.split(",")] if to else []
            cc_list = [email.strip() for email in cc.split(",")] if cc else []
            bcc_list = [email.strip() for email in bcc.split(",")] if bcc else []
            
            email_input = EmailDraftInput(
                to=to_list[0] if len(to_list) == 1 else to_list,
                subject=subject,
                body=body,
                cc=cc_list if cc_list else None,
                bcc=bcc_list if bcc_list else None,
                is_html=is_html
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Validation error: {str(e)}"
            ).to_string()
        
        # Get Gmail service - wrap in try/except to catch auth errors early
        try:
            service = get_gmail_service()
        except FileNotFoundError as e:
            return ToolResult(
                success=False,
                error=f"Gmail authentication error: {str(e)}. Please ensure credentials.json exists and gmail_token.json is set up."
            ).to_string()
        except RuntimeError as e:
            return ToolResult(
                success=False,
                error=f"Gmail authentication error: {str(e)}"
            ).to_string()
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Gmail service initialization error: {str(e)}"
            ).to_string()
        
        # Create MIME message following official Gmail API pattern
        if email_input.is_html:
            message = MIMEText(email_input.body, 'html')
        else:
            message = MIMEText(email_input.body, 'plain')
        
        # Handle multiple recipients
        to_str = ", ".join(email_input.to) if isinstance(email_input.to, list) else email_input.to
        message['to'] = to_str
        message['subject'] = email_input.subject
        
        if email_input.cc:
            cc_str = ", ".join(email_input.cc) if isinstance(email_input.cc, list) else email_input.cc
            message['cc'] = cc_str
        if email_input.bcc:
            bcc_str = ", ".join(email_input.bcc) if isinstance(email_input.bcc, list) else email_input.bcc
            message['bcc'] = bcc_str
        
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
            
            # Build formatted message for display
            formatted_msg = f"✓ Draft created successfully!\n"
            formatted_msg += f"  Draft ID: {draft_id}\n"
            to_str = ", ".join(email_input.to) if isinstance(email_input.to, list) else email_input.to
            formatted_msg += f"  To: {to_str}\n"
            if email_input.cc:
                cc_str = ", ".join(email_input.cc)
                formatted_msg += f"  CC: {cc_str}\n"
            if email_input.bcc:
                bcc_str = ", ".join(email_input.bcc)
                formatted_msg += f"  BCC: {bcc_str}\n"
            formatted_msg += f"  Subject: {email_input.subject}\n"
            formatted_msg += f"  Message ID: {message_id}\n"
            formatted_msg += f"\nUse the Draft ID with send_draft tool to send this email."
            
            return ToolResult(
                success=True,
                data={
                    "draft_id": draft_id,
                    "message_id": message_id,
                    "to": email_input.to,
                    "subject": email_input.subject,
                    "cc": email_input.cc,
                    "bcc": email_input.bcc,
                    "formatted": formatted_msg
                },
                metadata={"is_html": email_input.is_html}
            ).to_string()
            
        except Exception as e:
            error_msg = str(e)
            # Provide helpful error messages
            if 'invalid' in error_msg.lower() or 'malformed' in error_msg.lower():
                return ToolResult(
                    success=False,
                    error=f"Invalid email address format. Please check the recipient email address(es). Details: {error_msg}"
                ).to_string()
            elif 'quota' in error_msg.lower() or 'limit' in error_msg.lower():
                return ToolResult(
                    success=False,
                    error=f"Gmail quota exceeded. Please try again later. Details: {error_msg}"
                ).to_string()
            else:
                return ToolResult(
                    success=False,
                    error=f"Error creating draft: {error_msg}"
                ).to_string()
        
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Error preparing draft: {str(e)}"
        ).to_string()

