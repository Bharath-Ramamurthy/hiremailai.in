import base64
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from core.logger import get_logger
from core.exceptions import SendEmailError

logger = get_logger(__name__)

# Gmail API scope

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

if isinstance(SCOPES, str):
    SCOPES = [s.strip() for s in SCOPES.split(",") if s.strip()]



def get_gmail_service():
    creds = None

    # Corrected variable roles
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")  # client secrets
    token_path = os.getenv("GOOGLE_API_TOKEN")  # stored token file

    # Validate presence
    if not creds_path:
        raise SendEmailError("Missing GOOGLE_APPLICATION_CREDENTIALS environment variable.")
    if not token_path:
        raise SendEmailError("Missing GOOGLE_API_TOKEN environment variable.")

    # Load existing token if available
    if token_path and os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Refresh or obtain new token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save new token
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def send_email_with_attachment(receiver_email, email_subject, email_body_text, resume_path, cover_letter_path=None):
    try:
        service = get_gmail_service()

        # Construct email
        message = MIMEMultipart()
        message['to'] = receiver_email
        message['subject'] = email_subject
        message.attach(MIMEText(email_body_text, "html"))

        # Attach Resume
        attach_file_to_email(message, resume_path, "Resume")

        # Attach Cover Letter (if provided)
        if cover_letter_path:
            attach_file_to_email(message, cover_letter_path, "Cover Letter")

        # Encode and send
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {'raw': raw_message}

        send_result = service.users().messages().send(userId="me", body=body).execute()
        return "Application sent!"

    except Exception as error:
        logger.critical(f"Failed to send application email to {receiver_email}: {str(error)}", exc_info=True)
        raise SendEmailError(f"Could not send email to {receiver_email}") from error


def attach_file_to_email(message, file_path, file_name):
    with open(file_path, 'rb') as f:
        mime_part = MIMEBase('application', 'pdf')
        mime_part.set_payload(f.read())
        encoders.encode_base64(mime_part)
        mime_part.add_header('Content-Disposition', f'attachment; filename={file_name}')
        message.attach(mime_part)
