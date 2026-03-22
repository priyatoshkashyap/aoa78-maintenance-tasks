"""
Payment synchronization module.
Syncs Excel financial data with Firestore and maintains JSON cache.
"""

import os
import json
import pandas as pd
from datetime import datetime
import pytz
import firebase_admin
from firebase_admin import credentials, firestore


def load_payment_cache(filepath: str) -> dict:
    """Load existing payment cache from JSON file. Returns empty dict if file doesn't exist."""
    if not os.path.exists(filepath):
        print(f"Info: Payment cache file '{filepath}' not found. Starting with empty cache.")
        return {}
    with open(filepath) as f:
        return json.load(f)


def save_payment_cache(filepath: str, data: dict) -> None:
    """Save payment cache to JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4, default=str)


def sync_payments_from_excel(db, excel_path: str, sheet_name: str, cache_file: str) -> None:
    """
    Sync payment balances from Excel file to Firestore and update cache.

    Args:
        db: Firestore client
        excel_path: Path to the Excel file
        sheet_name: Sheet name containing flat details
        cache_file: Path to payment cache JSON file
    """
    df = pd.read_excel(excel_path, sheet_name=sheet_name)

    # Get modification time
    modification_timestamp = excel_path.stat().st_mtime
    modification_time = datetime.fromtimestamp(modification_timestamp)
    timezone_default = os.getenv("TIMEZONE_DEFAULT", "UTC")
    report_timezone = pytz.timezone(os.getenv("REPORT_TIMEZONE", "Asia/Kolkata"))
    modification_time = modification_time.replace(tzinfo=pytz.timezone(timezone_default))
    modification_time = modification_time.astimezone(report_timezone)

    address_payment = {}
    existing_cache = load_payment_cache(cache_file)

    for x in range(1, 332):
        address = df.loc[x]["Unnamed: 3"]
        balance = df.loc[x]["Unnamed: 23"]
        old_balance = existing_cache.get(address, {}).get("balance")

        if old_balance != balance:
            print(f"New balance found for {address} - Old: {old_balance}, New: {balance}")

            address_payment_dtl = {
                'address': address,
                'balance': balance,
                'updated_ts': modification_time
            }
            address_payment[address] = address_payment_dtl
            db.document(f'payments/{address}').set(document_data=address_payment_dtl)
        else:
            address_payment[address] = existing_cache[address]

    save_payment_cache(cache_file, address_payment)


def initialize_firebase(credentials_path: str) -> firestore.client:
    """
    Initialize Firebase Admin SDK.

    Args:
        credentials_path: Path to Firebase service account JSON

    Returns:
        Firestore client instance
    """
    cred = credentials.Certificate(credentials_path)
    firebase_admin.initialize_app(cred)
    return firestore.client()
