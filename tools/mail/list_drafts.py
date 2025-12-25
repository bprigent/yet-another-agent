"""Tool to list draft emails."""

from langchain_core.tools import tool
from .mail_auth import get_gmail_service
from email.utils import parseaddr


@tool
def list_drafts(max_results: int = 10) -> str:
    """List draft emails with their ID, subject line, and recipient details.
    
    Use this tool when the user wants to see their draft emails or review drafts before sending.
    
    Args:
        max_results: Maximum number of drafts to return (default: 10, max: 50)
        
    Returns:
        Formatted string with list of drafts including:
        - Draft ID (for use with send_draft tool)
        - Subject line
        - Recipient(s)
        - Snippet/preview of the email
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
        
        # List drafts
        try:
            results = service.users().drafts().list(
                userId='me',
                maxResults=max_results
            ).execute()
            
            drafts = results.get('drafts', [])
            
            if not drafts:
                return "No draft emails found."
            
            # Get details for each draft
            draft_list = []
            for draft_item in drafts:
                draft_id = draft_item.get('id', 'Unknown')
                message_id = draft_item.get('message', {}).get('id', 'Unknown')
                
                # Get full message details
                try:
                    message = service.users().messages().get(
                        userId='me',
                        id=message_id,
                        format='metadata',
                        metadataHeaders=['To', 'Subject', 'Cc', 'Bcc']
                    ).execute()
                    
                    # Extract headers
                    headers = message['payload'].get('headers', [])
                    
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                    to_header = next((h['value'] for h in headers if h['name'] == 'To'), 'No Recipient')
                    cc_header = next((h['value'] for h in headers if h['name'] == 'Cc'), None)
                    
                    # Get snippet if available
                    snippet = message.get('snippet', '')
                    
                    # Format draft entry
                    draft_entry = f"Draft ID: {draft_id}\n"
                    draft_entry += f"  Subject: {subject}\n"
                    draft_entry += f"  To: {to_header}\n"
                    if cc_header:
                        draft_entry += f"  CC: {cc_header}\n"
                    if snippet:
                        draft_entry += f"  Preview: {snippet[:100]}{'...' if len(snippet) > 100 else ''}\n"
                    
                    draft_list.append(draft_entry)
                    
                except Exception as e:
                    # If we can't get details for a specific draft, skip it
                    draft_list.append(f"Draft ID: {draft_id}\n  Error retrieving details: {str(e)}\n")
                    continue
            
            # Build result
            result = f"Found {len(draft_list)} draft email(s):\n\n"
            result += "\n".join(draft_list)
            result += f"\n\nUse the Draft ID with send_draft tool to send a draft."
            
            return result
            
        except Exception as e:
            return f"Error retrieving drafts: {str(e)}"
        
    except Exception as e:
        return f"Error listing drafts: {str(e)}"

