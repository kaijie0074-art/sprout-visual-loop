"""像素 diff：借 pixelmatch 思想的极简实现——逐像素差 + 阈值 + 变化区域 bbox。

它只能回答"变在哪、变了多大"，回答不了"改对了没有"（那是客户的主观
验收）——所以输出侧的正确形态是：像素 diff 定位变化 + 属性断言证明
"声明的改动确实发生" + 提案点选闭环（见 docs/04）。
"""
from .render import render_page


def diff(img_a: list, img_b: list, threshold: int = 30) -> dict:
    # R3-2（评审修复）：尺寸不等显式报错——裸 IndexError 不可诊断
    if (len(img_a), len(img_a[0])) != (len(img_b), len(img_b[0])):
        raise ValueError(f"两图尺寸不等：{len(img_a[0])}x{len(img_a)} vs "
                         f"{len(img_b[0])}x{len(img_b)}（diff 前必须同源渲染）")
    h, w = len(img_a), len(img_a[0])
    changed, max_delta = [], 0
    for y in range(h):
        for x in range(w):
            pa, pb = img_a[y][x], img_b[y][x]
            d = sum(abs(a - b) for a, b in zip(pa, pb))
            max_delta = max(max_delta, d)
            if d > threshold:
                changed.append((x, y))
    box = None
    if changed:
        xs = [p[0] for p in changed]
        ys = [p[1] for p in changed]
        box = [min(xs), min(ys), max(xs), max(ys)]
    return {"changed_ratio": round(len(changed) / (w * h), 4),
            "changed_pixels": len(changed), "box": box, "max_delta": max_delta}


def diff_configs(config_a: dict, config_b: dict, threshold: int = 30) -> dict:
    """渲染两个配置并 diff（同一渲染器保证可判性）。"""
    return diff(render_page(config_a), render_page(config_b), threshold)
