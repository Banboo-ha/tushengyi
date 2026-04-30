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
from app.services.settings import (
    PROMPT_TEMPLATE_MAIN_IMAGE,
    PROMPT_TEMPLATE_PRODUCT,
    PROMPT_TEMPLATE_PROMOTION,
    PROMPT_TEMPLATE_XIAOHONGSHU,
    get_int_setting,
    get_setting,
)


STYLE_LABELS = {
    "premium_commercial": "高级商业广告",
    "xiaohongshu": "小红书种草风",
    "ecommerce": "电商主图风",
    "minimal": "极简高级风",
}

POSTER_TYPE_LABELS = {
    "product": "产品广告海报",
    "xiaohongshu": "小红书种草图",
    "main_image": "电商主图",
    "promotion": "活动促销海报",
}

PROMPT_TEMPLATE_DEFAULTS = {
    "product": PROMPT_TEMPLATE_PRODUCT,
    "xiaohongshu": PROMPT_TEMPLATE_XIAOHONGSHU,
    "main_image": PROMPT_TEMPLATE_MAIN_IMAGE,
    "promotion": PROMPT_TEMPLATE_PROMOTION,
}

REFERENCE_TYPE_LABELS = {
    "background": "背景图",
    "logo": "Logo参考图",
    "style": "品牌风格参考图",
    "layout": "排版模板参考图",
    "color": "色彩参考图",
    "other": "参考图",
    "": "参考图",
}

QUALITY_COSTS = {
    "medium": 8,
    "high": 10,
}

QUALITY_LABELS = {
    "medium": "高清",
    "high": "超清",
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


def reference_material_lines(product_images: list[UploadedImage], reference_images: list[UploadedImage]) -> tuple[str, str]:
    product_line = f"参考素材：提供产品图 {len(product_images)} 张，请将其作为关键视觉参考。" if product_images else "参考素材：未提供产品图。"
    if not reference_images:
        return product_line, "参考素材：未提供其他参考图。"

    grouped: dict[str, int] = {}
    for image in reference_images:
        label = REFERENCE_TYPE_LABELS.get(image.reference_type or "other", "参考图")
        grouped[label] = grouped.get(label, 0) + 1
    lines = [
        f"参考素材：提供{label} {count} 张，请将其作为关键视觉参考。"
        for label, count in grouped.items()
    ]
    return product_line, "\n".join(lines)


def render_prompt_template(template: str, values: dict[str, str]) -> str:
    text = template
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value or "无")
    return text.strip()


def build_generate_prompt(db: Session, task: PosterTask, product_images: list[UploadedImage], reference_images: list[UploadedImage]) -> str:
    poster_type = task.poster_type if task.poster_type in POSTER_TYPE_LABELS else "product"
    template = get_setting(
        db,
        f"prompt_template_{poster_type}",
        PROMPT_TEMPLATE_DEFAULTS[poster_type],
    ).strip() or PROMPT_TEMPLATE_DEFAULTS[poster_type]
    product_reference, reference_materials = reference_material_lines(product_images, reference_images)
    return render_prompt_template(template, {
        "poster_type": poster_type,
        "poster_type_label": POSTER_TYPE_LABELS.get(poster_type, "产品广告海报"),
        "title": task.title,
        "subtitle": task.subtitle or "无",
        "selling_points": task.selling_points or "无",
        "product_count": str(len(product_images)),
        "reference_count": str(len(reference_images)),
        "product_reference": product_reference,
        "reference_materials": reference_materials,
        "style_label": STYLE_LABELS.get(task.style, task.style or "无"),
        "ratio": task.ratio,
        "quality_label": QUALITY_LABELS.get(task.image_quality, task.image_quality or "高清"),
    })


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
    poster_type: str,
    ratio: str,
    image_quality: str = "medium",
) -> PosterTask:
    title = title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="请填写主标题")
    if style not in STYLE_LABELS:
        raise HTTPException(status_code=400, detail="请选择海报风格")
    if poster_type not in POSTER_TYPE_LABELS:
        raise HTTPException(status_code=400, detail="请选择生成类型")
    if ratio not in {"1:1", "3:4", "4:5", "9:16", "16:9"}:
        raise HTTPException(status_code=400, detail="画幅比例不支持")
    if image_quality not in QUALITY_COSTS:
        raise HTTPException(status_code=400, detail="图片质量不支持")

    product_images = validate_images(db, user.id, product_image_ids, "product", 1, 4)
    reference_images = validate_images(db, user.id, reference_image_ids, "reference", 0, 4)
    cost = QUALITY_COSTS[image_quality]

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
        poster_type=poster_type,
        ratio=ratio,
        image_quality=image_quality,
        points_cost=cost,
    )
    task.prompt = build_generate_prompt(db, task, product_images, reference_images)
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
        poster_type=source_task.poster_type if source_task else "product",
        ratio=source_task.ratio if source_task else "3:4",
        image_quality=source_task.image_quality if source_task else "medium",
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
            base_url=get_setting(db, "model_base_url") or get_setting(db, "image_base_url"),
            api_key=get_setting(db, "model_api_key") or get_setting(db, "image_api_key"),
            model=get_setting(db, "model_name", "gpt-5.5"),
            mock_mode=mock_mode,
            api_type="responses",
            size_mode=get_setting(db, "image_size_mode", "ratio_standard"),
            response_format=get_setting(db, "image_response_format", ""),
            quality=task.image_quality or get_setting(db, "image_quality", "auto"),
            file_field=get_setting(db, "image_file_field", "image"),
            generation_action=get_setting(db, "image_generation_action", ""),
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
