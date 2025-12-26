"""Tool to mark emails as read."""

from typing import List, Union
from langchain_core.tools import tool
from .mail_auth import get_gmail_service
from tools.core.base_tool import ToolResult, log_tool_call, ensure_string_result


@tool
@ensure_string_result
@log_tool_call("mark_as_read")
def mark_as_read(message_ids: Union[str, List[str]]) -> ToolResult:
    """Mark one or more emails as read by their message IDs.
    
    Use this tool when the user wants to mark emails as read. You can mark a single email
    or multiple emails at once. The email IDs can be obtained from get_unread_emails or
    other email listing tools.
    
    Args:
        message_ids: A single message ID (string) or a list of message IDs to mark as read
        
    Returns:
        Success message indicating how many emails were marked as read, or an error message
    """
    try:
        # Normalize input to a list
        if isinstance(message_ids, str):
            message_ids = [message_ids]
        elif not isinstance(message_ids, list):
            return ToolResult(
                success=False,
                error=f"Error: message_ids must be a string or list of strings, got {type(message_ids)}"
            )
        
        # Validate that we have at least one message ID
        if not message_ids:
            return ToolResult(
                success=False,
                error="Error: At least one message ID is required."
            )
        
        # Filter out empty strings
        message_ids = [msg_id.strip() for msg_id in message_ids if msg_id and msg_id.strip()]
        
        if not message_ids:
            return ToolResult(
                success=False,
                error="Error: No valid message IDs provided."
            )
        
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
        
        # Mark messages as read using batchModify
        try:
            batch_body = {
                'ids': message_ids,
                'removeLabelIds': ['UNREAD']
            }
            
            service.users().messages().batchModify(
                userId='me',
                body=batch_body
            ).execute()
            
            count = len(message_ids)
            if count == 1:
                return ToolResult(
                    success=True,
                    data=f"Successfully marked 1 email as read (ID: {message_ids[0]})."
                )
            else:
                return ToolResult(
                    success=True,
                    data=f"Successfully marked {count} emails as read."
                )
                
        except Exception as e:
            error_msg = str(e)
            # Provide more helpful error messages
            if '404' in error_msg or 'not found' in error_msg.lower():
                return ToolResult(
                    success=False,
                    error="Error: One or more email IDs not found. Please verify the message IDs are correct."
                )
            elif '403' in error_msg or 'permission' in error_msg.lower():
                return ToolResult(
                    success=False,
                    error="Error: Permission denied. Please ensure the Gmail API has modify permissions."
                )
            else:
                return ToolResult(
                    success=False,
                    error=f"Error marking emails as read: {error_msg}"
                )
        
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Error marking emails as read: {str(e)}"
        )

