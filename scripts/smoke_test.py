import io
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal
from app.main import app
from app.models import PosterTask, User
from app.services.points import consume_points
from app.services.poster import process_task


client = TestClient(app)


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def assert_ok(response):
    if response.status_code >= 400:
        raise AssertionError(f"{response.status_code}: {response.text}")
    return response.json()


def main():
    admin = assert_ok(client.post("/api/admin/auth/login", json={"username": "admin", "password": "admin123"}))
    admin_token = admin["token"]
    original_settings = assert_ok(client.get("/api/admin/settings", headers=auth_headers(admin_token)))
    settings_payload = {key: original_settings[key] for key in [
        "model_base_url",
        "model_api_key",
        "model_name",
        "mock_mode",
        "chat_api_type",
        "chat_base_url",
        "chat_api_key",
        "chat_model_name",
        "image_api_type",
        "image_base_url",
        "image_api_key",
        "image_model_name",
        "image_size_mode",
        "image_response_format",
        "image_quality",
        "image_file_field",
        "image_generation_action",
        "prompt_common",
        "prompt_template_product",
        "prompt_template_xiaohongshu",
        "prompt_template_main_image",
        "prompt_template_promotion",
        "signup_points",
        "generate_cost",
        "modify_cost",
        "task_timeout_seconds",
    ]}
    mock_settings = {
        **settings_payload,
        "mock_mode": "true",
        "signup_points": 50,
        "generate_cost": 10,
        "modify_cost": 8,
        "task_timeout_seconds": 300,
    }
    assert_ok(client.put("/api/admin/settings", headers=auth_headers(admin_token), json=mock_settings))

    username = f"smoke_{int(time.time())}"
    try:
        registered = assert_ok(client.post("/api/h5/auth/register", json={"username": username, "password": "123456"}))
        token = registered["token"]
        assert registered["points_balance"] == 50
        stale_task_id = ""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username).one()
            stale_task = PosterTask(
                user_id=user.id,
                task_type="generate",
                status="running",
                title="超时任务",
                style="premium_commercial",
                poster_type="product",
                ratio="3:4",
                image_quality="medium",
                points_cost=8,
                created_at=datetime.utcnow() - timedelta(minutes=10),
                updated_at=datetime.utcnow() - timedelta(minutes=10),
            )
            db.add(stale_task)
            db.flush()
            stale_task_id = stale_task.id
            consume_points(db, user, 8, "生成消耗", stale_task.id)
            db.commit()
        finally:
            db.close()
        active_after_timeout = assert_ok(client.get("/api/h5/poster/tasks?status=active", headers=auth_headers(token)))
        assert all(item["task_id"] != stale_task_id for item in active_after_timeout["list"])
        stale_payload = assert_ok(client.get(f"/api/h5/poster/task/{stale_task_id}", headers=auth_headers(token)))
        assert stale_payload["status"] == "failed"
        assert "超时" in stale_payload["error_message"]
        profile_after_timeout = assert_ok(client.get("/api/h5/user/profile", headers=auth_headers(token)))
        assert profile_after_timeout["points_balance"] == 50

        image = io.BytesIO(b"fake image bytes for smoke test")
        uploaded = assert_ok(
            client.post(
                "/api/h5/upload/image",
                headers=auth_headers(token),
                data={"image_type": "product", "reference_type": ""},
                files={"file": ("product.png", image, "image/png")},
            )
        )
        no_copy_task = assert_ok(
            client.post(
                "/api/h5/poster/generate",
                headers=auth_headers(token),
                json={
                    "product_image_ids": [uploaded["image_id"]],
                    "reference_image_ids": [],
                    "title": "",
                    "subtitle": "",
                    "selling_points": "",
                    "style": "premium_commercial",
                    "poster_type": "product",
                    "ratio": "3:4",
                    "image_quality": "medium",
                },
            )
        )
        process_task(no_copy_task["task_id"])
        no_copy_task = assert_ok(client.get(f"/api/h5/poster/task/{no_copy_task['task_id']}", headers=auth_headers(token)))
        assert no_copy_task["status"] == "success"

        task = assert_ok(
            client.post(
                "/api/h5/poster/generate",
                headers=auth_headers(token),
                json={
                    "product_image_ids": [uploaded["image_id"]],
                    "reference_image_ids": [],
                    "title": "好水出好鱼",
                    "subtitle": "山美水美鱼更美",
                    "selling_points": "现打现捞，鲜活直达",
                    "style": "premium_commercial",
                    "poster_type": "product",
                    "ratio": "3:4",
                    "image_quality": "medium",
                },
            )
        )
        assert task["points_cost"] == 8
        process_task(task["task_id"])
        task = assert_ok(client.get(f"/api/h5/poster/task/{task['task_id']}", headers=auth_headers(token)))
        assert task["status"] == "success"
        assert task["work_id"]

        work = assert_ok(client.get(f"/api/h5/works/{task['work_id']}", headers=auth_headers(token)))
        assert work["is_saved"] is True
        works = assert_ok(client.get("/api/h5/works", headers=auth_headers(token)))
        assert any(item["work_id"] == task["work_id"] for item in works["list"])
        modify = assert_ok(
            client.post(
                "/api/h5/poster/modify",
                headers=auth_headers(token),
                json={
                    "work_id": task["work_id"],
                    "version_id": work["versions"][-1]["version_id"],
                    "edit_instruction": "背景更高级，标题更大",
                },
            )
        )
        process_task(modify["task_id"])
        modify = assert_ok(client.get(f"/api/h5/poster/task/{modify['task_id']}", headers=auth_headers(token)))
        assert modify["status"] == "success"
        works_after_modify = assert_ok(client.get("/api/h5/works", headers=auth_headers(token)))
        version_items = [item for item in works_after_modify["list"] if item["work_id"] == task["work_id"]]
        assert len(version_items) >= 2
        assert {item["version_no"] for item in version_items} >= {1, 2}

        featured_ids = [item["version_id"] for item in version_items[:2]]
        liked_target = featured_ids[0]
        liked = assert_ok(
            client.post(
                "/api/admin/works/versions/batch-likes",
                headers=auth_headers(admin_token),
                json={"version_ids": [liked_target], "amount": 10000},
            )
        )
        assert liked["updated"] == 1
        refreshed_work = assert_ok(client.get(f"/api/h5/works/{task['work_id']}", headers=auth_headers(token)))
        liked_version = next(item for item in refreshed_work["versions"] if item["version_id"] == liked_target)
        assert liked_version["likes_count"] >= 10000
        home_featured = assert_ok(client.get("/api/h5/works/featured", headers=auth_headers(token)))
        assert all(not item["cover_url"].endswith(".svg") for item in home_featured["list"])
        plaza = assert_ok(client.get("/api/h5/works/plaza", headers=auth_headers(token)))
        assert all(not item["cover_url"].endswith(".svg") for item in plaza["list"])
        like_once = assert_ok(client.post(f"/api/h5/works/versions/{liked_target}/like", headers=auth_headers(token)))
        assert like_once["likes_count"] == liked_version["likes_count"] + 1
        like_twice = assert_ok(client.post(f"/api/h5/works/versions/{liked_target}/like", headers=auth_headers(token)))
        assert like_twice["likes_count"] == like_once["likes_count"]
        my_likes = assert_ok(client.get("/api/h5/works/liked", headers=auth_headers(token)))
        assert isinstance(my_likes["list"], list)
        assert all(item["liked_by_me"] for item in my_likes["list"])

        users = assert_ok(client.get("/api/admin/users", headers=auth_headers(admin_token)))
        user_id = next(user["user_id"] for user in users["list"] if user["username"] == username)
        before_topup = assert_ok(client.get("/api/h5/user/profile", headers=auth_headers(token)))["points_balance"]
        topped = assert_ok(
            client.post(
                f"/api/admin/users/{user_id}/points",
                headers=auth_headers(admin_token),
                json={"amount": 5, "reason": "smoke"},
            )
        )
        assert topped["points_balance"] == before_topup + 5
        print("smoke ok")
    finally:
        assert_ok(client.put("/api/admin/settings", headers=auth_headers(admin_token), json=settings_payload))


if __name__ == "__main__":
    main()
