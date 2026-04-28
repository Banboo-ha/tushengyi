from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import PointsRecord, User


def add_points_record(
    db: Session,
    user: User,
    amount: int,
    record_type: str,
    scene: str,
    related_id: str = "",
) -> PointsRecord:
    user.points_balance += amount
    record = PointsRecord(
        user_id=user.id,
        type=record_type,
        amount=amount,
        scene=scene,
        related_id=related_id,
    )
    db.add(record)
    return record


def grant_points(db: Session, user: User, amount: int, scene: str, related_id: str = "") -> PointsRecord:
    return add_points_record(db, user, abs(amount), "gain", scene, related_id)


def consume_points(db: Session, user: User, amount: int, scene: str, related_id: str = "") -> PointsRecord:
    if user.status != "normal":
        raise HTTPException(status_code=403, detail="账号已被禁用")
    if user.points_balance < amount:
        raise HTTPException(status_code=400, detail="当前积分不足，无法生成")
    return add_points_record(db, user, -abs(amount), "consume", scene, related_id)


def refund_points(db: Session, user: User, amount: int, scene: str, related_id: str = "") -> PointsRecord:
    return add_points_record(db, user, abs(amount), "refund", scene, related_id)

