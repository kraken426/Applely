# Applely: Cold Emailer & Bounce Handler

A lightweight, Jinja-based cold-email sender with built-in rate-limiting, MX pre-checks, CSV tracking, and a Gmail-API-powered bounce handler.

---

## Features

- **Domain-specific Jinja2 templates** (`templates/*.j2`)  
- **PDF attachments** per domain (`attachments/<domain>_resume.pdf`)  
- **Batch sending** (default: 5 emails) with configurable pause (default: 30 min)  
- **Nightly cap** (`TOTAL_PER_NIGHT`)  
- **DNS MX pre-check** to skip domains with no mail server  
- **CSV tracking**: auto-adds `sent`, `sent_at`, and `error` columns to `contacts.csv`  
- **Bounce handling** via Gmail REST API: marks bounced addresses back to `sent=no`, `error="bounced (Address not found)"`  
- **One-click runner** (`run_all.py`) to send then process bounces  

---

## Project Layout

```
cold_email/
├── .env
├── credentials.json        ← Google OAuth client secrets
├── token.json              ← cached Gmail API token (after first run)
├── requirements.txt
├── run_all.py
├── README.md
│
├── templates/
│   ├── frontend.j2
│   ├── backend.j2
│   ├── devops.j2
│   └── default.j2
│
├── attachments/
│   ├── frontend_resume.pdf
│   ├── backend_resume.pdf
│   ├── devops_resume.pdf
│   └── default_resume.pdf
│
├── contacts/
│   └── contacts.csv        ← first_name,email,company,domain[,sent,sent_at,error]
│
├── logs/
│   └── send.log
│
└── src/
    ├── main.py
    ├── sender.py
    ├── renderer.py
    └── bounce_handler_gmail_api.py
```

---

## Prerequisites

- **Python 3.8+**  
- **Gmail account** with:
  - IMAP enabled (Gmail Settings → Forwarding & POP/IMAP → Enable IMAP)  
  - An **App Password** if 2FA is on (or “Allow less secure apps”)  
- **Google Cloud Project** with Gmail API enabled

---

## Installation

1. **Clone** or **unzip** this repo:  
   ```bash
   git clone <your-repo-url> cold_email
   cd cold_email
   ```
2. *(Optional)* Create & activate a virtual environment:  
   ```bash
   python -m venv venv
   source venv/bin/activate   # macOS/Linux
   venv\Scripts\activate    # Windows
   ```
3. **Install** dependencies:  
   ```bash
   pip install -r requirements.txt
   ```

---

## Configuration

### 1. Create your `.env` file

```ini
# SMTP (main.py)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=you@yourdomain.com
SMTP_PASSWORD=your-app-password

# Paths & rate-limits
CONTACTS_FILE=contacts/contacts.csv
TEMPLATES_DIR=templates
ATTACHMENTS_DIR=attachments
TOTAL_PER_NIGHT=50
BATCH_SIZE=5
PAUSE_INTERVAL=1800

# Gmail API bounce handler
GOOGLE_CREDENTIALS=credentials.json
BOUNCE_LOOKBACK_DAYS=1
```

> **Security**: add `.env`, `credentials.json`, and `token.json` to `.gitignore` and restrict permissions (`chmod 600 .env`).

---

## `credentials.json` — What & How to Get It

Your **OAuth client secret** for the Gmail API. Follow these steps:

1. **Go to Google Cloud Console**  
   https://console.cloud.google.com/

2. **Create or select a project**  
   - Click the project dropdown → **New Project** → name it (e.g. “ColdEmailer”) → **Create**.

3. **Enable the Gmail API**  
   - **APIs & Services → Library** → search “Gmail API” → **Enable**.

4. **Configure OAuth consent screen**  
   - **APIs & Services → OAuth consent screen**  
   - **User Type**: External → **Create**  
   - Fill in **App name**, **User support email**.  
   - Under **Scopes**, leave defaults.  
   - **Test users**: **Add your Gmail address** here and save.  
     > Only addresses listed as Test Users can authorize your unverified app.  

5. **Create OAuth Client ID**  
   - **APIs & Services → Credentials** → **Create Credentials → OAuth client ID**  
   - **Application type**: Desktop  
   - Name it (e.g. “ColdEmailer Desktop”) → **Create**.

6. **Download JSON**  
   - In the Credentials list, find your new client → click **Download** icon → save as `credentials.json` in your project root.

7. **Authorize**  
   - On first run of `bounce_handler_gmail_api.py`, a browser window opens.  
   - Sign in, click **Advanced → Go to ColdEmailer (unsafe) → Allow**.  
   - A `token.json` file will be saved for future runs.

---

## Usage

### 1. Send cold emails

```bash
python src/main.py
```

### 2. Handle bounces via Gmail API

```bash
python src/bounce_handler_gmail_api.py
```

### 3. Combined runner

```bash
python run_all.py
```

---

## Testing

- MX pre-check: use non-existent domain  
- Bounce handler: send to invalid alias, wait, run handler

---

## Security Best Practices

- **Do not** commit `.env`, `credentials.json`, or `token.json`.  
- **Add to `.gitignore`**:  
  ```gitignore
  .env
  credentials.json
  token.json
  ```  
- **Restrict file permissions** (`chmod 600 .env`).  
- **Use** a dedicated App Password or secret store in production.  
- **Rotate** and **audit** credentials regularly.

---

## License

MIT License © 2025 Ayush Srivastav