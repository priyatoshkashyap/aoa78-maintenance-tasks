# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AOA78 (Area Owners Association - 78) service requests and payments management system. Python scripts that sync Excel financial data with Firebase Firestore and generate HTML reports for service requests.

## Commands

**Run the main script:**
```bash
python main.py [options]
```

**Install dependencies:**
```bash
pip install -r requirements.txt
or py -m pip install -r requirements.txt
```

## Command-Line Options

Feature flags (all optional, defaults to False):
- `--sync-payments` - Sync Excel data to Firestore
- `--cleanup-old-requests` - Remove requests older than threshold
- `--cleanup-months N` - Age threshold in months for cleanup (default: 12)
- `--generate-pending-approval` - Generate and email pending approval requests
- `--generate-in-progress` - Generate and email in-progress requests
- `--generate-monthly-stats` - Generate and email monthly aggregated stats
- `--generate-quarterly-stats` - Generate and email quarterly aggregated stats

**Examples:**
```bash
# Sync payments only
python main.py --sync-payments

# Cleanup old requests older than 12 months
python main.py --cleanup-old-requests

# Cleanup with custom threshold (6 months)
python main.py --cleanup-old-requests --cleanup-months 6

# Generate all reports
python main.py --generate-pending-approval --generate-in-progress --generate-monthly-stats --generate-quarterly-stats
or py main.py --generate-pending-approval --generate-in-progress --generate-monthly-stats --generate-quarterly-stats

# Combine sync, cleanup, and reports
python main.py --sync-payments --cleanup-old-requests --generate-pending-approval
```

## Architecture

### Module Structure
- `main.py` - Main entry point, orchestrates payment sync, cleanup, and report generation
- `payment_sync.py` - Syncs Excel payment data to Firestore, maintains JSON cache
- `report_generator.py` - Generates HTML reports (current requests, aggregated stats, SLA analysis)
- `email_client.py` - Pluggable email client interface (SendGrid, Mailjet, Gmail SMTP)
- `request_cleanup.py` - Removes old service request records from Firestore based on age

### Data Flow
1. **Excel → Firestore**: `payment_sync.py` reads Excel (`FlatDetails` sheet) and syncs balances to Firestore `payments/` collection
2. **Firestore → HTML Reports**: `report_generator.py` queries `requests/` collection, generates HTML reports
3. **JSON Cache**: `address_payment_details.json` caches payment balances per flat address

### Firestore Collections
- `requests` - Service requests: `address`, `name`, `mobile`, `serviceType`, `status`, `createdAt`, `lastUpdatedAt`
- `payments` - Payment records keyed by address: `balance`, `updated_ts`

### Configuration

**Environment variables** (via `.env` file):
- `FIREBASE_CREDENTIALS_PATH` - Service account JSON path (required)
- `EXCEL_FILE_PATH` - Finance data source path (required for sync)
- `EMAIL_PROVIDER` - Email provider to use: `sendgrid`, `mailjet`, or `gmail` (default: `mailjet`)
- `SENDGRID_API_KEY` - SendGrid API key (required for SendGrid emails)
- `MAILJET_API_KEY` / `MAILJET_SECRET_KEY` - Mailjet credentials (required for Mailjet emails)
- `GMAIL_APP_PASSWORD` - Gmail app password (required for Gmail SMTP emails)
- `EMAIL_FROM` / `EMAIL_FROM_NAME` - Sender email and name
- `EMAIL_TO` - Recipient email address
- `TIMEZONE_DEFAULT` / `REPORT_TIMEZONE` - Timezone settings

**Feature control** - Use command-line arguments (see Commands section). Environment variable flags (`SYNC_PAYMENTS`, `GENERATE_*`, `CLEANUP_OLD_REQUESTS`) are no longer used.

### Adding New Email Providers
Implement the `EmailClient` interface in `email_client.py`:
```python
class MySMTPClient(EmailClient):
    def send_email(self, to_email: str, subject: str, html_content: str) -> None:
        # implementation
```
Register in `get_email_client()` factory function.

## Notes
- Report generation controlled by env flags (disabled by default)
- Timezone: UTC → Asia/Kolkata conversion
