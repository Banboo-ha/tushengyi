from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_admin
from app.db import get_db
from app.models import Admin, PosterTask

router = APIRouter(prefix="/tasks", tags=["admin-tasks"])


@router.get("")
def list_tasks(_: Admin = Depends(current_admin), db: Session = Depends(get_db)):
    tasks = db.query(PosterTask).order_by(PosterTask.created_at.desc()).limit(200).all()
    return {
        "list": [
            {
                "task_id": task.id,
                "user_id": task.user_id,
                "task_type": task.task_type,
                "status": task.status,
                "title": task.title,
                "poster_type": task.poster_type,
                "style": task.style,
                "ratio": task.ratio,
                "image_quality": task.image_quality,
                "points_cost": task.points_cost,
                "result_image_url": task.result_image_url,
                "error_message": task.error_message,
                "work_id": task.work_id,
                "version_id": task.version_id,
                "created_at": task.created_at.isoformat(),
            }
            for task in tasks
        ]
    }
