from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import current_admin
from app.db import get_db
from app.models import Admin
from app.services.ai_client import AIImageClient, AITextClient
from app.services.settings import all_settings, set_setting

router = APIRouter(prefix="/settings", tags=["admin-settings"])


class SettingsRequest(BaseModel):
    model_base_url: str = ""
    model_api_key: str = ""
    model_name: str = "gpt-image-1"
    mock_mode: str = "true"
    chat_api_type: str = "chat_completions"
    chat_base_url: str = ""
    chat_api_key: str = ""
    chat_model_name: str = "gpt-4o-mini"
    image_api_type: str = "images_edits"
    image_base_url: str = ""
    image_api_key: str = ""
    image_model_name: str = "gpt-image-1"
    image_size_mode: str = "ratio_standard"
    image_response_format: str = ""
    image_quality: str = ""
    image_file_field: str = "image"
    signup_points: int = 50
    generate_cost: int = 10
    modify_cost: int = 8


class TestModelRequest(BaseModel):
    target: str


@router.get("")
def get_settings(_: Admin = Depends(current_admin), db: Session = Depends(get_db)):
    return {**all_settings(db), "model_specs": model_specs()}


@router.put("")
def update_settings(payload: SettingsRequest, _: Admin = Depends(current_admin), db: Session = Depends(get_db)):
    values = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    for key, value in values.items():
        set_setting(db, key, str(value))
    if values.get("image_base_url"):
        set_setting(db, "model_base_url", str(values["image_base_url"]))
    if values.get("image_api_key"):
        set_setting(db, "model_api_key", str(values["image_api_key"]))
    if values.get("image_model_name"):
        set_setting(db, "model_name", str(values["image_model_name"]))
    db.commit()
    return {**all_settings(db), "model_specs": model_specs()}


@router.post("/test")
def test_model(payload: TestModelRequest, _: Admin = Depends(current_admin), db: Session = Depends(get_db)):
    settings = all_settings(db)
    try:
        if payload.target == "chat":
            client = AITextClient(
                base_url=settings.get("chat_base_url") or settings.get("model_base_url", ""),
                api_key=settings.get("chat_api_key") or settings.get("model_api_key", ""),
                model=settings.get("chat_model_name") or "gpt-4o-mini",
                api_type=settings.get("chat_api_type") or "chat_completions",
            )
            return client.test_chat()
        if payload.target == "image":
            client = AIImageClient(
                base_url=settings.get("image_base_url") or settings.get("model_base_url", ""),
                api_key=settings.get("image_api_key") or settings.get("model_api_key", ""),
                model=settings.get("image_model_name") or settings.get("model_name", "gpt-image-1"),
                mock_mode=False,
                api_type=settings.get("image_api_type") or "images_generations",
                size_mode=settings.get("image_size_mode") or "ratio_standard",
                response_format=settings.get("image_response_format") or "",
                quality=settings.get("image_quality") or "",
                file_field=settings.get("image_file_field") or "image",
            )
            return client.test_image()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    raise HTTPException(status_code=400, detail="测试目标不正确")


def model_specs() -> list[dict]:
    return [
        {
            "key": "chat_completions",
            "title": "对话模型：Chat Completions",
            "endpoint": "POST /v1/chat/completions",
            "request": '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"你好"}]}',
            "response": "读取 choices[0].message.content",
            "note": "适合 OpenAI 兼容对话模型；只返回文本，不负责出图。",
        },
        {
            "key": "responses",
            "title": "对话/多模态：Responses",
            "endpoint": "POST /v1/responses",
            "request": '{"model":"gpt-4o-mini","input":"你好"}',
            "response": "优先读取 output_text；复杂响应读取 output[].content[]",
            "note": "OpenAI 新项目推荐接口；兼容服务未必都支持。",
        },
        {
            "key": "images_generations",
            "title": "图片模型：Images Generations",
            "endpoint": "POST /v1/images/generations",
            "request": '{"model":"gpt-image-1","prompt":"生成一张海报","size":"1024x1536","n":1}',
            "response": "读取 data[0].b64_json 或 data[0].url",
            "note": "纯文生图，不会携带用户上传的产品图；不适合当前产品主流程。",
        },
        {
            "key": "images_edits",
            "title": "图片模型：Images Edits 图生图",
            "endpoint": "POST /v1/images/edits",
            "request": 'multipart/form-data: model, prompt, size, n, image=<产品图/参考图文件，可重复>',
            "response": "读取 data[0].b64_json 或 data[0].url",
            "note": "用于当前海报生成主流程，会把产品图、参考图或当前海报图作为图片输入传给模型。",
        },
    ]
