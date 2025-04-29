import os
import csv
import base64
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email import message_from_bytes

# ——— Configuration —————————————————————————————————————————————
SCOPES            = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_PATH        = 'token.json'
CREDENTIALS_PATH  = os.getenv('GOOGLE_CREDENTIALS', 'credentials.json')
BOUNCE_LOOKBACK   = int(os.getenv('BOUNCE_LOOKBACK_DAYS', 1))
CONTACTS_CSV_PATH = os.getenv('CONTACTS_FILE', 'contacts/contacts.csv')


def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())
        print(f"Saved new token to {TOKEN_PATH}")

    return build('gmail', 'v1', credentials=creds)


def load_contacts(path):
    with open(path, newline='', encoding='utf-8') as f:
        reader   = csv.DictReader(f)
        contacts = list(reader)
        fields   = reader.fieldnames[:] if reader.fieldnames else []
    return contacts, fields


def save_contacts(path, contacts, fieldnames):
    if 'error' not in fieldnames:
        fieldnames.append('error')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(contacts)


def extract_failed_addresses(raw_bytes):
    msg    = message_from_bytes(raw_bytes)
    failed = set()

    # 1) Official DSN part
    for part in msg.walk():
        if part.get_content_type() == 'message/delivery-status':
            payload = part.get_payload(decode=True) or b''
            text    = payload.decode(errors='ignore')
            for m in re.findall(r'Final-Recipient:.*?;\s*([\w\.\+\-@]+)', text):
                failed.add(m.strip())

    # 2) Fallback free-text scan
    if not failed:
        full = raw_bytes.decode(errors='ignore')
        for m in re.findall(
            r"delivered to\s+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
            full,
            flags=re.IGNORECASE
        ):
            failed.add(m)

    return failed

def main():
    load_dotenv()
    contacts, fieldnames = load_contacts(CONTACTS_CSV_PATH)
    service             = get_gmail_service()

    # Build a broad query: any mailer-daemon message in the last N days
    since = (datetime.utcnow() - timedelta(days=BOUNCE_LOOKBACK)).strftime('%Y/%m/%d')
    query = f'after:{since} from:mailer-daemon'
    print("Searching for bounce candidates with query:", query)

    resp = service.users().messages().list(userId='me', q=query).execute()
    msgs = resp.get('messages', [])

    if not msgs:
        print("No mailer-daemon messages found in that window.")
        return

    # Client-side filter: require 'address not found' in snippet
    candidate_ids = []
    for m in msgs:
        meta    = service.users().messages().get(
            userId='me', id=m['id'], format='metadata', metadataHeaders=[]
        ).execute()
        snippet = meta.get('snippet', '').lower()
        if 'address not found' in snippet:
            candidate_ids.append(m['id'])

    if not candidate_ids:
        print("Found mailer-daemon messages, but none mention 'address not found'.")
        return

    # Fetch and parse DSN for each candidate
    failed = set()
    for msg_id in candidate_ids:
        raw = service.users().messages().get(
            userId='me', id=msg_id, format='raw'
        ).execute().get('raw', '')
        if not raw:
            continue
        data = base64.urlsafe_b64decode(raw.encode('ASCII'))
        failed |= extract_failed_addresses(data)

    if not failed:
        print("No failed recipient addresses parsed from DSNs.")
        return

    print("Detected bounced addresses:", ', '.join(failed))

    # Mark contacts accordingly
    for c in contacts:
        if c.get('email') in failed:
            c['sent']  = 'no'
            c['error'] = 'bounced (Address not found)'
            print(f"  ↳ Marking {c['email']} as bounced")

    save_contacts(CONTACTS_CSV_PATH, contacts, fieldnames)
    print("contacts.csv updated with bounce info.")


if __name__ == '__main__':
    main()
