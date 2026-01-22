from sqlmodel import create_engine, text

from app.core.config import settings

engine = create_engine(str(settings.DATABASE_URL))


def reset_schema():
    print("Dropping schema public...")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.commit()
    print("Schema reset successfully.")


if __name__ == "__main__":
    reset_schema()
