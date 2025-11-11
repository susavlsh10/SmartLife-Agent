#!/usr/bin/env python3
"""
Google OAuth Authentication Script for SmartLife Agent

Run this script to authenticate with Google services (Gmail and Calendar)
BEFORE starting the backend server.

Usage:
    python authenticate_google.py
    
Or with UV:
    uv run python authenticate_google.py
"""

import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Add gmail directory to path if needed
GMAIL_DIR = os.path.join(os.path.dirname(__file__), 'gmail')

# Gmail and Calendar scopes
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.send']
CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']

def authenticate_service(service_name, scopes, token_file, credentials_file):
    """Authenticate with a Google service"""
    print(f"\n{'='*60}")
    print(f"Authenticating {service_name}")
    print('='*60)
    
    creds = None
    
    # Load existing token
    if os.path.exists(token_file):
        print(f"✓ Found existing token: {token_file}")
        try:
            creds = Credentials.from_authorized_user_file(token_file, scopes)
            print("✓ Token loaded successfully")
        except Exception as e:
            print(f"⚠ Failed to load token: {e}")
            print("  Will create new token...")
            creds = None

    # Check if credentials are valid
    if creds and creds.valid:
        print(f"✅ {service_name} is already authenticated!")
        print(f"   Token file: {token_file}")
        return True
    
    # Refresh expired token
    if creds and creds.expired and creds.refresh_token:
        try:
            print("⟳ Refreshing expired token...")
            creds.refresh(Request())
            print("✓ Token refreshed successfully")
        except Exception as e:
            print(f"✗ Failed to refresh token: {e}")
            print("  Will create new token...")
            creds = None
    
    # Create new token
    if not creds:
        if not os.path.exists(credentials_file):
            print(f"\n❌ ERROR: Credentials file not found!")
            print(f"   Expected: {credentials_file}")
            print(f"\n   📝 To fix:")
            print(f"   1. Go to https://console.cloud.google.com/")
            print(f"   2. Create OAuth 2.0 Client ID (Desktop app)")
            print(f"   3. Download credentials")
            print(f"   4. Save as: {credentials_file}")
            return False
        
        print(f"\n🔐 Starting OAuth flow for {service_name}...")
        print(f"   A browser window will open")
        print(f"   Please sign in and grant permissions")
        print()
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
            creds = flow.run_local_server(port=0, open_browser=True)
            print(f"\n✅ Authentication successful!")
        except Exception as e:
            print(f"\n❌ Authentication failed: {e}")
            return False
    
    # Save token
    try:
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        print(f"✓ Token saved: {token_file}")
    except Exception as e:
        print(f"⚠ Failed to save token: {e}")
        return False
    
    print(f"✅ {service_name} authentication complete!")
    return True

def main():
    """Main authentication flow"""
    print("\n" + "="*60)
    print("SmartLife Agent - Google OAuth Authentication")
    print("="*60)
    
    # Check credentials file
    credentials_file = os.path.join(GMAIL_DIR, 'google_credentials.json')
    
    if not os.path.exists(GMAIL_DIR):
        print(f"\n❌ Gmail directory not found: {GMAIL_DIR}")
        print("   Creating directory...")
        os.makedirs(GMAIL_DIR, exist_ok=True)
    
    if not os.path.exists(credentials_file):
        print(f"\n❌ ERROR: OAuth credentials not found!")
        print(f"   Expected: {credentials_file}")
        print(f"\n   📋 Setup Instructions:")
        print(f"   1. Go to https://console.cloud.google.com/")
        print(f"   2. Navigate to 'APIs & Services' > 'Credentials'")
        print(f"   3. Click '+ CREATE CREDENTIALS' > 'OAuth client ID'")
        print(f"   4. Select 'Desktop app' as application type")
        print(f"   5. Download the JSON file")
        print(f"   6. Save it as: {credentials_file}")
        print(f"\n   Then run this script again.")
        return 1
    
    print(f"\n✓ Found credentials file: {credentials_file}")
    
    # Authenticate Gmail
    gmail_token = os.path.join(GMAIL_DIR, 'gmail_token.json')
    gmail_success = authenticate_service(
        "Gmail",
        GMAIL_SCOPES,
        gmail_token,
        credentials_file
    )
    
    # Authenticate Calendar
    calendar_token = os.path.join(GMAIL_DIR, 'token.json')
    calendar_success = authenticate_service(
        "Google Calendar",
        CALENDAR_SCOPES,
        calendar_token,
        credentials_file
    )
    
    # Summary
    print(f"\n" + "="*60)
    print("Authentication Summary")
    print("="*60)
    print(f"Gmail:    {'✅ Ready' if gmail_success else '❌ Failed'}")
    print(f"Calendar: {'✅ Ready' if calendar_success else '❌ Failed'}")
    
    if gmail_success and calendar_success:
        print(f"\n🎉 All services authenticated successfully!")
        print(f"\n📁 Token files created:")
        print(f"   {gmail_token}")
        print(f"   {calendar_token}")
        print(f"\n🚀 You can now start the backend server:")
        print(f"   cd backend")
        print(f"   ./start_backend.sh")
        print("="*60 + "\n")
        return 0
    else:
        print(f"\n⚠ Some services failed to authenticate")
        print(f"   See errors above for details")
        print("="*60 + "\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
