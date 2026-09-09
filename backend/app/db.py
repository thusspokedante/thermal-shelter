"""SQLAlchemy engine/session setup for the SQLite material database."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./materials.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite + FastAPI
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def init_db():
    """Create tables if they don't exist yet."""
    from app.models.materials import Material  # noqa: F401 (register model)
    Base.metadata.create_all(bind=engine)
