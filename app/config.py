import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("HAIBAO_DATA_DIR", str(BASE_DIR / "data")))
UPLOAD_DIR = Path(os.getenv("HAIBAO_UPLOAD_DIR", str(BASE_DIR / "uploads")))
PRD_APIKEY_FILE = BASE_DIR / "PRD" / "APIkey.md"

DATABASE_URL = os.getenv("HAIBAO_DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")
SECRET_KEY = os.getenv("HAIBAO_SECRET_KEY", "change-this-secret-before-production")
TOKEN_TTL_SECONDS = int(os.getenv("HAIBAO_TOKEN_TTL_SECONDS", str(60 * 60 * 24 * 7)))
MAX_UPLOAD_SIZE = int(os.getenv("HAIBAO_MAX_UPLOAD_SIZE", str(10 * 1024 * 1024)))
MAX_UPLOAD_RAW_SIZE = int(os.getenv("HAIBAO_MAX_UPLOAD_RAW_SIZE", str(30 * 1024 * 1024)))
UPLOAD_IMAGE_MAX_SIDE = int(os.getenv("HAIBAO_UPLOAD_IMAGE_MAX_SIDE", "2200"))
UPLOAD_IMAGE_JPEG_QUALITY = int(os.getenv("HAIBAO_UPLOAD_IMAGE_JPEG_QUALITY", "88"))
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
WORKER_POLL_SECONDS = float(os.getenv("HAIBAO_WORKER_POLL_SECONDS", "3"))
WORKER_BATCH_SIZE = int(os.getenv("HAIBAO_WORKER_BATCH_SIZE", "1"))
TASK_STALE_SECONDS = int(os.getenv("HAIBAO_TASK_STALE_SECONDS", str(60 * 30)))


def ensure_runtime_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def read_default_model_config() -> dict:
    config = {
        "model_base_url": "http://43.159.147.220:8080/v1",
        "model_api_key": "",
        "model_name": "gpt-5.5",
        "mock_mode": "true",
    }
    if not PRD_APIKEY_FILE.exists():
        return config

    text = PRD_APIKEY_FILE.read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        line = raw_line.strip().replace("：", ":")
        if "API地址" in line and ":" in line:
            config["model_base_url"] = line.split(":", 1)[1].strip()
        if "API key" in line and ":" in line:
            config["model_api_key"] = line.split(":", 1)[1].strip()
    return config
