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
            
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
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

