from textwrap import dedent

from sqlalchemy.orm import Session

from app.config import read_default_model_config
from app.models import Admin, SystemSetting
from app.services.security import hash_password


PROMPT_TEMPLATE_PRODUCT = dedent("""\
请设计一张具有产品宣传质感的产品海报。

海报类型：产品广告海报。

整体画面需要具备品牌广告感、产品主视觉质感、明确视觉焦点，并让文案与画面统一。

主标题：{{title}}
副标题：{{subtitle}}
内容文案：{{selling_points}}

{{product_reference}}
{{reference_materials}}

整体风格：{{style_label}}
画幅比例：{{ratio}}
图片质量：{{quality_label}}

请输出一张完成度高、适合正式展示的海报画面，避免界面截图感、避免排版杂乱、避免低质量拼贴感。""")

PROMPT_TEMPLATE_XIAOHONGSHU = dedent("""\
请设计一张具有小红书种草质感的营销海报。

海报类型：小红书种草图。

整体画面需要具备真实生活方式氛围、柔和但有吸引力的视觉焦点、适合社交媒体封面点击的构图，并让产品、场景和文案自然融合。

主标题：{{title}}
副标题：{{subtitle}}
内容文案：{{selling_points}}

{{product_reference}}
{{reference_materials}}

整体风格：{{style_label}}
画幅比例：{{ratio}}
图片质量：{{quality_label}}

请输出一张完成度高、适合小红书发布和分享的海报画面，避免界面截图感、避免过度堆字、避免低质量拼贴感。""")

PROMPT_TEMPLATE_MAIN_IMAGE = dedent("""\
请设计一张具有电商平台主图质感的商品展示图。

海报类型：电商主图。

整体画面需要突出商品主体、清晰呈现卖点和价格感/促销感，具备平台商品图的干净构图、明确层级和高点击率视觉表现。

主标题：{{title}}
副标题：{{subtitle}}
内容文案：{{selling_points}}

{{product_reference}}
{{reference_materials}}

整体风格：{{style_label}}
画幅比例：{{ratio}}
图片质量：{{quality_label}}

请输出一张完成度高、适合电商平台展示的主图画面，避免界面截图感、避免排版杂乱、避免低质量拼贴感。""")

PROMPT_TEMPLATE_PROMOTION = dedent("""\
请设计一张具有活动促销氛围的营销海报。

海报类型：活动促销海报。

整体画面需要具备强活动感、明确优惠/活动视觉焦点、醒目的文案层级和适合门店或线上传播的商业宣传质感。

主标题：{{title}}
副标题：{{subtitle}}
内容文案：{{selling_points}}

{{product_reference}}
{{reference_materials}}

整体风格：{{style_label}}
画幅比例：{{ratio}}
图片质量：{{quality_label}}

请输出一张完成度高、适合正式活动宣传的海报画面，避免界面截图感、避免信息杂乱、避免低质量拼贴感。""")


DEFAULT_SETTINGS = {
    "signup_points": "50",
    "generate_cost": "10",
    "modify_cost": "8",
    "mock_mode": "true",
    "chat_api_type": "responses",
    "chat_base_url": "",
    "chat_api_key": "",
    "chat_model_name": "gpt-5.5",
    "image_api_type": "responses",
    "image_base_url": "",
    "image_api_key": "",
    "image_model_name": "gpt-5.5",
    "image_size_mode": "ratio_standard",
    "image_response_format": "",
    "image_quality": "",
    "image_file_field": "image",
    "image_generation_action": "",
    "prompt_template_product": PROMPT_TEMPLATE_PRODUCT,
    "prompt_template_xiaohongshu": PROMPT_TEMPLATE_XIAOHONGSHU,
    "prompt_template_main_image": PROMPT_TEMPLATE_MAIN_IMAGE,
    "prompt_template_promotion": PROMPT_TEMPLATE_PROMOTION,
}


def init_defaults(db: Session) -> None:
    model_defaults = read_default_model_config()
    defaults = {**DEFAULT_SETTINGS, **model_defaults}
    defaults["chat_base_url"] = model_defaults.get("model_base_url", "")
    defaults["chat_api_key"] = model_defaults.get("model_api_key", "")
    defaults["chat_model_name"] = model_defaults.get("model_name", "gpt-5.5")
    defaults["image_base_url"] = model_defaults.get("model_base_url", "")
    defaults["image_api_key"] = model_defaults.get("model_api_key", "")
    defaults["image_model_name"] = model_defaults.get("model_name", "gpt-5.5")
    for key, value in defaults.items():
        if db.get(SystemSetting, key) is None:
            db.add(SystemSetting(key=key, value=str(value)))
    upgrade_legacy_model_defaults(db)

    admin = db.query(Admin).filter(Admin.username == "admin").first()
    if admin is None:
        db.add(Admin(username="admin", password_hash=hash_password("admin123")))
    db.commit()


def upgrade_legacy_model_defaults(db: Session) -> None:
    replacements = {
        "model_name": {"gpt-image-1": "gpt-5.5", "": "gpt-5.5"},
        "chat_api_type": {"chat_completions": "responses", "": "responses"},
        "chat_model_name": {"gpt-4o-mini": "gpt-5.5", "": "gpt-5.5"},
        "image_api_type": {"images_edits": "responses", "images_generations": "responses", "": "responses"},
        "image_model_name": {"gpt-image-1": "gpt-5.5", "": "gpt-5.5"},
    }
    for key, values in replacements.items():
        setting = db.get(SystemSetting, key)
        if setting and setting.value in values:
            setting.value = values[setting.value]


def get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.get(SystemSetting, key)
    return setting.value if setting else default


def get_int_setting(db: Session, key: str, default: int) -> int:
    try:
        return int(get_setting(db, key, str(default)))
    except ValueError:
        return default


def set_setting(db: Session, key: str, value: str) -> None:
    setting = db.get(SystemSetting, key)
    if setting is None:
        db.add(SystemSetting(key=key, value=value))
    else:
        setting.value = value


def all_settings(db: Session) -> dict:
    settings = {row.key: row.value for row in db.query(SystemSetting).all()}
    model_defaults = read_default_model_config()
    defaults = {**DEFAULT_SETTINGS, **model_defaults}
    defaults["chat_base_url"] = model_defaults.get("model_base_url", "")
    defaults["chat_api_key"] = model_defaults.get("model_api_key", "")
    defaults["chat_model_name"] = model_defaults.get("model_name", "gpt-5.5")
    defaults["image_base_url"] = model_defaults.get("model_base_url", "")
    defaults["image_api_key"] = model_defaults.get("model_api_key", "")
    defaults["image_model_name"] = model_defaults.get("model_name", "gpt-5.5")
    for key, value in defaults.items():
        settings.setdefault(key, str(value))
    if not settings.get("image_base_url"):
        settings["image_base_url"] = settings.get("model_base_url", "")
    if not settings.get("image_api_key"):
        settings["image_api_key"] = settings.get("model_api_key", "")
    if not settings.get("image_model_name"):
        settings["image_model_name"] = settings.get("model_name", "gpt-5.5")
    if not settings.get("chat_base_url"):
        settings["chat_base_url"] = settings.get("model_base_url", "")
    if not settings.get("chat_api_key"):
        settings["chat_api_key"] = settings.get("model_api_key", "")
    return settings
