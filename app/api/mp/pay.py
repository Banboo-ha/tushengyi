import json
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db import get_db
from app.models import PaymentOrder, User
from app.services.ids import new_id
from app.services.points import grant_points
from app.services.settings import get_setting

router = APIRouter(prefix="/pay", tags=["mp-pay"])


class CreateOrderRequest(BaseModel):
    package_id: str


def pay_packages(db: Session) -> list[dict]:
    raw = get_setting(db, "wechat_pay_packages", "[]")
    try:
        packages = json.loads(raw)
    except Exception:
        packages = []
    return [item for item in packages if item.get("id") and int(item.get("amount_cents", 0)) > 0 and int(item.get("points", 0)) > 0]


def order_payload(order: PaymentOrder) -> dict:
    return {
        "order_id": order.id,
        "order_no": order.order_no,
        "package_id": order.package_id,
        "title": order.title,
        "amount_cents": order.amount_cents,
        "points": order.points,
        "status": order.status,
        "payment_available": False,
        "payment_params": None,
        "message": "微信支付能力配置中，请先在后台配置商户号、API v3 key 和证书信息。",
        "created_at": order.created_at.isoformat(),
        "paid_at": order.paid_at.isoformat() if order.paid_at else "",
    }


@router.get("/packages")
def packages(db: Session = Depends(get_db)):
    return {"list": pay_packages(db)}


@router.post("/orders")
def create_order(payload: CreateOrderRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    package = next((item for item in pay_packages(db) if item["id"] == payload.package_id), None)
    if not package:
        raise HTTPException(status_code=400, detail="充值套餐不存在")
    order = PaymentOrder(
        order_no=f"MP{int(time.time())}{new_id()[:10]}",
        user_id=user.id,
        package_id=package["id"],
        title=package.get("title") or f"{package['points']}积分",
        amount_cents=int(package["amount_cents"]),
        points=int(package["points"]),
        status="unpaid",
        channel="wechat",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order_payload(order)


@router.get("/orders/{order_id}")
def get_order(order_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    order = db.get(PaymentOrder, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order_payload(order)


def mark_order_paid(db: Session, order: PaymentOrder, transaction_id: str = "", raw: str = "") -> None:
    if order.status == "paid":
        return
    user = db.get(User, order.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    order.status = "paid"
    order.transaction_id = transaction_id
    order.notify_raw = raw[:4000]
    order.paid_at = datetime.utcnow()
    grant_points(db, user, order.points, f"微信充值 {order.title}", order.id)


@router.post("/notify/wechat")
async def wechat_notify(request: Request, db: Session = Depends(get_db)):
    raw = (await request.body()).decode("utf-8", errors="ignore")
    try:
        data = json.loads(raw or "{}")
    except Exception:
        data = {}
    order_no = data.get("out_trade_no") or data.get("order_no") or ""
    if not order_no:
        return {"code": "FAIL", "message": "missing order_no"}
    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == order_no).first()
    if not order:
        return {"code": "FAIL", "message": "order not found"}
    mark_order_paid(db, order, data.get("transaction_id") or "", raw)
    db.commit()
    return {"code": "SUCCESS", "message": "成功"}
