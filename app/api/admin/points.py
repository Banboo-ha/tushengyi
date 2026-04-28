from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_admin
from app.db import get_db
from app.models import Admin, PointsRecord

router = APIRouter(prefix="/points", tags=["admin-points"])


@router.get("/records")
def records(_: Admin = Depends(current_admin), db: Session = Depends(get_db)):
    rows = db.query(PointsRecord).order_by(PointsRecord.created_at.desc()).limit(300).all()
    return {
        "records": [
            {
                "id": row.id,
                "user_id": row.user_id,
                "type": row.type,
                "amount": row.amount,
                "scene": row.scene,
                "related_id": row.related_id,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
    }

