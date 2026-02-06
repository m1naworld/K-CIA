"""Database engine and session utilities for ETL."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from etl.config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_engine():
    return engine


def execute_sql(sql: str, params: dict | None = None):
    """Execute raw SQL and return result proxy."""
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        conn.commit()
        return result
