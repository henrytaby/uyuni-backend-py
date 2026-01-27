from sqlmodel import Session, select

from app.auth.utils import get_password_hash
from app.core.db import engine
from app.models.user import User
from app.util.datetime import get_current_time


def create_users(session: Session):
    # Create Admin User if doesn't exist
    admin_user = session.exec(select(User).where(User.username == "admin")).first()
    if not admin_user:
        admin_user = User(
            username="admin",
            email="admin@gmail.com",
            first_name="Super",
            last_name="Admin",
            is_verified=True,
            is_active=True,
            is_superuser=True,
            password_hash=get_password_hash("admin123"),
            created_at=get_current_time(),
            updated_at=get_current_time(),
        )
        session.add(admin_user)
        session.commit()
        session.refresh(admin_user)
        print("✅ User 'admin' created (Pass: admin123)")
    else:
        print("ℹ️  User 'admin' already exists")


def run_seeders():
    with Session(engine) as session:
        create_users(session)


if __name__ == "__main__":
    run_seeders()
