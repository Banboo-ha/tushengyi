from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import current_user, optional_user
from app.db import get_db
from app.models import PosterLike, PosterVersion, PosterWork, User

router = APIRouter(prefix="/works", tags=["h5-works"])


def is_real_image_url(image_url: str) -> bool:
    url = (image_url or "").lower().split("?", 1)[0]
    return url.endswith((".jpg", ".jpeg", ".png", ".webp"))


def plaza_item(
    version: PosterVersion,
    work: PosterWork,
    liked_version_ids: Optional[set[str]] = None,
    author_name: str = "",
) -> dict:
    liked_version_ids = liked_version_ids or set()
    return {
        "work_id": work.id,
        "version_id": version.id,
        "version_no": version.version_no,
        "title": work.title,
        "author_name": author_name or "图生意用户",
        "cover_url": version.image_url,
        "latest_version": work.latest_version,
        "likes_count": version.likes_count or 0,
        "liked_by_me": version.id in liked_version_ids,
        "featured_order": version.featured_order or 0,
        "created_at": version.created_at.isoformat(),
        "edit_instruction": version.edit_instruction,
    }


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
                "likes_count": version.likes_count or 0,
                "featured_order": version.featured_order or 0,
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
def plaza_works(
    limit: int = Query(default=60, ge=1, le=200),
    user: Optional[User] = Depends(optional_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(PosterVersion, PosterWork, User)
        .join(PosterWork, PosterVersion.work_id == PosterWork.id)
        .join(User, PosterWork.user_id == User.id)
        .filter(PosterWork.is_saved.is_(True), PosterWork.is_deleted.is_(False))
        .order_by(PosterVersion.likes_count.desc(), PosterVersion.created_at.desc())
        .limit(limit * 3)
        .all()
    )
    rows = [(version, work, author) for version, work, author in rows if is_real_image_url(version.image_url)][:limit]
    liked_version_ids = liked_versions(db, user.id, [version.id for version, _, _ in rows]) if user else set()
    return {"list": [plaza_item(version, work, liked_version_ids, author.username) for version, work, author in rows]}


@router.get("/featured")
def featured_works(user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    rows = (
        db.query(PosterVersion, PosterWork, User)
        .join(PosterWork, PosterVersion.work_id == PosterWork.id)
        .join(User, PosterWork.user_id == User.id)
        .filter(PosterWork.is_saved.is_(True), PosterWork.is_deleted.is_(False))
        .order_by(PosterVersion.likes_count.desc(), PosterVersion.created_at.desc())
        .limit(24)
        .all()
    )
    rows = [(version, work, author) for version, work, author in rows if is_real_image_url(version.image_url)][:4]
    liked_version_ids = liked_versions(db, user.id, [version.id for version, _, _ in rows]) if user else set()
    return {"list": [plaza_item(version, work, liked_version_ids, author.username) for version, work, author in rows[:4]]}


@router.get("/liked")
def liked_works(
    limit: int = Query(default=60, ge=1, le=200),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(PosterLike, PosterVersion, PosterWork, User)
        .join(PosterVersion, PosterLike.version_id == PosterVersion.id)
        .join(PosterWork, PosterLike.work_id == PosterWork.id)
        .join(User, PosterWork.user_id == User.id)
        .filter(
            PosterLike.user_id == user.id,
            PosterWork.is_saved.is_(True),
            PosterWork.is_deleted.is_(False),
        )
        .order_by(PosterLike.created_at.desc())
        .limit(limit * 3)
        .all()
    )
    rows = [(version, work, author) for _, version, work, author in rows if is_real_image_url(version.image_url)][:limit]
    liked_version_ids = {version.id for version, _, _ in rows}
    return {"list": [plaza_item(version, work, liked_version_ids, author.username) for version, work, author in rows]}


def liked_versions(db: Session, user_id: str, version_ids: list[str]) -> set[str]:
    if not version_ids:
        return set()
    likes = (
        db.query(PosterLike.version_id)
        .filter(PosterLike.user_id == user_id, PosterLike.version_id.in_(version_ids))
        .all()
    )
    return {row[0] for row in likes}


@router.post("/versions/{version_id}/like")
def like_version(version_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    version = db.get(PosterVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="作品不存在")
    work = db.get(PosterWork, version.work_id)
    if not work or not work.is_saved or work.is_deleted:
        raise HTTPException(status_code=404, detail="作品不存在")
    existing = (
        db.query(PosterLike)
        .filter(PosterLike.user_id == user.id, PosterLike.version_id == version.id)
        .first()
    )
    if existing:
        return {"version_id": version.id, "likes_count": version.likes_count or 0, "liked_by_me": True}
    db.add(PosterLike(user_id=user.id, work_id=work.id, version_id=version.id))
    version.likes_count = (version.likes_count or 0) + 1
    db.commit()
    db.refresh(version)
    return {
        "version_id": version.id,
        "likes_count": version.likes_count or 0,
        "liked_by_me": True,
    }


@router.get("/public/{version_id}")
def get_public_work_version(
    version_id: str,
    user: Optional[User] = Depends(optional_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(PosterVersion, PosterWork, User)
        .join(PosterWork, PosterVersion.work_id == PosterWork.id)
        .join(User, PosterWork.user_id == User.id)
        .filter(
            PosterVersion.id == version_id,
            PosterWork.is_saved.is_(True),
            PosterWork.is_deleted.is_(False),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="作品不存在")
    version, work, author = row
    liked_version_ids = liked_versions(db, user.id, [version.id]) if user else set()
    return plaza_item(version, work, liked_version_ids, author.username)


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
