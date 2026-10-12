import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

# CHANGE: Force Vercel to prioritize its own environment variables, falling back to local settings
database_url = os.getenv("DATABASE_URL") or settings.DATABASE_URL

# PostgreSQL URL compatibility (if postgres:// is provided instead of postgresql://)
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

is_sqlite = database_url.startswith("sqlite")

if is_sqlite:
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False}
    )

    # Enable foreign key support for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    # Production PostgreSQL / MySQL connection pool configuration
    engine = create_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def run_auto_migrations():
    """
    Safely adds newly defined columns to existing database tables if they do not exist yet.
    """
    try:
        with engine.begin() as conn:
            if is_sqlite:
                # Check users table
                try:
                    result = conn.exec_driver_sql("PRAGMA table_info(users);").fetchall()
                    cols = [row[1] for row in result]
                    if cols and "is_email_verified" not in cols:
                        conn.exec_driver_sql("ALTER TABLE users ADD COLUMN is_email_verified BOOLEAN DEFAULT 1;")
                except Exception:
                    pass
    except Exception as e:
        print(f"Auto-migration note: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()