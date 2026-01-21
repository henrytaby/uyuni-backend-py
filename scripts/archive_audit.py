import gzip
import json
import os
import sys
from datetime import timedelta

from sqlalchemy import delete
from sqlmodel import Session, select, col

# Ensure we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import engine as db_engine
from app.models.audit import AuditLog
from app.util.datetime import get_current_time


def archive_audit_logs(days_retention: int = 90, archive_dir: str = "archive", engine=None):
    """
    Moves old audit logs to a compressed JSON file and deletes them from DB.
    """
    if engine is None:
        engine = db_engine

    print(f"Starting audit archive. Retention: {days_retention} days.")
    
    # 1. Calculate cutoff date
    cutoff_date = get_current_time() - timedelta(days=days_retention)
    
    # 2. Ensure archive directory exists
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)
        
    filename = f"audit_archive_{cutoff_date.strftime('%Y_%m_%d')}.json.gz"
    filepath = os.path.join(archive_dir, filename)
    
    with Session(engine) as session:
        # 3. Fetch old logs
        # We fetch in batches if needed, but for simplicity here we fetch all at once
        # For production with millions of rows, use yield_per or pagination
        query = select(AuditLog).where(col(AuditLog.timestamp) < cutoff_date)
        logs = session.exec(query).all()
        
        if not logs:
            print("No logs found to archive.")
            return

        print(f"Found {len(logs)} logs to archive.")
        
        # 4. Write to JSON GZ
        data = [log.model_dump(mode="json") for log in logs]
        
        with gzip.open(filepath, "wt", encoding="utf-8") as f:
            json.dump(data, f, default=str)
            
        print(f"Archived to {filepath}")
        
        # 5. Delete from DB
        delete_statement = delete(AuditLog).where(col(AuditLog.timestamp) < cutoff_date)
        session.exec(delete_statement) # type: ignore
        session.commit()
        
        print("Deleted archived logs from database.")

if __name__ == "__main__":
    # Simple CLI argument parsing
    import argparse
    parser = argparse.ArgumentParser(description="Archive old audit logs")
    parser.add_argument("--days", type=int, default=90, help="Days of retention")
    parser.add_argument("--dir", type=str, default="/opt/uab/archive", help="Archive directory")
    
    args = parser.parse_args()
    archive_audit_logs(args.days, args.dir)
