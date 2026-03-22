"""
Request cleanup module.
Removes old service request records from Firestore based on lastUpdatedAt timestamp.
"""

import pytz
from datetime import datetime, timedelta
from firebase_admin import firestore


def cleanup_old_requests(db, months_threshold: int = 12) -> int:
    """
    Remove requests older than the specified threshold from lastUpdatedAt.

    Args:
        db: Firestore client
        months_threshold: Age threshold in months (default: 12 months = 1 year)

    Returns:
        Number of documents deleted
    """
    # Calculate cutoff date using 365 days per year for accuracy
    days_threshold = months_threshold * 365 // 12
    cutoff_date = datetime.now(pytz.UTC) - timedelta(days=days_threshold)

    # Query old requests
    old_requests_query = db.collection('requests').where('lastUpdatedAt', '<', cutoff_date).stream()

    deleted_count = 0
    batch_size = 500  # Firestore batch limit is 500

    # Collect documents to delete
    docs_to_delete = list(old_requests_query)

    if not docs_to_delete:
        print(f"No requests found older than {months_threshold} months.")
        return 0

    print(f"Found {len(docs_to_delete)} requests older than {months_threshold} months. Deleting...")

    # Delete in batches
    for i in range(0, len(docs_to_delete), batch_size):
        batch = db.batch()
        batch_docs = docs_to_delete[i:i + batch_size]

        for doc in batch_docs:
            batch.delete(doc.reference)

        batch.commit()
        deleted_count += len(batch_docs)
        print(f"Deleted {deleted_count} requests so far...")

    print(f"Cleanup complete. Total {deleted_count} old requests removed.")
    return deleted_count
