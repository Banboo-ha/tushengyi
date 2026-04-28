from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db import get_db
from app.models import PosterVersion, PosterWork, User

router = APIRouter(prefix="/works", tags=["h5-works"])


def work_payload(work: PosterWork, versions: Optional[list[PosterVersion]] = None) -> dict:
    data = {
        "work_id": work.id,
        "title": work.title,
        "cover_url": work.cover_url,
        "latest_version": work.latest_version,
        "is_saved": work.is_saved,
        "created_at": work.created_at.isoformat(),
        "updated_at": work.updated_at.isoformat(),
    }
    if versions is not None:
        data["versions"] = [
            {
                "version_id": version.id,
                "version_no": version.version_no,
                "image_url": version.image_url,
                "edit_instruction": version.edit_instruction,
                "created_at": version.created_at.isoformat(),
            }
            for version in versions
        ]
    return data


@router.get("")
def list_works(user: User = Depends(current_user), db: Session = Depends(get_db)):
    works = (
        db.query(PosterWork)
        .filter(PosterWork.user_id == user.id, PosterWork.is_saved.is_(True), PosterWork.is_deleted.is_(False))
        .order_by(PosterWork.updated_at.desc())
        .all()
    )
    items = []
    for work in works:
        versions = (
            db.query(PosterVersion)
            .filter(PosterVersion.work_id == work.id)
            .order_by(PosterVersion.version_no.desc())
            .all()
        )
        for version in versions:
            items.append(
                {
                    "work_id": work.id,
                    "version_id": version.id,
                    "version_no": version.version_no,
                    "title": work.title,
                    "cover_url": version.image_url,
                    "latest_version": work.latest_version,
                    "is_saved": work.is_saved,
                    "created_at": version.created_at.isoformat(),
                    "updated_at": work.updated_at.isoformat(),
                    "edit_instruction": version.edit_instruction,
                }
            )
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return {"list": items}


@router.get("/plaza")
def plaza_works(limit: int = Query(default=60, ge=1, le=200), db: Session = Depends(get_db)):
    versions = (
        db.query(PosterVersion, PosterWork)
        .join(PosterWork, PosterVersion.work_id == PosterWork.id)
        .filter(PosterWork.is_saved.is_(True), PosterWork.is_deleted.is_(False))
        .order_by(PosterVersion.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "list": [
            {
                "work_id": work.id,
                "version_id": version.id,
                "version_no": version.version_no,
                "title": work.title,
                "cover_url": version.image_url,
                "latest_version": work.latest_version,
                "created_at": version.created_at.isoformat(),
                "edit_instruction": version.edit_instruction,
            }
            for version, work in versions
        ]
    }


@router.get("/{work_id}")
def get_work(work_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    work = db.get(PosterWork, work_id)
    if not work or work.user_id != user.id or work.is_deleted:
        raise HTTPException(status_code=404, detail="作品不存在")
    versions = (
        db.query(PosterVersion)
        .filter(PosterVersion.work_id == work.id)
        .order_by(PosterVersion.version_no.asc())
        .all()
    )
    return work_payload(work, versions)


@router.post("/{work_id}/save")
def save_work(work_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    work = db.get(PosterWork, work_id)
    if not work or work.user_id != user.id or work.is_deleted:
        raise HTTPException(status_code=404, detail="作品不存在")
    work.is_saved = True
    db.commit()
    db.refresh(work)
    return work_payload(work)
