from sqlalchemy.orm import Session

from app.config import read_default_model_config
from app.models import Admin, SystemSetting
from app.services.security import hash_password


DEFAULT_SETTINGS = {
    "signup_points": "50",
    "generate_cost": "10",
    "modify_cost": "8",
    "mock_mode": "true",
    "chat_api_type": "chat_completions",
    "chat_base_url": "",
    "chat_api_key": "",
    "chat_model_name": "gpt-4o-mini",
    "image_api_type": "images_edits",
    "image_base_url": "",
    "image_api_key": "",
    "image_model_name": "gpt-image-1",
    "image_size_mode": "ratio_standard",
    "image_response_format": "",
    "image_quality": "",
    "image_file_field": "image",
}


def init_defaults(db: Session) -> None:
    model_defaults = read_default_model_config()
    defaults = {**DEFAULT_SETTINGS, **model_defaults}
    defaults["chat_base_url"] = model_defaults.get("model_base_url", "")
    defaults["chat_api_key"] = model_defaults.get("model_api_key", "")
    defaults["image_base_url"] = model_defaults.get("model_base_url", "")
    defaults["image_api_key"] = model_defaults.get("model_api_key", "")
    defaults["image_model_name"] = model_defaults.get("model_name", "gpt-image-1")
    for key, value in defaults.items():
        if db.get(SystemSetting, key) is None:
            db.add(SystemSetting(key=key, value=str(value)))

    admin = db.query(Admin).filter(Admin.username == "admin").first()
    if admin is None:
        db.add(Admin(username="admin", password_hash=hash_password("admin123")))
    db.commit()


def get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.get(SystemSetting, key)
    return setting.value if setting else default


def get_int_setting(db: Session, key: str, default: int) -> int:
    try:
        return int(get_setting(db, key, str(default)))
    except ValueError:
        return default


def set_setting(db: Session, key: str, value: str) -> None:
    setting = db.get(SystemSetting, key)
    if setting is None:
        db.add(SystemSetting(key=key, value=value))
    else:
        setting.value = value


def all_settings(db: Session) -> dict:
    settings = {row.key: row.value for row in db.query(SystemSetting).all()}
    model_defaults = read_default_model_config()
    defaults = {**DEFAULT_SETTINGS, **model_defaults}
    defaults["chat_base_url"] = model_defaults.get("model_base_url", "")
    defaults["chat_api_key"] = model_defaults.get("model_api_key", "")
    defaults["image_base_url"] = model_defaults.get("model_base_url", "")
    defaults["image_api_key"] = model_defaults.get("model_api_key", "")
    defaults["image_model_name"] = model_defaults.get("model_name", "gpt-image-1")
    for key, value in defaults.items():
        settings.setdefault(key, str(value))
    if not settings.get("image_base_url"):
        settings["image_base_url"] = settings.get("model_base_url", "")
    if not settings.get("image_api_key"):
        settings["image_api_key"] = settings.get("model_api_key", "")
    if not settings.get("image_model_name"):
        settings["image_model_name"] = settings.get("model_name", "gpt-image-1")
    if not settings.get("chat_base_url"):
        settings["chat_base_url"] = settings.get("model_base_url", "")
    if not settings.get("chat_api_key"):
        settings["chat_api_key"] = settings.get("model_api_key", "")
    return settings
