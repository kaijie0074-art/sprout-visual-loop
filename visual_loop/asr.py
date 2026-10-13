"""真实 ASR 客户端（OpenAI 兼容 /audio/transcriptions 协议）。

接口：transcribe(audio_path) -> {"raw": 转写文本, "lang": 语言标记}。
方言口音（粤语混合等）交由所接 ASR 服务的方言能力；下游 normalize.py
负责口音词归一，假设分层不变。

环境变量：
  VISUAL_LOOP_API_KEY   必填（与 VLM 共用凭证）
  VISUAL_LOOP_BASE_URL  可选（默认智谱开放平台）
"""
from __future__ import annotations

import json
import os
import urllib.request
import uuid




class AsrConfigError(RuntimeError):
    """缺少真实 ASR 凭证。"""


class AsrClient:
    def __init__(self, *, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        self._api_key = api_key or os.environ.get("VISUAL_LOOP_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self._base_url = (
            base_url
            or os.environ.get("VISUAL_LOOP_BASE_URL")
            or os.environ.get("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
        )
        self._model = model or os.environ.get("VISUAL_LOOP_ASR_MODEL", "glm-asr")
        if not self._api_key:
            raise AsrConfigError(
                "需要真实 ASR 凭证：请设置 VISUAL_LOOP_API_KEY（或 OPENAI_API_KEY）。"
            )

    def transcribe(self, audio_path: str) -> dict:
        with open(audio_path, "rb") as f:
            audio = f.read()
        boundary = uuid.uuid4().hex
        parts = []
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\n{self._model}\r\n".encode()
        )
        fname = os.path.basename(audio_path)
        parts.append(
            (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
                f"filename=\"{fname}\"\r\nContent-Type: application/octet-stream\r\n\r\n"
            ).encode()
            + audio
        )
        parts.append(f"--{boundary}--\r\n".encode())
        req = urllib.request.Request(
            f"{self._base_url.rstrip('/')}/audio/transcriptions",
            data=b"".join(parts),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                     "Authorization": f"Bearer {self._api_key}"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = payload.get("text", "")
        return {"raw": text, "lang": payload.get("language", "auto"), "audio_key": fname}

