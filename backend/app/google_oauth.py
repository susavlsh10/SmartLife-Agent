import os
import json
from typing import Optional, Dict, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()
# OAuth 2.0 scopes for Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

# OAuth 2.0 client configuration
# These should be set in environment variables or .env file
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/settings/oauth/callback")

# If using OAuth client config from JSON file (alternative approach)
CLIENT_CONFIG = None
if os.getenv("GOOGLE_CLIENT_CONFIG_PATH"):
    try:
        with open(os.getenv("GOOGLE_CLIENT_CONFIG_PATH"), 'r') as f:
            CLIENT_CONFIG = json.load(f)
            if 'installed' in CLIENT_CONFIG:
                CLIENT_CONFIG = CLIENT_CONFIG['installed']
            CLIENT_ID = CLIENT_ID or CLIENT_CONFIG.get('client_id')
            CLIENT_SECRET = CLIENT_SECRET or CLIENT_CONFIG.get('client_secret')
    except Exception as e:
        print(f"Warning: Could not load Google client config: {e}")


def get_oauth_flow(redirect_uri: Optional[str] = None) -> Flow:
    """Create OAuth flow for Google Calendar"""
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError(
            "Google OAuth credentials not configured. "
            "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
        )

    client_config = {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri or REDIRECT_URI]
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri or REDIRECT_URI
    )
    return flow


def get_authorization_url(redirect_uri: Optional[str] = None, state: Optional[str] = None) -> str:
    """Get Google OAuth authorization URL"""
    # print(f"Redirect URI: {redirect_uri}")
    flow = get_oauth_flow(redirect_uri)
    # print(f"Flow: {flow}")
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=state
    )
    print(f"Authorization URL: {authorization_url}")
    return authorization_url


def exchange_code_for_token(
    authorization_code: str,
    redirect_uri: Optional[str] = None
) -> Dict[str, Any]:
    """Exchange authorization code for access token"""
    flow = get_oauth_flow(redirect_uri)
    flow.fetch_token(code=authorization_code)
    
    credentials = flow.credentials
    
    # Convert credentials to dict for storage
    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }
    
    return token_data


def get_user_email_from_token(token_json: str) -> Optional[str]:
    """Get user email from stored token"""
    try:
        token_data = json.loads(token_json)
        credentials = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", SCOPES)
        )
        
        # Refresh if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        
        # Get user info
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        return user_info.get('email')
    except Exception as e:
        print(f"Error getting user email: {e}")
        return None


def refresh_token_if_needed(token_json: str) -> Optional[str]:
    """Refresh token if expired and return updated token JSON"""
    try:
        token_data = json.loads(token_json)
        credentials = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", SCOPES)
        )
        
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            
            # Update token data
            token_data["token"] = credentials.token
            return json.dumps(token_data)
        
        return token_json
    except Exception as e:
        print(f"Error refreshing token: {e}")
        return None

