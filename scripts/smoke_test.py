import io
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app
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
        "signup_points",
        "generate_cost",
        "modify_cost",
    ]}
    mock_settings = {**settings_payload, "mock_mode": "true"}
    assert_ok(client.put("/api/admin/settings", headers=auth_headers(admin_token), json=mock_settings))

    username = f"smoke_{int(time.time())}"
    try:
        registered = assert_ok(client.post("/api/h5/auth/register", json={"username": username, "password": "123456"}))
        token = registered["token"]
        assert registered["points_balance"] == 50

        image = io.BytesIO(b"fake image bytes for smoke test")
        uploaded = assert_ok(
            client.post(
                "/api/h5/upload/image",
                headers=auth_headers(token),
                data={"image_type": "product", "reference_type": ""},
                files={"file": ("product.png", image, "image/png")},
            )
        )

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
                    "ratio": "3:4",
                },
            )
        )
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

        users = assert_ok(client.get("/api/admin/users", headers=auth_headers(admin_token)))
        user_id = next(user["user_id"] for user in users["list"] if user["username"] == username)
        topped = assert_ok(
            client.post(
                f"/api/admin/users/{user_id}/points",
                headers=auth_headers(admin_token),
                json={"amount": 5, "reason": "smoke"},
            )
        )
        assert topped["points_balance"] >= 37
        print("smoke ok")
    finally:
        assert_ok(client.put("/api/admin/settings", headers=auth_headers(admin_token), json=settings_payload))


if __name__ == "__main__":
    main()
