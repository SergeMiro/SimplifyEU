"""
SQLAlchemy engine + session management for plain PostgreSQL.

This is the reusable connectivity layer for the Python services:
  * a single Engine built from DATABASE_URL,
  * a SessionLocal factory,
  * a `get_db` FastAPI dependency that yields a Session and always closes it.

DATABASE_URL is a standard libpq URL, e.g.
  postgresql://user:pass@host:5432/simplifyeu_db
The `+psycopg` driver suffix is added automatically when missing so we use
psycopg 3 (psycopg[binary]) regardless of how the URL is written in the env.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings


def _normalize_db_url(url: str) -> str:
    """Force the psycopg (v3) driver so SQLAlchemy doesn't reach for psycopg2."""
    if url.startswith("postgresql+"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    return url


engine = create_engine(
    _normalize_db_url(settings.DATABASE_URL),
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a DB session and guarantee it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
