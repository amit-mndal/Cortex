from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.models import Base

# Local dev: sqlite:///./data/cortex.db (zero setup, but ephemeral on most
# free hosting - resets on every redeploy).
# Production: set DATABASE_URL to a Supabase/Render Postgres connection
# string in your environment - nothing else in this file needs to change.
DATABASE_URL = settings.database_url

# SQLite needs this flag for use across threads (Celery worker + FastAPI);
# Postgres doesn't need or accept it.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
