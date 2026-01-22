import argparse
import gzip
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

# Ensure we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.audit import AuditLog
from app.util.datetime import get_current_time


def archive_audit_logs(
    days_retention: int = 90, archive_dir: str = "archive", engine=None
):
    """
    Moves old audit logs to a compressed JSON file and deletes them from DB.
    """
    if engine is None:
        # Lazy load imports to avoid circular deps if imported at top
        from app.core import db

        engine = db.engine

    # Ensure archive directory exists
    os.makedirs(archive_dir, exist_ok=True)

    cutoff_date = get_current_time() - timedelta(days=days_retention)
    print(f"Archiving logs older than {cutoff_date}...")

    with Session(engine) as session:
        # 1. Select old logs
        # Note: In production with millions of rows, use pagination or LIMIT
        statement = select(AuditLog).where(AuditLog.timestamp < cutoff_date)
        logs_to_archive = session.exec(statement).all()

        if not logs_to_archive:
            print("No logs to archive.")
            return

        print(f"Found {len(logs_to_archive)} logs to archive.")

        # 2. Serialize to JSON
        # We convert to dict, handling datetime serialization
        data = [log.model_dump(mode="json") for log in logs_to_archive]

        # 3. Save to file (Compressed)
        ts = int(datetime.now(timezone.utc).timestamp())
        filename = f"audit_archive_{cutoff_date.strftime('%Y%m%d')}_{ts}.json.gz"
        filepath = os.path.join(archive_dir, filename)

        with gzip.open(filepath, "wt", encoding="UTF-8") as f:
            json.dump(data, f)

        print(f"Saved archive to {filepath}")

        # 4. Delete from DB
        # SQLModel doesn't support bulk delete directly easily without engine.execute
        # We'll stick to simple delete for now or session.delete

        for log in logs_to_archive:
            session.delete(log)

        session.commit()
        print("Deleted archived logs from database.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Archive old audit logs")
    parser.add_argument("--days", type=int, default=90, help="Days of retention")
    parser.add_argument(
        "--dir", type=str, default="/opt/uab/archive", help="Archive directory"
    )

    args = parser.parse_args()
    archive_audit_logs(args.days, args.dir)
