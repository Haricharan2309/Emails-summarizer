#!/usr/bin/env python3
import os
import datetime
from datetime import datetime as dt, time as dtime, timedelta
import base64
import pytz
import openai

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64 as b64

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

#############################
# CONFIGURATION
#############################

# SCOPES: includes 'gmail.readonly' and 'gmail.send'
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

# Update to your own OpenAI API key
openai.api_key = "Get_API_Key_From_OpenAI"

# Google OAuth client JSON file (downloaded from your Google Cloud Console)
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'

# The email address where you want to receive the summary
DESTINATION_EMAIL = 'Your_Email_Address'

# Your local timezone (for strictly "today" in local time)
LOCAL_TIMEZONE = pytz.timezone("America/Los_Angeles")

#############################
# AUTHENTICATION
#############################

def authenticate_gmail():
    """
    Authenticates with the Gmail API using the provided SCOPES.
    Stores the token in token.json to avoid repeated logins.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service

#############################
# HELPER: GET LOCAL MIDNIGHT RANGE
#############################

def get_local_midnight_epochs():
    """
    Returns two Unix timestamps: the start of 'today' and the start of 'tomorrow'
    for your local timezone.
    """
    today_local_date = dt.now(LOCAL_TIMEZONE).date()
    today_local_midnight = LOCAL_TIMEZONE.localize(dt.combine(today_local_date, dtime.min))
    tomorrow_local_midnight = today_local_midnight + timedelta(days=1)

    start_epoch = int(today_local_midnight.timestamp())
    end_epoch = int(tomorrow_local_midnight.timestamp())
    return start_epoch, end_epoch

#############################
# FETCH EMAILS (TODAY) FROM PRIMARY
#############################

def get_todays_emails(service):
    """
    Fetches all emails that arrived strictly today (local midnight to midnight)
    from the inbox's Primary tab. Returns a list of dictionaries:
        { 'from': <sender>, 'subject': <subject>, 'body': <plain_text_body> }
    """
    start_epoch, end_epoch = get_local_midnight_epochs()
    # The query now includes "category:primary" to ensure only Primary emails are fetched.
    query = f"in:inbox category:primary after:{start_epoch} before:{end_epoch}"
    
    response = service.users().messages().list(
        userId='me',
        q=query
    ).execute()

    messages = response.get('messages', [])
    email_list = []

    if not messages:
        return email_list

    for msg in messages:
        msg_id = msg['id']
        # Retrieve metadata (From, Subject)
        meta_result = service.users().messages().get(
            userId='me',
            id=msg_id,
            format='metadata',
            metadataHeaders=['From', 'Subject']
        ).execute()

        headers = meta_result.get('payload', {}).get('headers', [])
        from_field = ''
        subject_field = ''

        for h in headers:
            name = h.get('name', '').lower()
            value = h.get('value', '')
            if name == 'from':
                from_field = value
            elif name == 'subject':
                subject_field = value

        # Retrieve full message to extract the plain text body
        full_result = service.users().messages().get(
            userId='me',
            id=msg_id,
            format='full'
        ).execute()

        body_text = extract_plain_text_body(full_result)

        email_list.append({
            'from': from_field,
            'subject': subject_field,
            'body': body_text
        })

    return email_list

def extract_plain_text_body(msg_data):
    """
    Extracts the plain text body from the message data in 'full' format.
    Falls back to the snippet if no text is found.
    """
    payload = msg_data.get('payload', {})

    def _walk_parts(parts):
        text_segments = []
        for part in parts:
            mime_type = part.get('mimeType', '')
            if mime_type == 'text/plain':
                data = part.get('body', {}).get('data')
                if data:
                    text_segments.append(
                        base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    )
            elif 'parts' in part:
                text_segments.append(_walk_parts(part['parts']))
        return "\n".join(text_segments)

    text_body = ""
    if 'parts' in payload:
        text_body = _walk_parts(payload['parts'])
    else:
        data = payload.get('body', {}).get('data')
        if data:
            text_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

    if not text_body.strip():
        text_body = msg_data.get('snippet', '')
    return text_body

#############################
# SUMMARIZE VIA OPENAI
#############################

def summarize_emails(email_list):
    """
    Summarizes each email using GPT-4. The summary includes:
      - Sender (From)
      - Subject
      - A short summary of the body text
      - Any mention of meetings, schedules, or deadlines
    """
    if not email_list:
        return "No emails received today."

    combined_text = []
    for i, email_data in enumerate(email_list, start=1):
        text_block = (
            f"Email #{i}\n"
            f"From: {email_data['from']}\n"
            f"Subject: {email_data['subject']}\n"
            f"Body:\n{email_data['body']}\n"
            "----\n"
        )
        combined_text.append(text_block)

    full_text = "\n".join(combined_text)
    # Truncate if the text is too large
    max_input_length = 8000
    truncated_text = full_text[:max_input_length]

    system_message = "You are a helpful email summarization assistant."
    user_prompt = (
        "Below are emails received strictly today. For each email, please provide:\n"
        "- Who it is from\n"
        "- The subject\n"
        "- A short, clear summary of the body\n"
        "- Any mention of meetings, schedules, or deadlines\n\n"
        f"{truncated_text}\n\n"
        "Format your summary in a well-structured and readable way (e.g., using bullet points or numbering)."
    )

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=500,
        temperature=0.5
    )
    summary_text = response["choices"][0]["message"]["content"].strip()
    return summary_text

#############################
# SEND EMAIL
#############################

def send_email(service, sender, to, subject, body_text):
    """
    Sends an email using the Gmail API.
    """
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    message.attach(MIMEText(body_text, 'plain'))

    raw_message = b64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    result = service.users().messages().send(
        userId='me',
        body={'raw': raw_message}
    ).execute()
    return result

#############################
# MAIN PROCESS
#############################

def run_email_summary():
    """
    1) Authenticates and fetches today's Primary emails,
    2) Summarizes them using GPT-4,
    3) Sends the summary to your designated email.
    """
    service = authenticate_gmail()
    email_list = get_todays_emails(service)
    
    # Create a summary even if there are no emails (the summarizer returns a simple message)
    summary = summarize_emails(email_list)
    print("====== TODAY'S EMAIL SUMMARY ======")
    print(summary)

    subject = "[Daily Summary] Today's Emails"
    send_email(
        service=service,
        sender='me',
        to=DESTINATION_EMAIL,
        subject=subject,
        body_text=summary
    )
    print(f"\nSummary email sent to {DESTINATION_EMAIL}!")

def main():
    run_email_summary()

if __name__ == '__main__':
    main()
