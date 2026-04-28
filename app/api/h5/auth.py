from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.services.points import grant_points
from app.services.security import create_token, hash_password, verify_password
from app.services.settings import get_int_setting

router = APIRouter(prefix="/auth", tags=["h5-auth"])


class AuthRequest(BaseModel):
    username: str
    password: str


def user_payload(user: User) -> dict:
    return {
        "user_id": user.id,
        "username": user.username,
        "token": create_token(user.id, "user"),
        "points_balance": user.points_balance,
    }


@router.post("/register")
def register(payload: AuthRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="请输入用户名")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    exists = db.query(User).filter(User.username == username).first()
    if exists:
        raise HTTPException(status_code=400, detail="用户名已被注册")

    user = User(username=username, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    grant_points(db, user, get_int_setting(db, "signup_points", 50), "注册赠送")
    db.commit()
    db.refresh(user)
    return user_payload(user)


@router.post("/login")
def login(payload: AuthRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    if user.status != "normal":
        raise HTTPException(status_code=403, detail="账号已被禁用")
    return user_payload(user)

