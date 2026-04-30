from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import current_admin
from app.db import get_db
from app.models import Admin
from app.services.ai_client import AIImageClient, AITextClient
from app.services.settings import (
    PROMPT_TEMPLATE_MAIN_IMAGE,
    PROMPT_TEMPLATE_PRODUCT,
    PROMPT_TEMPLATE_PROMOTION,
    PROMPT_TEMPLATE_XIAOHONGSHU,
    all_settings,
    set_setting,
)

router = APIRouter(prefix="/settings", tags=["admin-settings"])


class SettingsRequest(BaseModel):
    model_base_url: str = ""
    model_api_key: str = ""
    model_name: str = "gpt-5.5"
    mock_mode: str = "true"
    chat_api_type: str = "responses"
    chat_base_url: str = ""
    chat_api_key: str = ""
    chat_model_name: str = "gpt-5.5"
    image_api_type: str = "responses"
    image_base_url: str = ""
    image_api_key: str = ""
    image_model_name: str = "gpt-5.5"
    image_size_mode: str = "ratio_standard"
    image_response_format: str = ""
    image_quality: str = ""
    image_file_field: str = "image"
    image_generation_action: str = ""
    prompt_template_product: str = PROMPT_TEMPLATE_PRODUCT
    prompt_template_xiaohongshu: str = PROMPT_TEMPLATE_XIAOHONGSHU
    prompt_template_main_image: str = PROMPT_TEMPLATE_MAIN_IMAGE
    prompt_template_promotion: str = PROMPT_TEMPLATE_PROMOTION
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
    if values.get("model_base_url"):
        set_setting(db, "chat_base_url", str(values["model_base_url"]))
        set_setting(db, "image_base_url", str(values["model_base_url"]))
    if values.get("model_api_key"):
        set_setting(db, "chat_api_key", str(values["model_api_key"]))
        set_setting(db, "image_api_key", str(values["model_api_key"]))
    if values.get("model_name"):
        set_setting(db, "chat_model_name", str(values["model_name"]))
        set_setting(db, "image_model_name", str(values["model_name"]))
    set_setting(db, "chat_api_type", "responses")
    set_setting(db, "image_api_type", "responses")
    db.commit()
    return {**all_settings(db), "model_specs": model_specs()}


@router.post("/test")
def test_model(payload: TestModelRequest, _: Admin = Depends(current_admin), db: Session = Depends(get_db)):
    settings = all_settings(db)
    try:
        if payload.target == "chat":
            client = AITextClient(
                base_url=settings.get("model_base_url") or settings.get("chat_base_url", ""),
                api_key=settings.get("model_api_key") or settings.get("chat_api_key", ""),
                model=settings.get("model_name") or "gpt-5.5",
                api_type="responses",
            )
            return client.test_chat()
        if payload.target == "image":
            client = AIImageClient(
                base_url=settings.get("model_base_url") or settings.get("image_base_url", ""),
                api_key=settings.get("model_api_key") or settings.get("image_api_key", ""),
                model=settings.get("model_name") or "gpt-5.5",
                mock_mode=False,
                api_type="responses",
                size_mode=settings.get("image_size_mode") or "ratio_standard",
                response_format=settings.get("image_response_format") or "",
                quality=settings.get("image_quality") or "",
                file_field=settings.get("image_file_field") or "image",
                generation_action=settings.get("image_generation_action") or "",
            )
            return client.test_image()
        if payload.target == "responses_diagnostics":
            client = AIImageClient(
                base_url=settings.get("model_base_url") or settings.get("image_base_url", ""),
                api_key=settings.get("model_api_key") or settings.get("image_api_key", ""),
                model=settings.get("model_name") or "gpt-5.5",
                mock_mode=False,
                api_type="responses",
                size_mode=settings.get("image_size_mode") or "ratio_standard",
                response_format=settings.get("image_response_format") or "",
                quality=settings.get("image_quality") or "",
                file_field=settings.get("image_file_field") or "image",
                generation_action=settings.get("image_generation_action") or "",
            )
            return client.diagnose_responses_image()
    except Exception as exc:
        if payload.target in {"image", "responses_diagnostics"}:
            preview_paths = []
            try:
                preview_paths = [client._test_reference_image()] if "client" in locals() else []
                preview = client.preview_image_request(
                    "生成一张用于接口连通性测试的极简蓝色产品海报，不要包含敏感内容。",
                    "1:1",
                    preview_paths,
                )
                raise HTTPException(status_code=400, detail={"message": str(exc), "request_preview": preview})
            except HTTPException:
                raise
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=str(exc))
    raise HTTPException(status_code=400, detail="测试目标不正确")


def model_specs() -> list[dict]:
    return [
        {
            "key": "chat_completions",
            "title": "兼容文本：Chat Completions",
            "endpoint": "POST /v1/chat/completions",
            "request": '{"model":"gpt-5.5","messages":[{"role":"user","content":"你好"}]}',
            "response": "读取 choices[0].message.content",
            "note": "适合 OpenAI 兼容对话模型；只返回文本，不负责出图。",
        },
        {
            "key": "responses",
            "title": "统一模型：Responses + image_generation",
            "endpoint": "POST /v1/responses",
            "request": '{"model":"gpt-5.5","input":[{"role":"user","content":[{"type":"input_text","text":"生成海报"},{"type":"input_image","image_url":"data:image/png;base64,..."}]}],"tools":[{"type":"image_generation","size":"1024x1536","quality":"high","action":"edit"}],"tool_choice":{"type":"image_generation"}}',
            "response": "图片读取 output[] 中 image_generation_call.result；文本优先读取 output_text。",
            "note": "当前统一主流程；文本和图片生成都使用同一个 gpt-5.5 Responses 模型，图片通过 image_generation 工具完成。",
        },
        {
            "key": "images_generations",
            "title": "图片模型：Images Generations",
            "endpoint": "POST /v1/images/generations",
            "request": '{"model":"gpt-image-1","prompt":"生成一张海报","size":"1024x1536","quality":"high","n":1}',
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
