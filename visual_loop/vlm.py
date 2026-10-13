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
import base64
import json
import os
import re
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


def parse_model_json(text: str) -> dict:
    """解析模型输出的 JSON，容忍真实模型实测缺陷（evidence/deep-dive-20261014）。

    实测故障模式（glm-4v-flash，40 次调用 6 次复现）：
      1. code fence（原有处理保留）；
      2. 重复左花括号：```json\\n{\\n    {\\n "page_kind"...（深缩进输出时高发）；
      3. 截断输出（右括号缺失）。
    逐级尝试修复，全部失败抛 JSONDecodeError。
    """
    if text.startswith("```"):
        text = text.split("```", 2)[1].removeprefix("json").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        original_err = e  # PEP 3110: as 名字在块尾自动解绑，需转存
    stripped = text.strip()
    dedup_open = re.sub(r"^\{\s*(?=\{)", "", stripped) if stripped.startswith("{") else stripped
    dedup_both = re.sub(r"\}\s*\}$", "}", dedup_open) if dedup_open != stripped else stripped
    for cand in (dedup_open, dedup_both, _balance_close(stripped), _balance_close(dedup_open)):
        if cand == stripped:
            continue
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    raise original_err


def _balance_close(text: str) -> str:
    """为截断的 JSON 补齐缺失的右括号（只补不删，保守修复）。"""
    stack = []
    in_str = False
    esc = False
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack:
            stack.pop()
    if in_str:  # 字符串本体被截断：无法安全修复
        return text
    return text + "".join(reversed(stack))

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
        out = parse_model_json(text)
        out.setdefault("components", [])
        out.setdefault("requires_human_review", False)
        return out

    def describe_stable(self, image_path: str, k: int = 3) -> dict:
        """同一图采样 k 次，把"自报置信度"替换为"跨采样一致率"（经验置信度）。

        动机（evidence/deep-dive-20261014 Q6/Q7 实测）：glm-4v-flash 自报 confidence
        退化为常数 1.0（校准失效），且同图 5 次采样出现 3 种不同组件集合（非确定性），
        "present=true + confidence=1.0" 的幻觉组件会直通需求树。一致率 <1 的组件
        confidence 被压低，重新落回 intent_tree 的 0.85 置信路由（进 assumptions）。
        """
        samples = [self.describe(image_path) for _ in range(k)]
        names = sorted({c["name"] for d in samples for c in d["components"]})
        components = []
        for name in names:
            ballot = [any(c["name"] == name and c.get("present", True)
                          for c in d["components"]) for d in samples]  # 未出现=缺席票
            reported_vals = [float(c.get("confidence", 0))
                             for d in samples for c in d["components"] if c["name"] == name]
            rate = sum(ballot) / len(ballot)
            reported = sum(reported_vals) / len(reported_vals) if reported_vals else 0.0
            components.append({
                "name": name, "present": rate >= 0.5, "confidence": round(rate, 3),
                "self_reported_confidence": round(reported, 3), "n_samples": len(ballot)})
        components.sort(key=lambda c: (-c["confidence"], c["name"]))
        page_kinds = [d.get("page_kind") for d in samples]
        stable_kind = max(set(page_kinds), key=page_kinds.count)
        return {
            "page_kind": stable_kind,
            "page_kind_stable": len(set(page_kinds)) == 1,
            "requires_human_review": sum(1 for d in samples if d["requires_human_review"]) * 2 > k,
            "components": components, "n_samples": k,
        }
