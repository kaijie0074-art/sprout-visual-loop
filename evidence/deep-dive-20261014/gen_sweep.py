#!/usr/bin/env python3
"""低保真度扫描：同一 video_feed 布局，手抖幅度 σ ∈ {1.6, 4, 8} px 三档 sketch。
外加降采样轴（clean 480→240/120 宽）——低保真的两个正交维度。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from gen_pages import Canvas, LAYOUTS, layout_video_feed, write_png  # noqa: E402

GT = json.loads((HERE / "images" / "ground_truth.json").read_text())


def main():
    imgdir = HERE / "images"
    # 1) 手抖幅度扫描
    for sigma in (1.6, 4.0, 8.0):
        cv = Canvas("sketch", seed=1234)
        cv.wobble = sigma
        layout_video_feed(cv)
        name = f"sketch_w{int(sigma*10):03d}.png"
        write_png(imgdir / name, cv.img)
        GT[name] = {"layout": f"sketch_wobble_{sigma}", "style": "sketch",
                    "components": ["search_bar", "banner", "video_feed", "tab_bar"]}
    # 2) 降采样扫描（区域平均，模拟低分辨率截图）
    base = Canvas("clean", seed=7)
    layout_video_feed(base)
    for target_w in (240, 120):
        ratio = 480 / target_w
        small = [[_avg(base.img, int(r * ratio), int(c * ratio), ratio)
                  for c in range(target_w)]
                 for r in range(int(800 / ratio))]
        name = f"clean_dw{target_w}.png"
        write_png(imgdir / name, small)
        GT[name] = {"layout": f"downscale_{target_w}", "style": "clean",
                    "components": ["search_bar", "banner", "video_feed", "tab_bar"]}
    (imgdir / "ground_truth.json").write_text(json.dumps(GT, ensure_ascii=False, indent=1))
    print("sweep images written:", [p.name for p in sorted(imgdir.glob('sketch_w*')) + sorted(imgdir.glob('clean_dw*'))])


def _avg(img, r0, c0, ratio):
    """ratio×ratio 块的均值（无依赖双线性近似：取块平均）。"""
    R = max(1, int(ratio))
    rs, gs, bs, n = 0, 0, 0, 0
    for r in range(r0, min(len(img), r0 + R)):
        for c in range(c0, min(len(img[0]), c0 + R)):
            p = img[r][c]
            rs += p[0]; gs += p[1]; bs += p[2]; n += 1
    return (rs // n, gs // n, bs // n)


if __name__ == "__main__":
    main()
