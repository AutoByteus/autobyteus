from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os.path
import json
import webbrowser
import urllib.parse

# Path to your client secret file
CLIENT_SECRET_FILE = '/Users/aswin/Downloads/client_secret_148034928640-8uigm4gqeeljbc50ialsa993c4jodso9.apps.googleusercontent.com.json'
# Token file to save the credentials
TOKEN_FILE = 'token.json'
# Define the scopes your application needs
# Add the specific scopes you need for your application
SCOPES = [
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/drive',
]
# Redirect URI from your client_secret.json
REDIRECT_URI = "https://developers.google.com/oauthplayground"

def get_oauth_url():
    # Load the client secrets file
    with open(CLIENT_SECRET_FILE, 'r') as f:
        client_config = json.load(f)
    
    # Create a flow using client secrets
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    
    # Generate the authorization URL
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        include_granted_scopes='true'
    )
    
    return auth_url, flow

def get_credentials():
    # Generate OAuth URL
    auth_url, flow = get_oauth_url()
    
    # Open the authorization URL in a browser
    print(f"Opening browser to authorize application...")
    print(f"Please authorize the application and copy the authorization code when prompted.")
    webbrowser.open(auth_url)
    
    # Get the authorization code from the user
    auth_code = input("Enter the authorization code: ")
    
    # Exchange the authorization code for credentials
    flow.fetch_token(code=auth_code)
    creds = flow.credentials
    
    # Save the credentials
    with open(TOKEN_FILE, 'w') as token:
        token_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
        token.write(json.dumps(token_data))
    
    # Print refresh token for reference
    print(f"Refresh token: {creds.refresh_token}")
    
    return creds

if __name__ == '__main__':
    credentials = get_credentials()
    print("Authentication successful!")
    print(f"Access token: {credentials.token}")
    print(f"Refresh token: {credentials.refresh_token}")