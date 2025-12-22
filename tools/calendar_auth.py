"""Google Calendar API authentication module."""

import os
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes required for Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Global service instance
_calendar_service = None


def get_calendar_service():
    """Get or create an authenticated Google Calendar service instance.
    
    Handles OAuth 2.0 authentication flow:
    - Loads credentials from token.json if available
    - Refreshes token if expired
    - Prompts for authorization if needed
    - Returns authenticated service object
    
    Returns:
        googleapiclient.discovery.Resource: Authenticated Calendar API service
        
    Raises:
        ValueError: If credentials path is not configured or invalid
        FileNotFoundError: If credentials.json file is not found
    """
    global _calendar_service
    
    if _calendar_service is not None:
        return _calendar_service
    
    # Get paths from environment variables
    creds_path = os.getenv('GOOGLE_CALENDAR_CREDENTIALS_PATH', 'credentials.json')
    token_path = os.getenv('GOOGLE_CALENDAR_TOKEN_PATH', 'token.json')
    
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
                    "and place it in the project root or set GOOGLE_CALENDAR_CREDENTIALS_PATH."
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
                        "or ensure token.json exists with valid credentials."
                    )
                creds = flow.run_local_server(port=0)
            except Exception as e:
                # Wrap any OAuth errors in a clear message
                error_msg = str(e)
                if "run_local_server" in error_msg or "OAuth" in error_msg or "browser" in error_msg.lower():
                    raise RuntimeError(
                        "Calendar authentication failed. OAuth requires browser interaction. "
                        "Please authenticate manually by running a script that calls get_calendar_service() "
                        "in a terminal, or ensure token.json contains valid credentials. "
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
        _calendar_service = build('calendar', 'v3', credentials=creds)
        return _calendar_service
    except HttpError as e:
        raise ValueError(f"Failed to build Calendar service: {e}")

