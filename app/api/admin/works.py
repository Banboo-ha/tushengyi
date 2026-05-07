from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import current_admin
from app.db import get_db
from app.models import Admin, PosterVersion, PosterWork

router = APIRouter(prefix="/works", tags=["admin-works"])


class FeaturedRequest(BaseModel):
    version_ids: list[str] = Field(default_factory=list)


class LikesRequest(BaseModel):
    likes_count: int = Field(default=0, ge=0)


class BatchLikesRequest(BaseModel):
    version_ids: list[str] = Field(default_factory=list)
    amount: int = Field(default=0, ge=0)


class BatchDeleteRequest(BaseModel):
    work_ids: list[str] = Field(default_factory=list)


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
                        "likes_count": version.likes_count or 0,
                        "featured_order": version.featured_order or 0,
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


@router.get("/featured")
def featured_works(_: Admin = Depends(current_admin), db: Session = Depends(get_db)):
    rows = (
        db.query(PosterVersion, PosterWork)
        .join(PosterWork, PosterVersion.work_id == PosterWork.id)
        .filter(PosterVersion.featured_order > 0, PosterWork.is_deleted.is_(False))
        .order_by(PosterVersion.featured_order.asc())
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
                "likes_count": version.likes_count or 0,
                "featured_order": version.featured_order or 0,
            }
            for version, work in rows
        ]
    }


@router.put("/featured")
def update_featured(payload: FeaturedRequest, _: Admin = Depends(current_admin), db: Session = Depends(get_db)):
    version_ids = [version_id for version_id in payload.version_ids if version_id]
    if len(version_ids) > 4:
        raise HTTPException(status_code=400, detail="首页最多展示 4 个作品")
    if len(set(version_ids)) != len(version_ids):
        raise HTTPException(status_code=400, detail="精选作品不能重复")

    versions = db.query(PosterVersion).filter(PosterVersion.id.in_(version_ids)).all() if version_ids else []
    found = {version.id: version for version in versions}
    if len(found) != len(version_ids):
        raise HTTPException(status_code=400, detail="有作品版本不存在")

    if version_ids:
        works = db.query(PosterWork).filter(PosterWork.id.in_({version.work_id for version in versions})).all()
        work_map = {work.id: work for work in works}
        if any(not work_map.get(version.work_id) or work_map[version.work_id].is_deleted for version in versions):
            raise HTTPException(status_code=400, detail="不能选择已删除作品")

    db.query(PosterVersion).filter(PosterVersion.featured_order > 0).update(
        {"featured_order": 0},
        synchronize_session=False,
    )
    for index, version_id in enumerate(version_ids, start=1):
        found[version_id].featured_order = index
    db.commit()
    return featured_works(_, db)


@router.post("/versions/{version_id}/likes")
def update_version_likes(
    version_id: str,
    payload: LikesRequest,
    _: Admin = Depends(current_admin),
    db: Session = Depends(get_db),
):
    version = db.get(PosterVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="作品版本不存在")
    version.likes_count = payload.likes_count
    db.commit()
    db.refresh(version)
    return {
        "version_id": version.id,
        "likes_count": version.likes_count or 0,
        "featured_order": version.featured_order or 0,
    }


@router.post("/versions/batch-likes")
def batch_add_likes(
    payload: BatchLikesRequest,
    _: Admin = Depends(current_admin),
    db: Session = Depends(get_db),
):
    version_ids = list(dict.fromkeys(version_id for version_id in payload.version_ids if version_id))
    if not version_ids:
        raise HTTPException(status_code=400, detail="请选择作品版本")
    versions = db.query(PosterVersion).filter(PosterVersion.id.in_(version_ids)).all()
    if not versions:
        raise HTTPException(status_code=400, detail="没有找到作品版本")
    for version in versions:
        version.likes_count = (version.likes_count or 0) + payload.amount
    db.commit()
    return {"updated": len(versions), "amount": payload.amount}


@router.post("/batch-delete")
def batch_delete_works(
    payload: BatchDeleteRequest,
    _: Admin = Depends(current_admin),
    db: Session = Depends(get_db),
):
    work_ids = list(dict.fromkeys(work_id for work_id in payload.work_ids if work_id))
    if not work_ids:
        raise HTTPException(status_code=400, detail="请选择作品")
    works = db.query(PosterWork).filter(PosterWork.id.in_(work_ids)).all()
    if not works:
        raise HTTPException(status_code=400, detail="没有找到作品")
    for work in works:
        work.is_deleted = True
    db.commit()
    return {"updated": len(works)}


@router.post("/{work_id}/delete")
def delete_work(work_id: str, _: Admin = Depends(current_admin), db: Session = Depends(get_db)):
    work = db.get(PosterWork, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="作品不存在")
    work.is_deleted = True
    db.commit()
    return {"work_id": work.id, "is_deleted": work.is_deleted}
