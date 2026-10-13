#!/usr/bin/env python3
"""live 验证研究修复：describe_stable 在真实 API 上的经验置信度。
用法：python3 validate_fixes.py <image.png> [k]（需 VISUAL_LOOP_API_KEY 等环境变量）"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from visual_loop.vlm import VlmClient  # noqa: E402

OUT = Path(__file__).parent / "stable_results.jsonl"


def main():
    img = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    client = VlmClient()
    t0 = time.time()
    out = client.describe_stable(img, k=k)
    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "image": Path(img).name,
           "model": os.environ.get("VISUAL_LOOP_VLM_MODEL", "glm-4v-flash"),
           "k": k, "wall_s": round(time.time() - t0, 1), **out}
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(row, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
