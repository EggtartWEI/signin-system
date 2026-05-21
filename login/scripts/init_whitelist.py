import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from services.whitelist_service import (  # noqa: E402
    get_admin_contact,
    set_admin_contact,
    upsert_allowed_user,
    ensure_db_ready,
)

load_dotenv()


def _get_env_list(name: str) -> list[str]:
    value = os.getenv(name, "")
    if not value.strip():
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    ensure_db_ready()

    default_names = _get_env_list("WHITELIST_DEFAULT_NAMES") or ["李茗", "韦学远"]
    default_ids = _get_env_list("WHITELIST_DEFAULT_IDS")

    for user_id in default_ids:
        upsert_allowed_user(user_id=user_id, user_name=None, enabled=True)
        print(f"已添加白名单用户ID: {user_id}")

    for name in default_names:
        upsert_allowed_user(user_id=None, user_name=name, enabled=True)
        print(f"已添加白名单用户姓名: {name}")

    contact = get_admin_contact()
    if not contact.get("name") and not contact.get("phone") and not contact.get("email"):
        name = os.getenv("ADMIN_CONTACT_NAME")
        phone = os.getenv("ADMIN_CONTACT_PHONE")
        email = os.getenv("ADMIN_CONTACT_EMAIL")
        if name or phone or email:
            set_admin_contact(name=name, phone=phone, email=email)
            print("已写入管理员联系方式")
        else:
            print("管理员联系方式未配置")


if __name__ == "__main__":
    main()
