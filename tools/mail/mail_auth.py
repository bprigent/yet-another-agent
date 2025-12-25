"""Gmail API authentication module."""

import os
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes required for Gmail API
# Read emails, send emails, compose drafts, and modify emails (for marking as read)
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify'
]

# Global service instance
_gmail_service = None


def get_gmail_service():
    """Get or create an authenticated Gmail service instance.
    
    Handles OAuth 2.0 authentication flow:
    - Loads credentials from token.json if available
    - Refreshes token if expired
    - Prompts for authorization if needed
    - Returns authenticated service object
    
    Returns:
        googleapiclient.discovery.Resource: Authenticated Gmail API service
        
    Raises:
        ValueError: If credentials path is not configured or invalid
        FileNotFoundError: If credentials.json file is not found
    """
    global _gmail_service
    
    if _gmail_service is not None:
        return _gmail_service
    
    # Get paths from environment variables
    # Can use same credentials.json as calendar, or separate Gmail credentials
    creds_path = os.getenv('GOOGLE_GMAIL_CREDENTIALS_PATH', os.getenv('GOOGLE_CALENDAR_CREDENTIALS_PATH', 'credentials.json'))
    token_path = os.getenv('GOOGLE_GMAIL_TOKEN_PATH', 'gmail_token.json')
    
    creds = None
    
    # Load existing token if available
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            # If token is invalid, we'll need to re-authenticate
            print(f"Warning: Could not load token from {token_path}: {e}")
            creds = None
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh expired token
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Warning: Could not refresh token: {e}")
                creds = None
        
        if not creds:
            # Need to authenticate
            if not os.path.exists(creds_path):
                raise FileNotFoundError(
                    f"Credentials file not found at {creds_path}. "
                    "Please download credentials.json from Google Cloud Console "
                    "and place it in the project root or set GOOGLE_GMAIL_CREDENTIALS_PATH."
                )
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                # Check if we're in a headless environment (no display)
                # In Chainlit/server environments, OAuth flow won't work
                import sys
                if not sys.stdout.isatty() or os.getenv('CHAINLIT') or os.getenv('HEADLESS'):
                    raise RuntimeError(
                        "OAuth authentication requires user interaction (browser). "
                        "Please run the authentication flow manually in a terminal first, "
                        "or ensure gmail_token.json exists with valid credentials."
                    )
                creds = flow.run_local_server(port=0)
            except Exception as e:
                # Wrap any OAuth errors in a clear message
                error_msg = str(e)
                if "run_local_server" in error_msg or "OAuth" in error_msg or "browser" in error_msg.lower():
                    raise RuntimeError(
                        "Gmail authentication failed. OAuth requires browser interaction. "
                        "Please authenticate manually by running a script that calls get_gmail_service() "
                        "in a terminal, or ensure gmail_token.json contains valid credentials. "
                        f"Original error: {error_msg}"
                    )
                raise
        
        # Save the credentials for the next run
        try:
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"Warning: Could not save token to {token_path}: {e}")
    
    # Build and return the service
    try:
        _gmail_service = build('gmail', 'v1', credentials=creds)
        return _gmail_service
    except HttpError as e:
        raise ValueError(f"Failed to build Gmail service: {e}")

