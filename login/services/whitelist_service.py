import os
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from sqlalchemy import or_

from models.user_whitelist import (
    AdminContact,
    AllowedUser,
    SessionLocal,
    init_db,
)

load_dotenv()

_db_ready = False


def _get_env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def ensure_db_ready() -> None:
    global _db_ready
    if _db_ready:
        return
    init_db()
    _db_ready = True


def is_whitelist_enabled() -> bool:
    return _get_env_bool("WHITELIST_ENABLED", False)


def is_user_allowed(user_id: Optional[str], user_name: Optional[str]) -> Tuple[bool, Optional[str]]:
    ensure_db_ready()
    user_id = user_id.strip() if user_id else None
    user_name = user_name.strip() if user_name else None

    session = SessionLocal()
    try:
        query = session.query(AllowedUser).filter(AllowedUser.enabled.is_(True))
        if user_id and user_name:
            record = query.filter(
                or_(AllowedUser.user_id == user_id, AllowedUser.user_name == user_name)
            ).first()
            if record:
                match = "user_id" if record.user_id == user_id else "user_name"
                return True, match
            return False, None
        if user_id:
            record = query.filter(AllowedUser.user_id == user_id).first()
            return bool(record), "user_id" if record else None
        if user_name:
            record = query.filter(AllowedUser.user_name == user_name).first()
            return bool(record), "user_name" if record else None
        return False, None
    finally:
        session.close()


def list_allowed_users(limit: int = 200) -> List[Dict[str, Optional[str]]]:
    ensure_db_ready()
    session = SessionLocal()
    try:
        rows = (
            session.query(AllowedUser)
            .order_by(AllowedUser.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "user_id": row.user_id,
                "user_name": row.user_name,
                "enabled": row.enabled,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def upsert_allowed_user(
    user_id: Optional[str],
    user_name: Optional[str],
    enabled: bool = True,
) -> AllowedUser:
    ensure_db_ready()
    user_id = user_id.strip() if user_id else None
    user_name = user_name.strip() if user_name else None
    if not user_id and not user_name:
        raise ValueError("user_id 或 user_name 至少提供一个")

    session = SessionLocal()
    try:
        record = None
        if user_id:
            record = session.query(AllowedUser).filter(AllowedUser.user_id == user_id).first()
        if not record and user_name:
            record = session.query(AllowedUser).filter(AllowedUser.user_name == user_name).first()

        if record:
            record.user_id = user_id or record.user_id
            record.user_name = user_name or record.user_name
            record.enabled = enabled
        else:
            record = AllowedUser(
                user_id=user_id,
                user_name=user_name,
                enabled=enabled,
            )
            session.add(record)

        session.commit()
        session.refresh(record)
        return record
    finally:
        session.close()


def remove_allowed_user(user_id: Optional[str], user_name: Optional[str]) -> bool:
    ensure_db_ready()
    user_id = user_id.strip() if user_id else None
    user_name = user_name.strip() if user_name else None
    if not user_id and not user_name:
        return False

    session = SessionLocal()
    try:
        query = session.query(AllowedUser)
        if user_id and user_name:
            record = query.filter(
                or_(AllowedUser.user_id == user_id, AllowedUser.user_name == user_name)
            ).first()
        elif user_id:
            record = query.filter(AllowedUser.user_id == user_id).first()
        else:
            record = query.filter(AllowedUser.user_name == user_name).first()

        if not record:
            return False
        session.delete(record)
        session.commit()
        return True
    finally:
        session.close()


def _contact_from_env() -> Dict[str, Optional[str]]:
    return {
        "name": os.getenv("ADMIN_CONTACT_NAME"),
        "phone": os.getenv("ADMIN_CONTACT_PHONE"),
        "email": os.getenv("ADMIN_CONTACT_EMAIL"),
    }


def get_admin_contact() -> Dict[str, Optional[str]]:
    ensure_db_ready()
    session = SessionLocal()
    try:
        record = session.query(AdminContact).order_by(AdminContact.id.desc()).first()
        if record:
            return {
                "name": record.name,
                "phone": record.phone,
                "email": record.email,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            }
    finally:
        session.close()
    return _contact_from_env()


def set_admin_contact(name: Optional[str], phone: Optional[str], email: Optional[str]) -> AdminContact:
    ensure_db_ready()
    session = SessionLocal()
    try:
        record = session.query(AdminContact).order_by(AdminContact.id.desc()).first()
        if record:
            record.name = name
            record.phone = phone
            record.email = email
        else:
            record = AdminContact(name=name, phone=phone, email=email)
            session.add(record)
        session.commit()
        session.refresh(record)
        return record
    finally:
        session.close()
