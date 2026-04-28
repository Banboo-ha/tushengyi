import json
import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import TASK_STALE_SECONDS, UPLOAD_DIR
from app.db import SessionLocal
from app.models import PosterTask, PosterVersion, PosterWork, UploadedImage, User
from app.services.ai_client import AIImageClient
from app.services.points import consume_points, refund_points
from app.services.settings import get_int_setting, get_setting


STYLE_LABELS = {
    "premium_commercial": "高级商业广告",
    "xiaohongshu": "小红书种草风",
    "ecommerce": "电商主图风",
    "minimal": "极简高级风",
}

logger = logging.getLogger(__name__)


def parse_ids(value: str) -> list[str]:
    try:
        data = json.loads(value or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def dump_ids(ids: Iterable[str]) -> str:
    return json.dumps(list(ids), ensure_ascii=False)


def validate_images(db: Session, user_id: str, ids: list[str], image_type: str, min_count: int, max_count: int) -> list[UploadedImage]:
    if len(ids) < min_count:
        raise HTTPException(status_code=400, detail="请至少上传 1 张产品图")
    if len(ids) > max_count:
        raise HTTPException(status_code=400, detail=f"最多只能上传 {max_count} 张")
    images = db.query(UploadedImage).filter(UploadedImage.id.in_(ids), UploadedImage.user_id == user_id).all() if ids else []
    found = {image.id: image for image in images}
    if len(found) != len(ids):
        raise HTTPException(status_code=400, detail="图片不存在或无权使用")
    if any(image.image_type != image_type for image in images):
        raise HTTPException(status_code=400, detail="图片类型不匹配")
    return [found[image_id] for image_id in ids]


def build_generate_prompt(task: PosterTask, product_images: list[UploadedImage], reference_images: list[UploadedImage]) -> str:
    refs = "、".join(filter(None, [image.reference_type or "其他参考" for image in reference_images])) or "无"
    return f"""请根据用户上传的产品图生成一张商业宣传海报。
产品主体需要清晰、真实、突出，参考上传产品图的外观、材质、包装和颜色。
产品图数量：{len(product_images)} 张。参考图类型：{refs}。
如果用户上传了背景、Logo、品牌风格或模板参考图，请在画面氛围、排版方向、色彩风格上参考，但不要破坏产品主体识别。
海报主标题为：{task.title}
副标题为：{task.subtitle or "无"}
卖点文案为：{task.selling_points or "无"}
整体风格为：{STYLE_LABELS.get(task.style, task.style)}
画幅比例为：{task.ratio}
画面需要具备移动端宣传海报质感，构图清晰，文案层级明确，避免杂乱，避免低质量拼贴感。"""


def build_modify_prompt(task: PosterTask) -> str:
    return f"""请基于当前海报继续优化，不要完全偏离原始产品。
保留产品主体和核心文案，根据用户修改意见进行调整。
用户修改意见：{task.edit_instruction}
请输出一张新的完整海报图，保持商业宣传海报质感，画面清晰，排版合理。"""


def local_path_from_url(image_url: str) -> str:
    if image_url.startswith("/uploads/"):
        path = UPLOAD_DIR / image_url.removeprefix("/uploads/")
        if path.exists():
            return str(path)
    return ""


def task_input_image_paths(db: Session, task: PosterTask) -> list[str]:
    paths: list[str] = []
    if task.task_type == "modify" and task.version_id:
        current_version = db.get(PosterVersion, task.version_id)
        if current_version:
            path = local_path_from_url(current_version.image_url)
            if path:
                paths.append(path)

    image_ids = parse_ids(task.product_image_ids) + parse_ids(task.reference_image_ids)
    if image_ids:
        images = db.query(UploadedImage).filter(UploadedImage.id.in_(image_ids)).all()
        by_id = {image.id: image for image in images}
        for image_id in image_ids:
            image = by_id.get(image_id)
            if image and image.storage_path and Path(image.storage_path).exists():
                paths.append(image.storage_path)

    seen = set()
    unique_paths = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)
    return unique_paths


def create_generate_task(
    db: Session,
    user: User,
    product_image_ids: list[str],
    reference_image_ids: list[str],
    title: str,
    subtitle: str,
    selling_points: str,
    style: str,
    ratio: str,
) -> PosterTask:
    title = title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="请填写主标题")
    if style not in STYLE_LABELS:
        raise HTTPException(status_code=400, detail="请选择海报风格")
    if ratio not in {"1:1", "3:4", "4:5", "9:16", "16:9"}:
        raise HTTPException(status_code=400, detail="画幅比例不支持")

    product_images = validate_images(db, user.id, product_image_ids, "product", 1, 4)
    reference_images = validate_images(db, user.id, reference_image_ids, "reference", 0, 4)
    cost = get_int_setting(db, "generate_cost", 10)

    task = PosterTask(
        user_id=user.id,
        task_type="generate",
        status="pending",
        product_image_ids=dump_ids(product_image_ids),
        reference_image_ids=dump_ids(reference_image_ids),
        title=title,
        subtitle=subtitle.strip(),
        selling_points=selling_points.strip(),
        style=style,
        ratio=ratio,
        points_cost=cost,
    )
    task.prompt = build_generate_prompt(task, product_images, reference_images)
    db.add(task)
    db.flush()
    consume_points(db, user, cost, "生成消耗", task.id)
    db.commit()
    db.refresh(task)
    return task


def create_modify_task(db: Session, user: User, work_id: str, version_id: str, edit_instruction: str) -> PosterTask:
    edit_instruction = edit_instruction.strip()
    if not edit_instruction:
        raise HTTPException(status_code=400, detail="请填写修改意见")
    work = db.get(PosterWork, work_id)
    version = db.get(PosterVersion, version_id)
    if not work or not version or work.user_id != user.id or version.work_id != work.id or work.is_deleted:
        raise HTTPException(status_code=404, detail="作品不存在")
    cost = get_int_setting(db, "modify_cost", 8)
    source_task = db.get(PosterTask, version.task_id)
    task = PosterTask(
        user_id=user.id,
        task_type="modify",
        status="pending",
        product_image_ids=source_task.product_image_ids if source_task else "[]",
        reference_image_ids=source_task.reference_image_ids if source_task else "[]",
        title=work.title,
        style=source_task.style if source_task else "",
        ratio=source_task.ratio if source_task else "3:4",
        edit_instruction=edit_instruction,
        points_cost=cost,
        work_id=work.id,
        version_id=version.id,
    )
    task.prompt = build_modify_prompt(task)
    db.add(task)
    db.flush()
    consume_points(db, user, cost, "修改消耗", task.id)
    db.commit()
    db.refresh(task)
    return task


def process_task(task_id: str, allow_running: bool = False) -> bool:
    db = SessionLocal()
    try:
        task = db.get(PosterTask, task_id)
        if not task:
            return False
        if task.status == "pending":
            task.status = "running"
            db.commit()
        elif not (allow_running and task.status == "running"):
            return False
        user = db.get(User, task.user_id)
        if not user:
            raise RuntimeError("用户不存在")

        mock_mode = get_setting(db, "mock_mode", "true").lower() in {"1", "true", "yes", "on"}
        client = AIImageClient(
            base_url=get_setting(db, "image_base_url") or get_setting(db, "model_base_url"),
            api_key=get_setting(db, "image_api_key") or get_setting(db, "model_api_key"),
            model=get_setting(db, "image_model_name") or get_setting(db, "model_name", "gpt-image-1"),
            mock_mode=mock_mode,
            api_type=get_setting(db, "image_api_type", "images_generations"),
            size_mode=get_setting(db, "image_size_mode", "ratio_standard"),
            response_format=get_setting(db, "image_response_format", ""),
            quality=get_setting(db, "image_quality", "auto"),
            file_field=get_setting(db, "image_file_field", "image"),
        )
        image_paths = task_input_image_paths(db, task)
        image_url = client.generate_image(task.prompt, task.ratio, title=task.title or "AI 海报", image_paths=image_paths)
        task.result_image_url = image_url
        task.status = "success"

        if task.task_type == "modify" and task.work_id:
            work = db.get(PosterWork, task.work_id)
            if not work:
                raise RuntimeError("作品不存在")
            version_no = work.latest_version + 1
        else:
            work = PosterWork(
                user_id=task.user_id,
                title=task.title or "未命名海报",
                cover_url=image_url,
                latest_version=1,
                is_saved=True,
            )
            db.add(work)
            db.flush()
            task.work_id = work.id
            version_no = 1

        version = PosterVersion(
            work_id=work.id,
            task_id=task.id,
            version_no=version_no,
            image_url=image_url,
            edit_instruction=task.edit_instruction,
        )
        db.add(version)
        db.flush()
        work.cover_url = image_url
        work.latest_version = version_no
        task.version_id = version.id
        db.commit()
        return True
    except Exception as exc:
        db.rollback()
        task = db.get(PosterTask, task_id)
        if task:
            user = db.get(User, task.user_id)
            task.status = "failed"
            task.error_message = str(exc) or traceback.format_exc(limit=1)
            if user and task.points_cost > 0:
                refund_points(db, user, task.points_cost, "失败退还", task.id)
            db.commit()
        logger.exception("poster task failed: %s", task_id)
        return False
    finally:
        db.close()


def reset_stale_running_tasks() -> int:
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(seconds=TASK_STALE_SECONDS)
        tasks = (
            db.query(PosterTask)
            .filter(PosterTask.status == "running", PosterTask.updated_at < cutoff)
            .all()
        )
        for task in tasks:
            task.status = "pending"
            task.error_message = "任务因 worker 重启或超时被重新排队"
        db.commit()
        return len(tasks)
    finally:
        db.close()


def pending_task_ids(limit: int = 1) -> list[str]:
    db = SessionLocal()
    try:
        tasks = (
            db.query(PosterTask)
            .filter(PosterTask.status == "pending")
            .order_by(PosterTask.created_at.asc())
            .limit(limit)
            .all()
        )
        return [task.id for task in tasks]
    finally:
        db.close()


def process_next_tasks(limit: int = 1) -> int:
    count = 0
    for task_id in pending_task_ids(limit=limit):
        if process_task(task_id):
            count += 1
    return count
