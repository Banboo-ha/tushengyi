from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import current_admin
from app.db import get_db
from app.models import Admin, PosterTask, User
from app.services.points import grant_points

router = APIRouter(prefix="/users", tags=["admin-users"])


class AddPointsRequest(BaseModel):
    amount: int
    reason: str = "管理员补发"


@router.get("")
def list_users(_: Admin = Depends(current_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return {
        "list": [
            {
                "user_id": user.id,
                "username": user.username,
                "points_balance": user.points_balance,
                "status": user.status,
                "created_at": user.created_at.isoformat(),
                "generate_count": db.query(PosterTask).filter(PosterTask.user_id == user.id).count(),
            }
            for user in users
        ],
    }


@router.post("/{user_id}/points")
def add_points(user_id: str, payload: AddPointsRequest, _: Admin = Depends(current_admin), db: Session = Depends(get_db)):
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="补发积分必须大于 0")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    grant_points(db, user, payload.amount, payload.reason or "管理员补发")
    db.commit()
    return {"user_id": user.id, "points_balance": user.points_balance}


@router.post("/{user_id}/disable")
def disable_user(user_id: str, _: Admin = Depends(current_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.status = "disabled"
    db.commit()
    return {"user_id": user.id, "status": user.status}
