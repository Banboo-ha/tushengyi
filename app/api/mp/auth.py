import hashlib
import json
import secrets
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.services.points import grant_points
from app.services.security import create_token, hash_password
from app.services.settings import get_int_setting, get_setting

router = APIRouter(prefix="/auth", tags=["mp-auth"])


class MpLoginRequest(BaseModel):
    code: str


def mock_openid(code: str) -> str:
    digest = hashlib.sha1((code or secrets.token_hex(8)).encode("utf-8")).hexdigest()[:24]
    return f"dev_{digest}"


def fetch_wechat_session(db: Session, code: str) -> dict:
    appid = get_setting(db, "wechat_appid", "")
    secret = get_setting(db, "wechat_app_secret", "")
    mock_mode = get_setting(db, "wechat_login_mock_mode", "true").lower() in {"1", "true", "yes", "on"}
    if mock_mode or not appid or not secret:
        return {"openid": mock_openid(code), "session_key": "", "unionid": ""}

    query = urllib.parse.urlencode(
        {
            "appid": appid,
            "secret": secret,
            "js_code": code,
            "grant_type": "authorization_code",
        }
    )
    url = f"https://api.weixin.qq.com/sns/jscode2session?{query}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"微信登录失败：{exc}")
    if data.get("errcode"):
        raise HTTPException(status_code=400, detail=f"微信登录失败：{data.get('errmsg') or data.get('errcode')}")
    if not data.get("openid"):
        raise HTTPException(status_code=400, detail="微信登录失败：未返回 openid")
    return data


@router.post("/login")
def login(payload: MpLoginRequest, db: Session = Depends(get_db)):
    if not payload.code.strip():
        raise HTTPException(status_code=400, detail="缺少微信登录 code")
    session = fetch_wechat_session(db, payload.code.strip())
    openid = session["openid"]
    user = db.query(User).filter(User.wechat_openid == openid).first()
    created = False
    if user is None:
        username = f"wx_{openid[-10:]}"
        while db.query(User).filter(User.username == username).first():
            username = f"wx_{secrets.token_hex(5)}"
        user = User(
            username=username,
            password_hash=hash_password(secrets.token_urlsafe(18)),
            wechat_openid=openid,
            wechat_unionid=session.get("unionid") or "",
            wechat_session_key=session.get("session_key") or "",
        )
        db.add(user)
        db.flush()
        grant_points(db, user, get_int_setting(db, "signup_points", 50), "小程序注册赠送")
        created = True
    else:
        user.wechat_unionid = session.get("unionid") or user.wechat_unionid
        user.wechat_session_key = session.get("session_key") or ""
    db.commit()
    db.refresh(user)
    return {
        "user_id": user.id,
        "username": user.username,
        "token": create_token(user.id, "user"),
        "points_balance": user.points_balance,
        "member_status": "normal",
        "created": created,
    }
