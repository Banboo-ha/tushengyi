from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_admin
from app.db import get_db
from app.models import Admin, PosterVersion, PosterWork

router = APIRouter(prefix="/works", tags=["admin-works"])


@router.get("")
def list_works(_: Admin = Depends(current_admin), db: Session = Depends(get_db)):
    works = db.query(PosterWork).order_by(PosterWork.created_at.desc()).limit(200).all()
    return {
        "list": [
            {
                "work_id": work.id,
                "user_id": work.user_id,
                "title": work.title,
                "cover_url": work.cover_url,
                "latest_version": work.latest_version,
                "is_saved": work.is_saved,
                "is_deleted": work.is_deleted,
                "created_at": work.created_at.isoformat(),
                "versions": [
                    {
                        "version_id": version.id,
                        "version_no": version.version_no,
                        "image_url": version.image_url,
                        "edit_instruction": version.edit_instruction,
                    }
                    for version in db.query(PosterVersion)
                    .filter(PosterVersion.work_id == work.id)
                    .order_by(PosterVersion.version_no.asc())
                    .all()
                ],
            }
            for work in works
        ]
    }


@router.post("/{work_id}/delete")
def delete_work(work_id: str, _: Admin = Depends(current_admin), db: Session = Depends(get_db)):
    work = db.get(PosterWork, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="作品不存在")
    work.is_deleted = True
    db.commit()
    return {"work_id": work.id, "is_deleted": work.is_deleted}

