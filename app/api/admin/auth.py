from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Admin
from app.services.security import create_token, verify_password

router = APIRouter(prefix="/auth", tags=["admin-auth"])


class AdminLoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: AdminLoginRequest, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == payload.username.strip()).first()
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=400, detail="管理员账号或密码错误")
    if admin.status != "normal":
        raise HTTPException(status_code=403, detail="管理员账号已禁用")
    return {
        "admin_id": admin.id,
        "username": admin.username,
        "token": create_token(admin.id, "admin"),
    }

