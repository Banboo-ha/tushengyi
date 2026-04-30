from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db import get_db
from app.models import PosterTask, User
from app.services.poster import create_generate_task, create_modify_task, process_task

router = APIRouter(prefix="/poster", tags=["h5-poster"])


class GenerateRequest(BaseModel):
    product_image_ids: list[str]
    reference_image_ids: list[str] = []
    title: str
    subtitle: str = ""
    selling_points: str = ""
    style: str
    poster_type: str = "product"
    ratio: str = "3:4"
    image_quality: str = "medium"


class ModifyRequest(BaseModel):
    work_id: str
    version_id: str
    edit_instruction: str


def task_payload(task: PosterTask) -> dict:
    return {
        "task_id": task.id,
        "status": task.status,
        "points_cost": task.points_cost,
        "image_quality": task.image_quality,
        "poster_type": task.poster_type,
        "result_image_url": task.result_image_url,
        "work_id": task.work_id,
        "version_id": task.version_id,
        "error_message": task.error_message,
    }


@router.post("/generate")
def generate(
    payload: GenerateRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    task = create_generate_task(
        db,
        user,
        payload.product_image_ids,
        payload.reference_image_ids,
        payload.title,
        payload.subtitle,
        payload.selling_points,
        payload.style,
        payload.poster_type,
        payload.ratio,
        payload.image_quality,
    )
    background_tasks.add_task(process_task, task.id)
    return task_payload(task)


@router.post("/modify")
def modify(
    payload: ModifyRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    task = create_modify_task(db, user, payload.work_id, payload.version_id, payload.edit_instruction)
    background_tasks.add_task(process_task, task.id)
    return task_payload(task)


@router.get("/task/{task_id}")
def get_task(task_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = db.get(PosterTask, task_id)
    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task_payload(task)


@router.get("/tasks")
def list_tasks(
    status: str = Query("active"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = db.query(PosterTask).filter(PosterTask.user_id == user.id)
    if status == "active":
        query = query.filter(PosterTask.status.in_(["pending", "running"]))
    elif status in {"pending", "running", "success", "failed"}:
        query = query.filter(PosterTask.status == status)
    tasks = query.order_by(PosterTask.created_at.desc()).limit(20).all()
    return {"list": [task_payload(task) for task in tasks]}
