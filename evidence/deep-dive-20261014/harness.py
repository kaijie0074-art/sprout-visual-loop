#!/usr/bin/env python3
"""深潜实验 harness：串行真实 VLM 调用（节流：间隔 sleep 2；429 → sleep 60 重试 ≤3）。

用法：
  python3 harness.py run <images...>        # 对每张图调 VLM（复用 visual_loop.vlm.PROMPT）
  python3 harness.py rerun <image> <times>  # 同图重复调用（确定性测量）
结果追加写入 results.jsonl：时间戳/模型/图名/延迟/原始输出。key 只进环境变量，绝不落盘。
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))  # repo root
from visual_loop.vlm import PROMPT  # noqa: E402

BASE_URL = os.environ.get("VISUAL_LOOP_BASE_URL", "https://open.bigmodel.cn/api/coding/paas/v4")
MODEL = os.environ.get("VISUAL_LOOP_VLM_MODEL", "glm-4v-flash")
KEY = os.environ.get("VISUAL_LOOP_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
RESULTS = HERE / "results.jsonl"
def call_vlm(image: Path, model: str, prompt: str = PROMPT, temperature: float | None = None,
             max_tokens: int | None = None) -> dict:
    b64 = base64.b64encode(image.read_bytes()).decode("ascii")
    body = {"model": model, "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        {"type": "text", "text": prompt}]}]}
    if temperature is not None:
        body["temperature"] = temperature
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    req = urllib.request.Request(
        f"{BASE_URL.rstrip('/')}/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    t0 = time.time()
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                payload = json.loads(resp.read().decode())
            dt = time.time() - t0
            msg = payload["choices"][0]["message"]
            content = (msg.get("content") or "").strip()
            if not content and msg.get("reasoning_content"):
                content = msg["reasoning_content"].strip()
            usage = payload.get("usage", {})
            return {"latency_s": round(dt, 2), "content": content,
                    "usage": {k: usage.get(k) for k in ("prompt_tokens", "completion_tokens",
                                                        "total_tokens")}}
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                print(f"  429 -> sleep 60 (attempt {attempt+1}/3)", flush=True)
                time.sleep(60)
                continue
            raise
    raise RuntimeError("unreachable")


def parse_json_out(text: str) -> dict:
    if text.startswith("```"):
        text = text.split("```", 2)[1].removeprefix("json").strip()
    try:
        out = json.loads(text)
    except json.JSONDecodeError:
        i, j = text.find("{"), text.rfind("}")
        if i >= 0 and j > i:
            out = json.loads(text[i:j + 1])
        else:
            raise
    out.setdefault("components", [])
    out.setdefault("requires_human_review", False)
    return out


def record(image: Path, model: str, raw: dict, parsed: dict, extra: dict | None = None):
    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "image": image.name, "model": model,
           "latency_s": raw["latency_s"], "usage": raw["usage"],
           "raw_text": raw["content"], "parsed": parsed}
    if extra:
        row.update(extra)
    with open(RESULTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"  {image.name} [{model}] {raw['latency_s']}s "
          f"-> {len(parsed['components'])} comps, review={parsed['requires_human_review']}", flush=True)


def main():
    if not KEY:
        sys.exit("缺少 VISUAL_LOOP_API_KEY")
    cmd = sys.argv[1]
    model = os.environ.get("VISUAL_LOOP_VLM_MODEL", "glm-4v-flash")
    if cmd == "run":
        for name in sys.argv[2:]:
            img = HERE / "images" / name if not Path(name).exists() else Path(name)
            raw = call_vlm(img, model)
            try:
                parsed = parse_json_out(raw["content"])
            except json.JSONDecodeError as e:
                parsed = {"parse_error": str(e), "components": [], "requires_human_review": False}
            record(img, model, raw, parsed)
            time.sleep(2)
    elif cmd == "rerun":
        img = Path(sys.argv[2])
        times = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        for k in range(times):
            raw = call_vlm(img, model)
            try:
                parsed = parse_json_out(raw["content"])
            except json.JSONDecodeError as e:
                parsed = {"parse_error": str(e), "components": [], "requires_human_review": False}
            record(img, model, raw, parsed, extra={"repeat": k})
            time.sleep(2)
    else:
        sys.exit("用法: harness.py run <images...> | rerun <image> <times>")


if __name__ == "__main__":
    main()
