from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import ALLOWED_IMAGE_EXTENSIONS, MAX_UPLOAD_SIZE, UPLOAD_DIR
from app.services.ids import new_id


async def save_upload(file: UploadFile) -> dict:
    original = file.filename or "image"
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="当前格式不支持，请上传 jpg、png 或 webp")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="图片过大，请压缩后重新上传")

    name = f"{new_id()}{suffix}"
    path = UPLOAD_DIR / name
    path.write_bytes(data)
    return {
        "storage_path": str(path),
        "image_url": f"/uploads/{name}",
        "file_size": len(data),
    }

