from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os
import json
import base64

# IMPORTANT: Allow HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add a test endpoint
@app.get("/test")
async def test():
    return {"message": "Backend is working!", "status": "ok"}

# Configuration
CLIENT_SECRET_PATH = '../client_secret.json'
REDIRECT_URI = 'http://localhost:8080/callback'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/userinfo.email', 'openid']
TOKEN_FILE = 'token.json'

def get_flow():
    return Flow.from_client_secrets_file(
        CLIENT_SECRET_PATH,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

def load_credentials():
    """Load credentials from token file"""
    if not os.path.exists(TOKEN_FILE):
        return None
    
    try:
        with open(TOKEN_FILE, 'r') as token_file:
            creds_data = json.load(token_file)
        
        creds = Credentials(
            token=creds_data['token'],
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data['token_uri'],
            client_id=creds_data['client_id'],
            client_secret=creds_data['client_secret'],
            scopes=creds_data['scopes']
        )
        
        # Refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
            # Save updated credentials
            save_credentials(creds)
        
        return creds
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None

def save_credentials(creds):
    """Save credentials to token file"""
    creds_dict = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }
    
    with open(TOKEN_FILE, 'w') as token_file:
        json.dump(creds_dict, token_file)

@app.get("/auth")
async def auth():
    """Get authorization URL"""
    flow = get_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    return {
        "authorization_url": authorization_url,
        "state": state
    }

@app.get("/callback")
async def callback(request: Request):
    """Handle OAuth callback"""
    flow = get_flow()
    
    try:
        flow.fetch_token(authorization_response=str(request.url))
        credentials = flow.credentials
        save_credentials(credentials)
        
        return {"success": True, "message": "Authentication successful!"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/status")
async def status():
    """Check authentication status"""
    creds = load_credentials()
    if creds and creds.valid:
        return {"authenticated": True, "message": "Ready to access Gmail"}
    else:
        return {"authenticated": False, "message": "Not authenticated"}

@app.get("/emails")
async def get_emails(limit: int = 10):
    """Get list of emails"""
    creds = load_credentials()
    if not creds or not creds.valid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        
        # Get list of messages
        results = service.users().messages().list(
            userId='me', 
            maxResults=limit
        ).execute()
        
        messages = results.get('messages', [])
        
        email_list = []
        for message in messages:
            # Get message details
            msg = service.users().messages().get(
                userId='me', 
                id=message['id']
            ).execute()
            
            # Extract headers
            headers = msg['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
            
            email_list.append({
                'id': message['id'],
                'subject': subject,
                'sender': sender,
                'date': date,
                'snippet': msg.get('snippet', '')
            })
        
        return {"emails": email_list}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/email/{email_id}")
async def get_email(email_id: str):
    """Get specific email content"""
    creds = load_credentials()
    if not creds or not creds.valid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        
        # Get message
        message = service.users().messages().get(
            userId='me', 
            id=email_id,
            format='full'
        ).execute()
        
        # Extract headers
        headers = message['payload'].get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
        to = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown Recipient')
        
        # Extract body
        def extract_body(payload):
            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body']['data']
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
                    elif part['mimeType'] == 'text/html':
                        data = part['body']['data']
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
            else:
                if payload['body'].get('data'):
                    body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            return body
        
        body = extract_body(message['payload'])
        
        return {
            "id": email_id,
            "subject": subject,
            "sender": sender,
            "to": to,
            "date": date,
            "body": body,
            "snippet": message.get('snippet', '')
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

