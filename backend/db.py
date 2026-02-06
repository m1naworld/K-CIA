"""Database engine and session dependency."""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://kcia:kcia_local_pw@localhost:5432/kcia",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    """FastAPI dependency that yields a DB session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
