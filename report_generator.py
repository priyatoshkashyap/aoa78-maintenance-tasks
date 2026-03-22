"""
Report generation module for Firestore service requests.
Generates HTML reports for pending approvals, in-progress requests, and aggregated statistics.
"""

import json
import os
import pytz
from datetime import datetime, date
from firebase_admin import firestore


def load_payment_details(filepath: str) -> dict:
    """Load payment details from JSON file."""
    with open(filepath) as f:
        return json.load(f)


def generate_current_requests_report(db, status: str, file_mod_time: str, output_file: str) -> None:
    """
    Generate HTML report for current requests (Pending Approval or In Progress).

    Args:
        db: Firestore client
        status: Request status filter ("Pending Approval" or "In Progress")
        file_mod_time: File modification time to display
        output_file: Output HTML file path
    """
    link = "https://aoa78-dashboard.web.app/pending-approval"
    if status == "In Progress":
        link = "https://aoa78-dashboard.web.app/in-progress"

    address_payment = load_payment_details("address_payment_details.json")
    timezone_default = os.getenv("TIMEZONE_DEFAULT", "UTC")
    report_timezone = pytz.timezone(os.getenv("REPORT_TIMEZONE", "Asia/Kolkata"))

    with open(output_file, 'a') as f:
        f.write(f" ---------------------------------------- <a href='{link}'>{status:<10} Requests</a> ----------------------------------------\n")
        f.write("<table style='border-spacing: 30px 0px'>"
                "<tr><th>Address</th><th>Name</th><th>Mobile No.</th><th>Service</th>"
                "<th>Raised On</th><th>Last Updated</th>"
                f"<th>Balance Due (as at - {file_mod_time})</th></tr>\n")

        docs = (db.collection('requests')
                .where('status', '==', status)
                .order_by('createdAt', direction=firestore.Query.ASCENDING)
                .stream())

        for doc in docs:
            created_at = doc.get("createdAt").astimezone(report_timezone)
            last_updated = doc.get("lastUpdatedAt").astimezone(report_timezone)

            address = doc.get("address").replace("-", "")
            total_balance = address_payment.get(address, {}).get("balance", 0)

            f.write(f"<tr>"
                    f"<td>{doc.get('address')}</td>"
                    f"<td>{doc.get('name')}</td>"
                    f"<td><a href='tel:{doc.get('mobile')}'>{doc.get('mobile')}</a></td>"
                    f"<td>{doc.get('serviceType')}</td>"
                    f"<td>{created_at.year}-{created_at.month:02d}-{created_at.day:02d} "
                    f"{created_at.hour:02d}:{created_at.minute:02d}</td>"
                    f"<td>{last_updated.year}-{last_updated.month:02d}-{last_updated.day:02d} "
                    f"{last_updated.hour:02d}:{last_updated.minute:02d}</td>"
                    f"<td>{total_balance}</td>"
                    f"</tr>\n")

        f.write("</table><br/>\n")


def generate_aggregated_stats(db, start_date: date, file_mod_time: str, output_file: str) -> None:
    """
    Generate aggregated statistics report for requests from a given date.

    Args:
        db: Firestore client
        start_date: Start date for filtering requests
        file_mod_time: File modification time to display
        output_file: Output HTML file path
    """
    timezone_default = os.getenv("TIMEZONE_DEFAULT", "UTC")
    report_timezone = pytz.timezone(os.getenv("REPORT_TIMEZONE", "Asia/Kolkata"))

    # Convert date to datetime for Firestore query
    dt = datetime.combine(start_date, datetime.min.time())

    address_payment = load_payment_details("address_payment_details.json")

    # Aggregation containers
    requests_per_address_service = {}
    service_counts = {}
    service_completed_sla = {}

    docs = (db.collection('requests')
            .where('createdAt', '>=', dt)
            .order_by('createdAt', direction=firestore.Query.ASCENDING)
            .stream())

    for doc in docs:
        if doc.get("status") == 'Rejected':
            continue

        address = doc.get("address")
        service_type = doc.get("serviceType")
        status = doc.get("status")

        # Count per address + service
        if address not in requests_per_address_service:
            requests_per_address_service[address] = {}
        if service_type in requests_per_address_service[address]:
            requests_per_address_service[address][service_type] += 1
        else:
            requests_per_address_service[address][service_type] = 1

        # Count per service
        service_counts[service_type] = service_counts.get(service_type, 0) + 1

        # SLA tracking for completed requests
        if status == 'Completed':
            completion_sla_days = (doc.get("lastUpdatedAt") - doc.get("createdAt")).days
            if service_type not in service_completed_sla:
                service_completed_sla[service_type] = {}
            service_completed_sla[service_type][completion_sla_days] = \
                service_completed_sla[service_type].get(completion_sla_days, 0) + 1

    # Prepare data for rendering
    address_stats_list = []
    for addr, services in requests_per_address_service.items():
        service_str = ', '.join(f"{count} - {svc}" for svc, count in services.items())
        total_count = sum(services.values())
        address_stats_list.append({
            "ADDRESS": addr,
            "SERVICE": service_str,
            "COUNT": total_count
        })
    address_stats_list.sort(key=lambda x: x["COUNT"] * -1)

    service_stats_list = [{"SERVICE": svc, "COUNT": cnt} for svc, cnt in service_counts.items()]
    service_stats_list.sort(key=lambda x: x["COUNT"] * -1)

    completed_stats_list = []
    for svc, sla_data in service_completed_sla.items():
        total = sum(sla_data.values())
        sla_str = '<br/>'.join(
            f"{(cnt / total) * 100:05.2f}% - SLA {sla_days} days"
            for sla_days, cnt in sla_data.items()
        )
        completed_stats_list.append({
            "SERVICE": svc,
            "SLA": sla_str,
            "COUNT": total
        })
    completed_stats_list.sort(key=lambda x: x["COUNT"] * -1)

    with open(output_file, 'a') as f:
        # Requests per Service Types
        f.write("---------------------------------------- Requests per Service Types ----------------------------------------\n")
        f.write("<table style='border-spacing: 30px 0px'><tr>")
        for item in service_stats_list:
            f.write(f"<th>{item['SERVICE']}</th>")
        f.write("</tr><tr>")
        for item in service_stats_list:
            f.write(f"<th>{item['COUNT']}</th>")
        f.write("</tr></table><br/>\n")

        # Closed requests SLA
        f.write("---------------------------------------- Closed requests SLA per Service Types ----------------------------------------\n")
        f.write("<table style='border-spacing: 30px 0px'><tr>")
        for item in completed_stats_list:
            f.write(f"<th>{item['SERVICE']}</th>")
        f.write("</tr><tr>")
        for item in completed_stats_list:
            f.write(f"<th>{item['COUNT']}</th>")
        f.write("</tr><tr>")
        for item in completed_stats_list:
            f.write(f"<td>{item['SLA']}</td>")
        f.write("</tr></table><br/>\n")

        # Requests per Flat
        f.write("---------------------------------- Requests per Flat, service type wise ------------------------------------\n")
        f.write(f"<table style='border-spacing: 30px 0px'>"
                f"<tr><th>Address</th><th>Service Types</th><th>Total</th>"
                f"<th>Balance Due (as at - {file_mod_time})</th></tr>\n")
        for item in address_stats_list:
            address_key = item["ADDRESS"].replace("-", "")
            balance = address_payment.get(address_key, {}).get("balance", 0)
            f.write(f"<tr><td>{item['ADDRESS']}</td><td>{item['SERVICE']}</td>"
                    f"<td>{item['COUNT']}</td><td>{balance}</td></tr>\n")
        f.write("</table><br/>\n")
