#!/usr/bin/env python3
"""
Verify Google OAuth credentials are valid
"""
import json
import os
import sys

def verify_credentials():
    """Verify google_credentials.json is valid"""
    creds_file = "gmail/google_credentials.json"
    
    print("🔍 Verifying OAuth Credentials\n")
    
    if not os.path.exists(creds_file):
        print(f"❌ Credentials file not found: {creds_file}")
        print("\n📝 To fix:")
        print("   1. Go to https://console.cloud.google.com/")
        print("   2. Create OAuth 2.0 Client ID (Desktop app)")
        print("   3. Download and save as backend/gmail/google_credentials.json")
        return False
    
    try:
        with open(creds_file, 'r') as f:
            data = json.load(f)
        
        print(f"✅ Credentials file exists: {creds_file}")
        print(f"   Size: {os.path.getsize(creds_file)} bytes\n")
        
        # Check structure
        if "installed" in data:
            client_info = data["installed"]
            print("📋 Credentials Info:")
            print(f"   Type: Desktop Application")
            print(f"   Client ID: {client_info.get('client_id', 'N/A')[:50]}...")
            print(f"   Project ID: {client_info.get('project_id', 'N/A')}")
            print(f"   Auth URI: {client_info.get('auth_uri', 'N/A')}")
            print(f"   Token URI: {client_info.get('token_uri', 'N/A')}")
            
            required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
            missing = [f for f in required_fields if f not in client_info]
            
            if missing:
                print(f"\n⚠️  Missing required fields: {missing}")
                return False
            
            print("\n✅ All required fields present")
            return True
            
        elif "web" in data:
            print("⚠️  Warning: This appears to be a 'Web application' credential")
            print("   For this app, you need 'Desktop app' credentials")
            print("\n📝 To fix:")
            print("   1. Go to Google Cloud Console")
            print("   2. Create new OAuth Client ID")
            print("   3. Select 'Desktop app' as application type")
            print("   4. Download and replace the credentials file")
            return False
        else:
            print("❌ Unknown credentials format")
            print("   Expected 'installed' (Desktop app) or 'web' type")
            return False
            
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in credentials file: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading credentials: {e}")
        return False

def check_tokens():
    """Check if token files exist"""
    print("\n🔑 Checking OAuth Tokens\n")
    
    gmail_token = "gmail/gmail_token.json"
    calendar_token = "gmail/token.json"
    
    if os.path.exists(gmail_token):
        print(f"✅ Gmail token exists: {gmail_token}")
        print(f"   Size: {os.path.getsize(gmail_token)} bytes")
    else:
        print(f"ℹ️  Gmail token not found (will be created on first use)")
    
    if os.path.exists(calendar_token):
        print(f"✅ Calendar token exists: {calendar_token}")
        print(f"   Size: {os.path.getsize(calendar_token)} bytes")
    else:
        print(f"ℹ️  Calendar token not found (will be created on first use)")
    
    if not os.path.exists(gmail_token) and not os.path.exists(calendar_token):
        print("\n📝 Next steps:")
        print("   1. Start the backend: ./start_backend.sh")
        print("   2. Try using a Gmail or Calendar feature")
        print("   3. Browser will open for authorization")
        print("   4. Tokens will be created automatically")

def main():
    print("="*60)
    print("Google OAuth Credentials Verification")
    print("="*60 + "\n")
    
    creds_valid = verify_credentials()
    check_tokens()
    
    print("\n" + "="*60)
    
    if creds_valid:
        print("✅ Credentials are valid!")
        print("\nYou're ready to use Gmail and Calendar features.")
        print("\nTo test:")
        print("  1. Start backend: ./start_backend.sh")
        print("  2. Use a project chat feature that needs OAuth")
        print("  3. Authorize when browser opens")
    else:
        print("⚠️  Please fix the credentials file")
        print("\nSee OAUTH_TROUBLESHOOTING.md for help")
    
    print("="*60)
    
    return 0 if creds_valid else 1

if __name__ == "__main__":
    sys.exit(main())
