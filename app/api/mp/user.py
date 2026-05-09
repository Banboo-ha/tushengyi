from fastapi import APIRouter, Depends

from app.api.deps import current_user
from app.models import User

router = APIRouter(prefix="/user", tags=["mp-user"])


@router.get("/profile")
def profile(user: User = Depends(current_user)):
    return {
        "user_id": user.id,
        "username": user.username,
        "avatar": user.avatar,
        "points_balance": user.points_balance,
        "member_status": "normal",
        "is_wechat_user": bool(user.wechat_openid),
    }
