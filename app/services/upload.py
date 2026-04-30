from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import (
    ALLOWED_IMAGE_EXTENSIONS,
    MAX_UPLOAD_RAW_SIZE,
    MAX_UPLOAD_SIZE,
    UPLOAD_DIR,
    UPLOAD_IMAGE_JPEG_QUALITY,
    UPLOAD_IMAGE_MAX_SIDE,
)
from app.services.ids import new_id

try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except ImportError:
    Image = None
    ImageOps = None
    UnidentifiedImageError = Exception


def _to_upload_jpeg(data: bytes) -> bytes:
    if Image is None or ImageOps is None:
        return data
    try:
        with Image.open(BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((UPLOAD_IMAGE_MAX_SIDE, UPLOAD_IMAGE_MAX_SIDE))
            if image.mode in {"RGBA", "LA"}:
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.getchannel("A"))
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=UPLOAD_IMAGE_JPEG_QUALITY, optimize=True)
            return buffer.getvalue()
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="图片文件无法识别，请换一张图片")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"图片处理失败：{exc}")


async def save_upload(file: UploadFile) -> dict:
    original = file.filename or "image"
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="当前格式不支持，请上传 jpg、png 或 webp")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(data) > MAX_UPLOAD_RAW_SIZE:
        raise HTTPException(status_code=400, detail="图片过大，请先压缩后重新上传")

    stored_data = _to_upload_jpeg(data)
    if len(stored_data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="图片压缩后仍然过大，请换一张图片")

    name = f"{new_id()}.jpg"
    path = UPLOAD_DIR / name
    path.write_bytes(stored_data)
    return {
        "storage_path": str(path),
        "image_url": f"/uploads/{name}",
        "file_size": len(stored_data),
    }
