import base64
import json
import mimetypes
import os
import textwrap
import urllib.error
import urllib.request
from html import escape
from pathlib import Path
from typing import Optional

from app.config import UPLOAD_DIR
from app.services.ids import new_id


class AIImageClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        mock_mode: bool = True,
        api_type: str = "images_generations",
        size_mode: str = "ratio_standard",
        response_format: str = "",
        quality: str = "auto",
        file_field: str = "image",
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.mock_mode = mock_mode
        self.api_type = api_type
        self.size_mode = size_mode
        self.response_format = response_format
        self.quality = quality
        self.file_field = file_field or "image"

    def generate_image(self, prompt: str, ratio: str, title: str = "AI 海报", image_paths: Optional[list[str]] = None) -> str:
        image_paths = [path for path in (image_paths or []) if path and Path(path).exists()]
        if self.mock_mode:
            return self._mock_image(prompt, ratio, title)
        if self.api_type == "responses":
            return self._responses_image(prompt, ratio, image_paths)
        if self.api_type == "images_edits" or image_paths:
            return self._openai_image_edit(prompt, ratio, image_paths)
        return self._openai_image(prompt, ratio)

    def test_image(self) -> dict:
        test_paths = [self._test_reference_image()] if self.api_type == "images_edits" else []
        image_url = self.generate_image("生成一张用于接口连通性测试的极简蓝色产品海报，不要包含敏感内容。", "1:1", "接口测试", test_paths)
        return {
            "ok": True,
            "api_type": self.api_type,
            "model": self.model,
            "image_inputs": len(test_paths),
            "image_url": image_url,
        }

    def _mock_image(self, prompt: str, ratio: str, title: str) -> str:
        width, height = self._ratio_size(ratio)
        filename = f"generated-{new_id()}.svg"
        path = UPLOAD_DIR / filename
        subtitle = "AI 产品海报生成器"
        lines = [escape(line) for line in textwrap.wrap(prompt.replace("\n", " "), width=22)[:5]]
        body = "".join(
            f'<text x="70" y="{height - 230 + i * 34}" font-size="24" fill="#30405f" opacity="0.78">{line}</text>'
            for i, line in enumerate(lines)
        )
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#eaf4ff"/>
      <stop offset="0.46" stop-color="#ffffff"/>
      <stop offset="1" stop-color="#d9ddff"/>
    </linearGradient>
    <linearGradient id="card" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#2f73ff"/>
      <stop offset="1" stop-color="#8c58ff"/>
    </linearGradient>
    <filter id="shadow"><feDropShadow dx="0" dy="22" stdDeviation="26" flood-color="#4d6fff" flood-opacity=".24"/></filter>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg)"/>
  <rect x="46" y="52" width="{width - 92}" height="{height - 104}" rx="44" fill="#fff" filter="url(#shadow)"/>
  <rect x="82" y="92" width="{width - 164}" height="{int(height * 0.48)}" rx="34" fill="url(#card)"/>
  <circle cx="{int(width * 0.70)}" cy="{int(height * 0.26)}" r="{int(width * 0.16)}" fill="#ffffff" opacity=".22"/>
  <circle cx="{int(width * 0.42)}" cy="{int(height * 0.32)}" r="{int(width * 0.11)}" fill="#ffffff" opacity=".16"/>
  <text x="112" y="164" font-size="34" font-weight="700" fill="#ffffff">{escape(subtitle)}</text>
  <text x="112" y="238" font-size="64" font-weight="800" fill="#ffffff">{escape(title[:16])}</text>
  <text x="112" y="304" font-size="30" fill="#eef3ff">商业质感 · 移动端 · 清晰排版</text>
  <rect x="{int(width * 0.44)}" y="{int(height * 0.29)}" width="{int(width * 0.31)}" height="{int(height * 0.28)}" rx="26" fill="#fff" opacity=".92"/>
  <rect x="{int(width * 0.48)}" y="{int(height * 0.34)}" width="{int(width * 0.23)}" height="{int(height * 0.18)}" rx="22" fill="#f4f7ff"/>
  <text x="{int(width * 0.505)}" y="{int(height * 0.44)}" font-size="42" font-weight="800" fill="#5074ff">AI</text>
  <text x="70" y="{height - 286}" font-size="32" font-weight="700" fill="#18243d">生成摘要</text>
  {body}
</svg>"""
        path.write_text(svg, encoding="utf-8")
        return f"/uploads/{filename}"

    def _openai_image(self, prompt: str, ratio: str) -> str:
        size = self._api_size(ratio)
        endpoint = f"{self.base_url}/images/generations"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": size,
        }
        if self.response_format:
            payload["response_format"] = self.response_format
        if self.quality:
            payload["quality"] = self.quality
        result = self._post_json(endpoint, payload, timeout=120)

        item = (result.get("data") or [{}])[0]
        if item.get("b64_json"):
            raw = base64.b64decode(item["b64_json"])
            filename = f"generated-{new_id()}.png"
            (UPLOAD_DIR / filename).write_bytes(raw)
            return f"/uploads/{filename}"
        if item.get("url"):
            return self._download_remote_image(item["url"])
        raise RuntimeError("AI 接口未返回图片")

    def _openai_image_edit(self, prompt: str, ratio: str, image_paths: list[str]) -> str:
        if not image_paths:
            raise RuntimeError("图生图接口需要至少一张产品图或参考图")
        endpoint = f"{self.base_url}/images/edits"
        fields = {
            "model": self.model,
            "prompt": prompt,
            "n": "1",
            "size": self._api_size(ratio),
        }
        if self.response_format:
            fields["response_format"] = self.response_format
        if self.quality:
            fields["quality"] = self.quality
        files = [(self.file_field, path) for path in image_paths[:8]]
        result = self._post_multipart(endpoint, fields, files, timeout=180)
        return self._image_result(result)

    def _responses_image(self, prompt: str, ratio: str, image_paths: list[str]) -> str:
        endpoint = f"{self.base_url}/responses"
        content = [{"type": "input_text", "text": prompt}]
        for path in image_paths[:8]:
            content.append({"type": "input_image", "image_url": self._data_url(path)})
        payload = {
            "model": self.model,
            "input": [{"role": "user", "content": content}] if image_paths else prompt,
            "tools": [{"type": "image_generation"}],
        }
        result = self._post_json(endpoint, payload, timeout=120)
        for output in result.get("output", []):
            if output.get("type") in {"image_generation_call", "output_image"} and output.get("result"):
                return self._save_b64_image(output["result"])
            for content in output.get("content", []):
                if content.get("type") in {"output_image", "image"}:
                    if content.get("b64_json"):
                        return self._save_b64_image(content["b64_json"])
                    if content.get("image_url"):
                        return self._download_remote_image(content["image_url"])
        raise RuntimeError("Responses 接口未返回图片")

    def _image_result(self, result: dict) -> str:
        item = (result.get("data") or [{}])[0]
        if item.get("b64_json"):
            return self._save_b64_image(item["b64_json"])
        if item.get("url"):
            return self._download_remote_image(item["url"])
        raise RuntimeError("AI 接口未返回图片")

    def _download_remote_image(self, url: str) -> str:
        filename = f"generated-{new_id()}.png"
        path = UPLOAD_DIR / filename
        with urllib.request.urlopen(url, timeout=120) as response:
            path.write_bytes(response.read())
        return f"/uploads/{filename}"

    def _save_b64_image(self, data: str) -> str:
        raw = base64.b64decode(data)
        filename = f"generated-{new_id()}.png"
        (UPLOAD_DIR / filename).write_bytes(raw)
        return f"/uploads/{filename}"

    def _post_json(self, endpoint: str, payload: dict, timeout: int = 60) -> dict:
        if not self.base_url:
            raise RuntimeError("请先配置模型 Base URL")
        if not self.api_key:
            raise RuntimeError("请先配置模型 API Key")
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"AI 接口失败：HTTP {exc.code} {detail[:500]}")
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, PermissionError) or "Operation not permitted" in str(reason):
                raise RuntimeError("AI 接口失败：当前运行环境没有外网访问权限，请用具备网络权限的 worker 运行，或检查服务器防火墙/安全组")
            raise RuntimeError(f"AI 接口失败：网络连接失败 {reason}")
        except Exception as exc:
            raise RuntimeError(f"AI 接口失败：{exc}")

    def _post_multipart(self, endpoint: str, fields: dict, files: list[tuple[str, str]], timeout: int = 60) -> dict:
        if not self.base_url:
            raise RuntimeError("请先配置模型 Base URL")
        if not self.api_key:
            raise RuntimeError("请先配置模型 API Key")

        boundary = f"----haibao{new_id()}"
        body = bytearray()
        for name, value in fields.items():
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
            body.extend(str(value).encode("utf-8"))
            body.extend(b"\r\n")
        for field_name, path in files:
            filename = os.path.basename(path)
            mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(
                f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode()
            )
            body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode())
            body.extend(Path(path).read_bytes())
            body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode())

        request = urllib.request.Request(
            endpoint,
            data=bytes(body),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"AI 接口失败：HTTP {exc.code} {detail[:500]}")
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, PermissionError) or "Operation not permitted" in str(reason):
                raise RuntimeError("AI 接口失败：当前运行环境没有外网访问权限，请用具备网络权限的 worker 运行，或检查服务器防火墙/安全组")
            raise RuntimeError(f"AI 接口失败：网络连接失败 {reason}")
        except Exception as exc:
            raise RuntimeError(f"AI 接口失败：{exc}")

    def _data_url(self, path: str) -> str:
        mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        data = base64.b64encode(Path(path).read_bytes()).decode("utf-8")
        return f"data:{mime_type};base64,{data}"

    def _test_reference_image(self) -> str:
        path = UPLOAD_DIR / "model-test-reference.png"
        if not path.exists():
            raw = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAEAAAAAkCAIAAACJ8g1GAAAAPUlEQVR4nO3OMQEAAAgDINc/9F0hQ4FIFtB0Z2YAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgG0kAAAFxF7P8AAAAAElFTkSuQmCC"
            )
            path.write_bytes(raw)
        return str(path)

    def _ratio_size(self, ratio: str) -> tuple[int, int]:
        return {
            "1:1": (1024, 1024),
            "3:4": (1024, 1536),
            "4:5": (1024, 1536),
            "9:16": (1024, 1792),
            "16:9": (1792, 1024),
        }.get(ratio, (1024, 1536))

    def _api_size(self, ratio: str) -> str:
        if self.size_mode == "auto":
            return "auto"
        if self.size_mode and self.size_mode not in {"ratio_standard", "mock_ratio"}:
            return self.size_mode
        return {
            "1:1": "1024x1024",
            "3:4": "1024x1536",
            "4:5": "1024x1536",
            "9:16": "1024x1536",
            "16:9": "1536x1024",
        }.get(ratio, "1024x1536")


class AITextClient:
    def __init__(self, base_url: str, api_key: str, model: str, api_type: str = "chat_completions"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.api_type = api_type

    def test_chat(self) -> dict:
        if self.api_type == "responses":
            result = self._post_json(
                f"{self.base_url}/responses",
                {
                    "model": self.model,
                    "input": "请只回复 pong",
                    "max_output_tokens": 16,
                },
            )
            text = result.get("output_text") or ""
            if not text:
                for output in result.get("output", []):
                    for content in output.get("content", []):
                        if content.get("type") in {"output_text", "text"}:
                            text += content.get("text", "")
            return {"ok": True, "api_type": self.api_type, "model": self.model, "reply": text.strip()}

        result = self._post_json(
            f"{self.base_url}/chat/completions",
            {
                "model": self.model,
                "messages": [{"role": "user", "content": "请只回复 pong"}],
                "max_tokens": 16,
            },
        )
        reply = (((result.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        return {"ok": True, "api_type": self.api_type, "model": self.model, "reply": reply}

    def _post_json(self, endpoint: str, payload: dict) -> dict:
        if not self.base_url:
            raise RuntimeError("请先配置模型 Base URL")
        if not self.api_key:
            raise RuntimeError("请先配置模型 API Key")
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"AI 接口失败：HTTP {exc.code} {detail[:500]}")
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, PermissionError) or "Operation not permitted" in str(reason):
                raise RuntimeError("AI 接口失败：当前运行环境没有外网访问权限，请用具备网络权限的 worker 运行，或检查服务器防火墙/安全组")
            raise RuntimeError(f"AI 接口失败：网络连接失败 {reason}")
        except Exception as exc:
            raise RuntimeError(f"AI 接口失败：{exc}")
