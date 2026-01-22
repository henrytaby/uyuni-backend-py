# ruff: noqa: E501
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time

import httpx
from sqlmodel import Session, create_engine, select

from app.auth.utils import get_password_hash
from app.core.config import settings
from app.models.audit import AuditLog
from app.models.user import User

# Database setup for reading logs
engine = create_engine(settings.DATABASE_URL)

BASE_URL = "http://127.0.0.1:8000"

def seed_superuser():
    print("--- 0. Checking/Seeding Superuser ---")
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == "superuser")).first()
        if not user:
            print("Creating superuser...")
            user = User(
                username="superuser",
                email="superuser@example.com",
                password_hash=get_password_hash("password"),
                is_superuser=True,
                is_active=True,
            )
            session.add(user)
            session.commit()
            print("Superuser created.")
        else:
            print("Superuser already exists.")

def run_demo():
    seed_superuser()
    print("--- 1. Authenticating as Superuser ---")
    # Login
    login_data = {"username": "superuser", "password": "password"} # Assuming default superuser
    try:
        response = httpx.post(f"{BASE_URL}/api/auth/token", data=login_data)
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            # Try generic admin if superuser fails, or maybe we need to create one?
            # But tests use superuser/password, so it should exist if seeded.
            return

        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Login successful!\n")

        print("--- 2. Creating a Task (Triggers ACCESS + CREATE Audit) ---")
        task_data = {
            "title": "Audit Demo Task",
            "description": "This task was created to test the audit system.",
            "status": "pending",
            "is_active": True
        }
        res_create = httpx.post(f"{BASE_URL}/api/tasks/", json=task_data, headers=headers)
        if res_create.status_code != 201:
            print(f"Create Task failed: {res_create.text}")
            return

        task_id = res_create.json()["id"]
        print(f"Task created with ID: {task_id}\n")

        print("--- 3. Updating the Task (Triggers ACCESS + UPDATE Audit) ---")
        update_data = {
            "title": "Audit Demo Task (Updated)",
            "status": "in_progress"
        }
        res_update = httpx.patch(f"{BASE_URL}/api/tasks/{task_id}", json=update_data, headers=headers)
        if res_update.status_code != 201: # Check router status code
             print(f"Update Task failed: {res_update.text}")
        else:
             print("Task updated successfully.\n")

        # Wait a moment for async things or db flush if needed (though it's sync)
        time.sleep(1)

        print("--- 4. Verifying Audit Logs in Database ---")
        with Session(engine) as session:
            # Fetch recent logs (last 5)
            logs = session.exec(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(5)).all()

            print(f"{'ID':<5} | {'Action':<10} | {'Entity':<10} | {'User':<10} | {'Changes (Preview)'}")
            print("-" * 80)
            for log in logs:
                changes_str = json.dumps(log.changes) if log.changes else ""
                changes_preview = (changes_str[:40] + '..') if len(changes_str) > 40 else changes_str
                print(f"{log.id:<5} | {log.action:<10} | {log.entity_type:<10} | {log.username or 'N/A':<10} | {changes_preview}")

                if log.action == "UPDATE" and log.entity_type == "Task":
                    print(f"   >>> Full Changes for Task Update: {json.dumps(log.changes, indent=2)}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_demo()
