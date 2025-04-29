import os
import time
import csv
import logging
from datetime import datetime
from dotenv import load_dotenv
import dns.resolver
from dns.exception import DNSException

from renderer import render_template
from sender import send_email

def load_contacts(path):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames[:] if reader.fieldnames else []
        contacts = []
        for row in reader:
            row.setdefault('sent',    'no')
            row.setdefault('sent_at', '')
            row.setdefault('error',   '')
            contacts.append(row)
        return contacts, fieldnames

def save_contacts(path, contacts, fieldnames):
    header = list(fieldnames)
    for col in ('sent', 'sent_at', 'error'):
        if col not in header:
            header.append(col)
    # dedupe
    unique_header = []
    for col in header:
        if col not in unique_header:
            unique_header.append(col)

    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=unique_header)
        writer.writeheader()
        writer.writerows(contacts)

def pick_paths(domain, templates_dir, attachments_dir):
    tpl = os.path.join(templates_dir, f"{domain}.j2")
    if not os.path.isfile(tpl):
        tpl = os.path.join(templates_dir, "default.j2")
    resume = os.path.join(attachments_dir, f"{domain}_resume.pdf")
    if not os.path.isfile(resume):
        resume = os.path.join(attachments_dir, "default_resume.pdf")
    return tpl, resume

def has_mx_record(domain: str) -> bool:
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        return bool(answers)
    except (DNSException, Exception):
        return False

def main():
    root = os.path.dirname(os.path.dirname(__file__))
    load_dotenv(os.path.join(root, ".env"))

    contacts_path   = os.getenv("CONTACTS_FILE",    os.path.join(root, "contacts/contacts.csv"))
    templates_dir   = os.getenv("TEMPLATES_DIR",    os.path.join(root, "templates"))
    attachments_dir = os.getenv("ATTACHMENTS_DIR",  os.path.join(root, "attachments"))
    logs_dir        = os.path.join(root, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    batch_size     = int(os.getenv("BATCH_SIZE",        5))
    pause_interval = int(os.getenv("PAUSE_INTERVAL", 1800))
    total_limit    = int(os.getenv("TOTAL_PER_NIGHT", batch_size))

    # configure logging
    log_file = os.path.join(logs_dir, "send.log")
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.info("=== Starting send run ===")

    contacts, fieldnames = load_contacts(contacts_path)

    sent = batch = 0

    for c in contacts:
        # skip already sent
        if c['sent'].lower() == 'yes':
            continue

        # respect nightly cap
        if sent >= total_limit:
            logging.info(f"Reached nightly limit ({total_limit}), stopping.")
            break

        recipient = c["email"]
        domain = recipient.split("@")[-1]

        # MX pre-validation
        if not has_mx_record(domain):
            c["error"] = f"No MX record for domain '{domain}'"
            print(":)", f"{recipient} skipped — no MX record for {domain}")
            logging.error(f"{recipient} — no MX record for {domain}")
            continue

        tpl_path, resume_path = pick_paths(c.get("domain", "default"), templates_dir, attachments_dir)
        subject, body = render_template(tpl_path, **c)

        try:
            send_email(
                to_address=recipient,
                subject=subject,
                body=body,
                attachments=[resume_path]
            )
            # mark success
            c["sent"]    = "yes"
            c["sent_at"] = datetime.utcnow().isoformat()
            c["error"]   = ""
            sent += 1
            batch += 1

            msg = f"Sent to {recipient} (batch {batch}/{batch_size}, total {sent}/{total_limit})"
            print(":)", msg)
            logging.info(msg)

        except Exception as e:
            c["error"] = str(e)
            err = f"Failed to send to {recipient}: {e}"
            print(":(", err)
            logging.error(err)

        # batch pause
        if batch >= batch_size and sent < total_limit:
            pause_msg = f"Batch of {batch_size} done — sleeping {pause_interval}s…"
            print("⏸", pause_msg)
            logging.info(pause_msg)
            time.sleep(pause_interval)
            batch = 0

    save_contacts(contacts_path, contacts, fieldnames)
    logging.info("Contacts CSV updated with send status and errors.")
    logging.info("=== Send run complete ===")

if __name__ == "__main__":
    main()
