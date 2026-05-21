import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import Boolean, Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_db_path() -> Path:
    raw_path = os.getenv("WHITELIST_DB_PATH", "data/whitelist.db").strip()
    db_path = Path(raw_path)
    if not db_path.is_absolute():
        base_dir = Path(__file__).resolve().parents[1]
        db_path = base_dir / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


DB_PATH = _resolve_db_path()
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class AllowedUser(Base):
    __tablename__ = "allowed_users"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(64), unique=True, index=True, nullable=True)
    user_name = Column(String(64), index=True, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=_utc_now)
    updated_at = Column(DateTime, nullable=False, default=_utc_now, onupdate=_utc_now)


class AdminContact(Base):
    __tablename__ = "admin_contacts"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=True)
    phone = Column(String(32), nullable=True)
    email = Column(String(128), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=_utc_now, onupdate=_utc_now)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session() -> Generator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
