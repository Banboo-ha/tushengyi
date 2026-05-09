from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_admin
from app.db import get_db
from app.models import Admin, PaymentOrder, User

router = APIRouter(prefix="/orders", tags=["admin-orders"])


@router.get("")
def list_orders(_: Admin = Depends(current_admin), db: Session = Depends(get_db)):
    rows = (
        db.query(PaymentOrder, User)
        .join(User, PaymentOrder.user_id == User.id)
        .order_by(PaymentOrder.created_at.desc())
        .limit(200)
        .all()
    )
    return {
        "list": [
            {
                "order_id": order.id,
                "order_no": order.order_no,
                "user_id": order.user_id,
                "username": user.username,
                "package_id": order.package_id,
                "title": order.title,
                "amount_cents": order.amount_cents,
                "points": order.points,
                "status": order.status,
                "channel": order.channel,
                "prepay_id": order.prepay_id,
                "transaction_id": order.transaction_id,
                "created_at": order.created_at.isoformat(),
                "paid_at": order.paid_at.isoformat() if order.paid_at else "",
            }
            for order, user in rows
        ]
    }
