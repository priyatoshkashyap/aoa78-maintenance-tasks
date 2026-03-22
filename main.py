"""
Main script for AOA78 service requests and payments management.
Syncs Excel financial data with Firestore and generates HTML reports.
"""

import os
import argparse
import pathlib
import pytz
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

from payment_sync import sync_payments_from_excel, initialize_firebase
from report_generator import generate_current_requests_report, generate_aggregated_stats
from email_client import get_email_client, EmailClient
from request_cleanup import cleanup_old_requests

# Load environment variables from .env file
load_dotenv()

# Configuration from environment (can't be CLI arguments due to sensitivity or variability)
EXCEL_FILE_PATH = os.getenv("EXCEL_FILE_PATH", r"C:/Users/P2/Desktop/RWA78_OS_25_26.xlsx")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "./aoa78-service-requests-firebase-adminsdk-9of97-708fbd4bc6.json")
PAYMENT_DETAILS_JSON = os.getenv("PAYMENT_DETAILS_JSON", "address_payment_details.json")
EMAIL_TO = os.getenv("EMAIL_TO", "priyatosh.kashyap@gmail.com")
TIMEZONE_DEFAULT = os.getenv("TIMEZONE_DEFAULT", "UTC")
REPORT_TIMEZONE = os.getenv("REPORT_TIMEZONE", "Asia/Kolkata")

# Email provider constant - change this to use a different provider for all emails
EMAIL_PROVIDER = "mailjet"


def parse_arguments():
    """Parse command-line arguments for feature flags."""
    parser = argparse.ArgumentParser(
        description="AOA78 Service Requests and Payments Management System"
    )
    parser.add_argument(
        "--sync-payments",
        action="store_true",
        help="Sync Excel payment data to Firestore"
    )
    parser.add_argument(
        "--cleanup-old-requests",
        action="store_true",
        help="Remove requests older than threshold from lastUpdatedAt"
    )
    parser.add_argument(
        "--cleanup-months",
        type=int,
        default=12,
        help="Age threshold in months for cleanup (default: 12)"
    )
    parser.add_argument(
        "--generate-pending-approval",
        action="store_true",
        help="Generate and email pending approval requests report"
    )
    parser.add_argument(
        "--generate-in-progress",
        action="store_true",
        help="Generate and email in-progress requests report"
    )
    parser.add_argument(
        "--generate-monthly-stats",
        action="store_true",
        help="Generate and email monthly aggregated stats report"
    )
    parser.add_argument(
        "--generate-quarterly-stats",
        action="store_true",
        help="Generate and email quarterly aggregated stats report"
    )
    return parser.parse_args()


# Get today's date formatted
today = datetime.now().replace(tzinfo=pytz.timezone(TIMEZONE_DEFAULT)).astimezone(pytz.timezone(REPORT_TIMEZONE)).strftime("%Y-%m-%d")


def main():
    """Main entry point."""
    # Parse command-line arguments
    args = parse_arguments()

    # Initialize Firebase
    db = initialize_firebase(FIREBASE_CREDENTIALS_PATH)

    # Sync payments from Excel (controlled by --sync-payments flag)
    if args.sync_payments:
        file_path = pathlib.Path(EXCEL_FILE_PATH)
        modification_timestamp = file_path.stat().st_mtime
        modification_time = datetime.fromtimestamp(modification_timestamp)
        modification_time = modification_time.replace(tzinfo=pytz.timezone(TIMEZONE_DEFAULT))
        modification_time = modification_time.astimezone(pytz.timezone(REPORT_TIMEZONE)).strftime("%Y-%m-%d")

        sync_payments_from_excel(
            db=db,
            excel_path=file_path,
            sheet_name='FlatDetails',
            cache_file=PAYMENT_DETAILS_JSON
        )
    else:
        modification_time = datetime.now().strftime("%Y-%m-%d")

    # Cleanup old requests (controlled by --cleanup-old-requests flag)
    if args.cleanup_old_requests:
        cleanup_old_requests(db, args.cleanup_months)

    # Generate Open Requests (Pending + In Progress) - combined into one email
    if args.generate_pending_approval or args.generate_in_progress:
        # Start fresh with open_requests.html
        with open("open_requests.html", 'w') as f:
            f.write(f"Open Requests Report for - <b>{today}</b><br/><br/>\n")

        # Generate Pending Approval if requested
        if args.generate_pending_approval:
            generate_current_requests_report(db, 'Pending Approval', modification_time, "open_requests.html")

        # Add separator and generate In Progress if requested
        if args.generate_in_progress:
            with open("open_requests.html", 'a') as f:
                f.write(f"<br/><br/>In Progress Requests Report for - <b>{today}</b><br/><br/>\n")
            generate_current_requests_report(db, 'In Progress', modification_time, "open_requests.html")

        # Send single consolidated email
        email_client = get_email_client(EMAIL_PROVIDER)
        email_client.send_email(
            to_email=EMAIL_TO,
            subject=f'"AOA78 - Open Requests Report - {today}"',
            html_content=open("open_requests.html").read()
        )

    # Generate Monthly Stats report
    if args.generate_monthly_stats:
        first_day_of_month = date.today().replace(day=1)

        with open("request_stats.html", 'w') as f:
            f.write(f"<b>Monthly</b> Status Report for Requests from - <b>{first_day_of_month.strftime('%Y-%m-%d')}</b><br/><br/>\n")

        dt = datetime.combine(first_day_of_month, datetime.min.time())
        generate_aggregated_stats(db, dt, modification_time, "request_stats.html")

        email_client = get_email_client(EMAIL_PROVIDER)
        email_client.send_email(
            to_email=EMAIL_TO,
            subject=f'"AOA78 - Monthly Stats Report - {first_day_of_month.strftime("%Y-%m-%d")}"',
            html_content=open("request_stats.html").read()
        )

    # Generate Quarterly Stats report
    if args.generate_quarterly_stats:
        few_days_back = date.today() - timedelta(days=15)
        first_day_of_month = few_days_back.replace(day=1)

        with open("request_stats.html", 'w') as f:
            f.write(f"<b>Monthly</b> Status Report for Requests from - <b>{first_day_of_month.strftime('%Y-%m-%d')}</b><br/><br/>\n")

        dt = datetime.combine(first_day_of_month, datetime.min.time())
        generate_aggregated_stats(db, dt, modification_time, "request_stats.html")

        two_months_back = date.today() - timedelta(days=75)
        first_day_of_quarter = two_months_back.replace(day=1)

        with open("request_stats.html", 'a') as f:
            f.write(f"<br/><br/><b>Quarterly</b> Status Report for Requests from - <b>{first_day_of_quarter.strftime('%Y-%m-%d')}</b><br/><br/>\n")

        dt = datetime.combine(first_day_of_quarter, datetime.min.time())
        generate_aggregated_stats(db, dt, modification_time, "request_stats.html")

        email_client = get_email_client(EMAIL_PROVIDER)
        email_client.send_email(
            to_email=EMAIL_TO,
            subject=f'"AOA78 - Quarterly Stats Report - {first_day_of_month.strftime("%Y-%m-%d")}"',
            html_content=open("request_stats.html").read()
        )


if __name__ == "__main__":
    main()
