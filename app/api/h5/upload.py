from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db import get_db
from app.models import UploadedImage, User
from app.services.upload import save_upload

router = APIRouter(prefix="/upload", tags=["h5-upload"])


@router.post("/image")
async def upload_image(
    image_type: str = Form(...),
    reference_type: str = Form(""),
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if image_type not in {"product", "reference"}:
        raise HTTPException(status_code=400, detail="图片类型不正确")
    if image_type == "product":
        reference_type = ""
    else:
        reference_type = reference_type or "other"
    saved = await save_upload(file)
    image = UploadedImage(
        user_id=user.id,
        image_url=saved["image_url"],
        storage_path=saved["storage_path"],
        image_type=image_type,
        reference_type=reference_type,
        file_size=saved["file_size"],
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return {
        "image_id": image.id,
        "image_url": image.image_url,
        "image_type": image.image_type,
        "reference_type": image.reference_type,
    }

