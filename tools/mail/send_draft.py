"""Tool to send a draft email via Gmail with structured results."""

from langchain_core.tools import tool
from .mail_auth import get_gmail_service
from tools.core.base_tool import ToolResult, log_tool_call
from pydantic import BaseModel, Field


class DraftIdInput(BaseModel):
    """Input schema for draft ID validation."""
    draft_id: str = Field(..., min_length=1, description="Gmail draft ID")


@log_tool_call("send_draft")
@tool
def send_draft(draft_id: str) -> str:
    """Send a draft email by its draft ID.
    
    Use this tool when the user wants to send a draft email that was previously created.
    The draft ID can be obtained from create_draft or list_drafts tools.
    
    Args:
        draft_id: The Gmail draft ID (obtained from create_draft or list_drafts)
        
    Returns:
        Success message with sent email details, or error message
    """
    try:
        # Validate input
        try:
            input_data = DraftIdInput(draft_id=draft_id)
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
        
        # Send the draft
        try:
            send_result = service.users().drafts().send(
                userId='me',
                body={'id': input_data.draft_id}
            ).execute()
            
            message_id = send_result.get('id', 'Unknown')
            thread_id = send_result.get('threadId', 'Unknown')
            
            # Get message details for confirmation
            try:
                message = service.users().messages().get(
                    userId='me',
                    id=message_id,
                    format='metadata',
                    metadataHeaders=['To', 'Subject', 'Cc', 'Bcc']
                ).execute()
                
                headers = message['payload'].get('headers', [])
                to_header = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown')
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                cc_header = next((h['value'] for h in headers if h['name'] == 'Cc'), None)
                bcc_header = next((h['value'] for h in headers if h['name'] == 'Bcc'), None)
                
                formatted_msg = f"✓ Email sent successfully!\n"
                formatted_msg += f"  Draft ID: {input_data.draft_id}\n"
                formatted_msg += f"  To: {to_header}\n"
                if cc_header:
                    formatted_msg += f"  CC: {cc_header}\n"
                if bcc_header:
                    formatted_msg += f"  BCC: {bcc_header}\n"
                formatted_msg += f"  Subject: {subject}\n"
                formatted_msg += f"  Message ID: {message_id}\n"
                formatted_msg += f"  Thread ID: {thread_id}"
                
                return ToolResult(
                    success=True,
                    data={
                        "draft_id": input_data.draft_id,
                        "message_id": message_id,
                        "thread_id": thread_id,
                        "to": to_header,
                        "subject": subject,
                        "cc": cc_header,
                        "bcc": bcc_header,
                        "formatted": formatted_msg
                    }
                ).to_string()
                
            except Exception:
                # If we can't get message details, still report success
                formatted_msg = f"✓ Email sent successfully!\n"
                formatted_msg += f"  Draft ID: {input_data.draft_id}\n"
                formatted_msg += f"  Message ID: {message_id}\n"
                formatted_msg += f"  Thread ID: {thread_id}"
                
                return ToolResult(
                    success=True,
                    data={
                        "draft_id": input_data.draft_id,
                        "message_id": message_id,
                        "thread_id": thread_id,
                        "formatted": formatted_msg
                    }
                ).to_string()
            
        except Exception as e:
            error_msg = str(e)
            # Provide helpful error messages
            if '404' in error_msg or 'not found' in error_msg.lower():
                return ToolResult(
                    success=False,
                    error=f"Draft with ID '{input_data.draft_id}' not found. It may have been deleted or the ID is incorrect."
                ).to_string()
            elif 'quota' in error_msg.lower() or 'limit' in error_msg.lower():
                return ToolResult(
                    success=False,
                    error=f"Gmail sending quota exceeded. Please try again later. Details: {error_msg}"
                ).to_string()
            else:
                return ToolResult(
                    success=False,
                    error=f"Error sending draft: {error_msg}"
                ).to_string()
        
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Error sending draft: {str(e)}"
        ).to_string()

