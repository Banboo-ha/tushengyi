from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db import get_db
from app.models import PointsRecord, User

router = APIRouter(prefix="/points", tags=["h5-points"])


@router.get("/records")
def records(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(PointsRecord)
        .filter(PointsRecord.user_id == user.id)
        .order_by(PointsRecord.created_at.desc())
        .limit(100)
        .all()
    )
    return {
        "balance": user.points_balance,
        "records": [
            {
                "id": row.id,
                "type": row.type,
                "amount": row.amount,
                "scene": row.scene,
                "related_id": row.related_id,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    }

