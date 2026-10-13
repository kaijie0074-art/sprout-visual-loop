"""真实 VLM 客户端（OpenAI 兼容多模态协议）。

接口：describe(image_path) -> 结构化页面描述 dict，字段与意图树分层置信路由
（intent_tree.py）对齐：
  - page_kind: 页面类型判断
  - requires_human_review: 手绘稿/低可读性 → 强制人工确认
  - components: [{name, present, confidence}]——present=图中是否真实可见，
    confidence=组件类型判定置信度（0-1）。模型只陈述图中真实存在的内容，
    不做"常见 APP 应该有"的补全。

环境变量：
  VISUAL_LOOP_API_KEY   必填（与 ASR 共用凭证）
  VISUAL_LOOP_BASE_URL  可选（默认智谱开放平台；可指向任意 OpenAI 兼容服务）
  VISUAL_LOOP_VLM_MODEL 可选（默认 glm-4v-flash）
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request


class VlmConfigError(RuntimeError):
    """缺少真实 VLM 凭证。"""


PROMPT = (
    "分析这张 App 界面截图或手绘稿，输出 JSON（只输出 JSON，不要解释）：\n"
    '{"page_kind": "<页面类型，如 video_feed_home/home/unknown，手绘稿或看不清用 unknown>",'
    '"requires_human_review": <bool，手绘稿/低可读性必须 true>,'
    '"components": [{"name": "<组件类型，取值 video_feed/banner/logo/community/mall/'
    "login_screen/search/tab_bar/feed_cards 之一或自拟英文 snake_case>, "
    '"present": <bool，图中是否真实可见该组件——只陈述可见的，不要补全"常见 APP 应该有的"组件>,'
    '"confidence": <0-1，组件类型判定的置信度，拿不准就给低分>]}\n'
    "铁律：只描述图中真实存在的内容；不存在就不要编。"
)


class VlmClient:
    def __init__(self, *, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        self._api_key = api_key or os.environ.get("VISUAL_LOOP_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self._base_url = (
            base_url
            or os.environ.get("VISUAL_LOOP_BASE_URL")
            or os.environ.get("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
        )
        self._model = model or os.environ.get("VISUAL_LOOP_VLM_MODEL", "glm-4v-flash")
        if not self._api_key:
            raise VlmConfigError(
                "需要真实 VLM 凭证：请设置 VISUAL_LOOP_API_KEY（或 OPENAI_API_KEY），"
                "可选 VISUAL_LOOP_BASE_URL / VISUAL_LOOP_VLM_MODEL。"
            )

    def describe(self, image_path: str, scenario: str = "") -> dict:
        """scenario 参数仅为接口兼容保留，真实实现不使用（由图像内容决定输出）。"""
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        ext = "png" if image_path.lower().endswith(".png") else "jpeg"
        body = json.dumps(
            {
                "model": self._model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}},
                            {"type": "text", "text": PROMPT},
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url.rstrip('/')}/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self._api_key}"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = payload["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1].removeprefix("json").strip()
        out = json.loads(text)
        out.setdefault("components", [])
        out.setdefault("requires_human_review", False)
        return out
