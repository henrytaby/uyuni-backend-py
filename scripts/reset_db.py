from sqlalchemy import text

from app.core.db import engine


def reset_db():
    print("Resetting database...")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.commit()
    print("Database reset complete.")


if __name__ == "__main__":
    reset_db()
