import json
import base64
import os
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Define scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_user(client_secret_path, token_path):
    """
    Authenticates the user and returns the Gmail API service object.

    Args:
        client_secret_path (str): Path to the client secret JSON file.
        token_path (str): Path to the token JSON file for storing credentials.

    Returns:
        service: An authenticated Gmail API service object.
    """
    creds = None

    # Check if token file exists
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # If no valid credentials are available, perform the OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            creds = flow.run_local_server(port=8080)

        # Save the credentials for future use
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())

    # Build and return the Gmail API client
    return build('gmail', 'v1', credentials=creds)

def extract_original_content(body):
    """
    Extracts only the original content from the email body by removing quoted text,
    email signatures, and other common patterns found in email threads.

    Args:
        body (str): The email body.

    Returns:
        str: The email body with only the original content.
    """
    # Split the email into lines
    lines = body.splitlines()
    clean_lines = []
    in_quoted_section = False
    in_signature = False
    
    # Common patterns that indicate quoted text or signatures
    quote_patterns = [
        r'^>',                                             # Lines starting with '>'
        r'^On .* wrote:$',                                 # Common start of quoted text
        r'^On .* at .* wrote:$',                           # Variation of start of quoted text
        r'^On .* at .*, .* wrote:$',                       # Extended variation
        r'^On .* at .* <.*?> wrote:$',                     # With email address
        r'^-+Original Message-+$',                         # Original message separator
        r'^From:.*$',                                      # Forwarded message header
        r'^Sent:.*$',                                      # Forwarded message header
        r'^To:.*$',                                        # Forwarded message header
        r'^Subject:.*$',                                   # Forwarded message header
        r'^-+ Forwarded message -+$',                      # Gmail forwarded marker
        r'^_+$',                                           # Underline separator
        r'^-+$'                                            # Dash separator
    ]
    
    # Common signature indicators
    signature_patterns = [
        r'^-- $',                                          # Standard signature delimiter
        r'^Best,?$',                                       # Common closing
        r'^Regards,?$',                                    # Common closing
        r'^Sincerely,?$',                                  # Common closing
        r'^Thanks,?$',                                     # Common closing
        r'^Thank you,?$',                                  # Common closing
        r'^Cheers,?$',                                     # Common closing
    ]
    
    # Combine all patterns
    combined_quote_pattern = '|'.join(quote_patterns)
    
    for line in lines:
        # Check if this line starts a quoted section
        if re.match(combined_quote_pattern, line.strip()):
            in_quoted_section = True
            continue
            
        # Check if this line is part of a signature
        if any(re.match(pattern, line.strip()) for pattern in signature_patterns):
            in_signature = True
            continue
            
        # Skip empty lines following quote markers or in signature sections
        if (in_quoted_section or in_signature) and not line.strip():
            continue
            
        # Lines with actual content can reset the quoted section flag
        if line.strip() and in_quoted_section:
            # Only reset if this doesn't look like a quoted line
            if not line.strip().startswith('>') and not re.match(combined_quote_pattern, line.strip()):
                in_quoted_section = False
                
        # If we're not in a quoted section or signature section, add the line
        if not in_quoted_section and not in_signature:
            clean_lines.append(line)
    
    # Join the clean lines back into text
    clean_body = '\n'.join(clean_lines)
    
    # Additional cleanup for specific common patterns we might have missed
    clean_body = re.sub(r'.*forwarded message.*', '', clean_body, flags=re.IGNORECASE)
    clean_body = re.sub(r'Sent from.*', '', clean_body, flags=re.IGNORECASE)
    clean_body = re.sub(r'Get Outlook for.*', '', clean_body, flags=re.IGNORECASE)
    clean_body = re.sub(r'\n\s*\n\s*\n+', '\n\n', clean_body)
    
    return clean_body.strip()

def baseDataFetch(client_secret_path, token_path, output_file, max_valid_emails=100, exclude_labels=None):
    """
    Fetches email data from the Gmail API and saves it to a JSON file.

    Args:
        client_secret_path (str): Path to the client secret JSON file.
        token_path (str): Path to the token JSON file for storing credentials.
        output_file (str): Path to the output JSON file.
        max_valid_emails (int): Maximum number of valid emails to fetch.
        exclude_labels (list): List of labels to exclude from the search.
    """
    if exclude_labels is None:
        exclude_labels = ['DRAFT', 'CHAT']
        
    service = authenticate_user(client_secret_path, token_path)
    email_data = []
    valid_email_count = 0
    next_page_token = None
    exclude_query = ' '.join([f'-label:{label}' for label in exclude_labels])
    query = f'from:me {exclude_query}'

    while valid_email_count < max_valid_emails:
        results = service.users().messages().list(
            userId='me',
            labelIds=['SENT'],
            q=query,
            maxResults=100,
            pageToken=next_page_token
        ).execute()
        messages = results.get('messages', [])
        
        if not messages:
            print("No more messages found.")
            break
            
        next_page_token = results.get('nextPageToken')

        for msg in messages:
            if valid_email_count >= max_valid_emails:
                break

            msg_detail = service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = msg_detail.get('payload', {})
            headers = payload.get('headers', [])
            
            subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No Subject')
            to = next((header['value'] for header in headers if header['name'].lower() == 'to'), 'Unknown Recipient')
            
            if "unsubscribe" in subject.lower():
                continue
            
            body = ''
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain' and 'data' in part.get('body', {}):
                        body = part['body']['data']
                        break
                    elif 'parts' in part:
                        for subpart in part['parts']:
                            if subpart['mimeType'] == 'text/plain' and 'data' in subpart.get('body', {}):
                                body = subpart['body']['data']
                                break
            elif 'body' in payload and 'data' in payload['body']:
                body = payload['body']['data']
            
            if body:
                try:
                    body = base64.urlsafe_b64decode(body).decode('utf-8', errors='ignore')
                except (ValueError, UnicodeDecodeError):
                    try:
                        body = base64.urlsafe_b64decode(body).decode('latin-1', errors='ignore')
                    except Exception as e:
                        print(f"Error decoding email body: {e}")
                        continue

            clean_body = extract_original_content(body)

            if not clean_body.strip():
                continue

            subject = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', subject)
            subject = re.sub(r'https?://\S+|www\.\S+', '', subject)
            clean_body = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', clean_body)
            clean_body = re.sub(r'https?://\S+|www\.\S+', '', clean_body)

            email_data.append({
                'subject': subject.strip(),
                'body': clean_body.strip(),

                'date': next((header['value'] for header in headers if header['name'].lower() == 'date'), 'Unknown Date')
            })
            valid_email_count += 1
            
            if valid_email_count % 10 == 0:
                print(f"Processed {valid_email_count} emails...")

        if not next_page_token:
            break

    with open(output_file, 'w', encoding='utf-8') as json_file:
        json.dump(email_data, json_file, indent=4, ensure_ascii=False)

    print(f"Email data saved to '{output_file}' with {valid_email_count} valid emails.")

if __name__ == "__main__":
    CLIENT_SECRET_PATH = '../client_secret.json'
    TOKEN_PATH = 'token.json'
    OUTPUT_FILE = 'sent_emails.json'
    MAX_VALID_EMAILS = 100
    EXCLUDE_LABELS = ['DRAFT', 'CHAT', 'CATEGORY_PROMOTIONS', 'CATEGORY_SOCIAL']

    baseDataFetch(CLIENT_SECRET_PATH, TOKEN_PATH, OUTPUT_FILE, MAX_VALID_EMAILS, EXCLUDE_LABELS)
