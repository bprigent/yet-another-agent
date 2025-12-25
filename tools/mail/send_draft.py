"""Tool to send a draft email via Gmail."""

from langchain_core.tools import tool
from .mail_auth import get_gmail_service


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
        if not draft_id or not draft_id.strip():
            return "Error: Draft ID is required."
        
        # Get Gmail service - wrap in try/except to catch auth errors early
        try:
            service = get_gmail_service()
        except FileNotFoundError as e:
            return f"Gmail authentication error: {str(e)}. Please ensure credentials.json exists and gmail_token.json is set up."
        except RuntimeError as e:
            return f"Gmail authentication error: {str(e)}"
        except Exception as e:
            return f"Gmail service initialization error: {str(e)}"
        
        # Send the draft
        try:
            send_result = service.users().drafts().send(
                userId='me',
                body={'id': draft_id}
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
                
                result = f"✓ Email sent successfully!\n"
                result += f"  Draft ID: {draft_id}\n"
                result += f"  To: {to_header}\n"
                if cc_header:
                    result += f"  CC: {cc_header}\n"
                if bcc_header:
                    result += f"  BCC: {bcc_header}\n"
                result += f"  Subject: {subject}\n"
                result += f"  Message ID: {message_id}\n"
                result += f"  Thread ID: {thread_id}"
                
            except Exception:
                # If we can't get message details, still report success
                result = f"✓ Email sent successfully!\n"
                result += f"  Draft ID: {draft_id}\n"
                result += f"  Message ID: {message_id}\n"
                result += f"  Thread ID: {thread_id}"
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            # Provide helpful error messages
            if '404' in error_msg or 'not found' in error_msg.lower():
                return f"Error sending draft: Draft with ID '{draft_id}' not found. It may have been deleted or the ID is incorrect."
            elif 'quota' in error_msg.lower() or 'limit' in error_msg.lower():
                return f"Error sending draft: Gmail sending quota exceeded. Please try again later. Details: {error_msg}"
            else:
                return f"Error sending draft: {error_msg}"
        
    except Exception as e:
        return f"Error sending draft: {str(e)}"

