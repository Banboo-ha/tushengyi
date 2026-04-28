from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Admin, User
from app.services.security import bearer_token, decode_token


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    payload = decode_token(bearer_token(request), expected_role="user")
    user = db.get(User, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    if user.status != "normal":
        raise HTTPException(status_code=403, detail="账号已被禁用")
    return user


def current_admin(request: Request, db: Session = Depends(get_db)) -> Admin:
    payload = decode_token(bearer_token(request), expected_role="admin")
    admin = db.get(Admin, payload["sub"])
    if not admin or admin.status != "normal":
        raise HTTPException(status_code=401, detail="管理员登录已过期")
    return admin

