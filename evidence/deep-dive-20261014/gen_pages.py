#!/usr/bin/env python3
"""研究用页面位图生成器（纯 stdlib）。

确定性：同一 layout+style+seed 永远生成同一 PNG（科学复现的前提）。
两种渲染风格，同一几何布局：
  - clean : 彩色填充+浅边框、锐利边缘（模拟真实 UI 截图）
  - sketch: 灰色抖动描边、无填充色（模拟手绘低保真草图）
"""
from __future__ import annotations

import json
import math
import random
import struct
import sys
import zlib
from pathlib import Path

W, H = 480, 800


# ---------------- PNG writer (纯 stdlib) ----------------
def write_png(path: Path, img: list[list[tuple[int, int, int]]]):
    h, w = len(img), len(img[0])
    raw = b"".join(b"\x00" + bytes(v for px in row for v in px) for row in img)

    def chunk(t: bytes, data: bytes) -> bytes:
        c = t + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6))
           + chunk(b"IEND", b""))
    path.write_bytes(png)


class Canvas:
    def __init__(self, style: str, seed: int = 7):
        self.style = style
        self.rng = random.Random(seed)
        self.wobble = 1.6  # 手抖幅度（px）；fidelity sweep 可调
        bg = (255, 255, 255) if style == "sketch" else (246, 247, 250)
        self.img = [[bg] * W for _ in range(H)]

    # --- primitives ---
    def px(self, x, y, rgb):
        if 0 <= x < W and 0 <= y < H:
            self.img[int(y)][int(x)] = rgb

    def _hard_line(self, x0, y0, x1, y1, rgb, width=2):
        n = max(1, int(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5))
        for i in range(n + 1):
            t = i / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            for ox in range(-(width // 2), width // 2 + 1):
                for oy in range(-(width // 2), width // 2 + 1):
                    self.px(x + ox, y + oy, rgb)

    def _wobble_line(self, x0, y0, x1, y1, rgb, width=2):
        """sketch 风格：折线 + 法向抖动（手抖感）。"""
        n = max(2, int(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 // 14))
        dx, dy = x1 - x0, y1 - y0
        L = (dx * dx + dy * dy) ** 0.5 or 1
        nx, ny = -dy / L, dx / L
        pts = []
        for i in range(n + 1):
            t = i / n
            j = self.rng.uniform(-self.wobble, self.wobble) * (0.35 + 0.65 * 4 * t * (1 - t))
            pts.append((x0 + dx * t + nx * j, y0 + dy * t + ny * j))
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            self._hard_line(ax, ay, bx, by, rgb, width)

    def rect(self, x, y, w, h, fill=None, stroke=(60, 62, 70)):
        """clean: 填充+浅边框；sketch: 抖动描边框。"""
        if self.style == "sketch":
            for (ax, ay, bx, by) in [(x, y, x + w, y), (x + w, y, x + w, y + h),
                                     (x + w, y + h, x, y + h), (x, y + h, x, y)]:
                self._wobble_line(ax, ay, bx, by, stroke, 2)
            return
        if fill:
            for r in range(max(0, y), min(H, y + h)):
                for c in range(max(0, x), min(W, x + w)):
                    self.img[r][c] = fill
        edge = (198, 200, 206)  # clean 无填充也要可见边框
        for c in range(max(0, x), min(W, x + w)):
            self.img[max(0, y)][c] = edge
            self.img[min(H - 1, y + h - 1)][c] = edge
        for r in range(max(0, y), min(H, y + h)):
            self.img[r][max(0, x)] = edge
            self.img[r][min(W - 1, x + w - 1)] = edge

    def text_block(self, x, y, w, nlines=2, lh=10, dark=(40, 42, 50)):
        """假文字：clean=4px 灰条；sketch=抖动短划。"""
        for i in range(nlines):
            ly = y + i * lh
            lw = w if i == 0 or nlines < 3 else int(w * 0.65)
            if self.style == "sketch":
                segs = 4
                for s in range(segs):
                    sx = x + s * (lw / segs) + self.rng.uniform(1, 5)
                    ex = x + (s + 1) * (lw / segs) - self.rng.uniform(1, 6)
                    self._wobble_line(sx, ly, ex, ly + self.rng.uniform(-1.5, 1.5), dark, 2)
            else:
                for xx in range(int(x), int(x + max(8, lw))):
                    for yy in range(int(ly), int(ly) + 4):
                        self.px(xx, yy, dark)

    def circle(self, cx, cy, r, fill=None, stroke=(60, 62, 70)):
        pts = []
        for a in range(0, 366, 6):
            j = self.rng.uniform(-1.2, 1.2) if self.style == "sketch" else 0
            rr = r + j
            pts.append((cx + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a))))
        if fill and self.style != "sketch":
            for a in range(0, 360, 2):
                for k in range(int(r)):
                    self.px(cx + k * math.cos(math.radians(a)), cy + k * math.sin(math.radians(a)), fill)
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            self._hard_line(ax, ay, bx, by, fill or stroke, 2)


# ---------------- layouts ----------------
def layout_video_feed(cv: Canvas):
    """GT: search_bar, banner, video_feed(卡片), tab_bar"""
    cv.rect(16, 24, 448, 44, fill=(240, 241, 245) if cv.style == "clean" else None)
    cv.circle(38, 46, 12, fill=(160, 164, 175))
    cv.text_block(60, 40, 180, 1)
    cv.rect(16, 84, 448, 110, fill=(196, 62, 62) if cv.style == "clean" else None)
    if cv.style == "sketch":
        cv.text_block(140, 128, 200, 1)
    for i in range(4):  # video cards
        y = 214 + i * 132
        cv.rect(16, y, 448, 116, fill=(255, 255, 255))
        cv.rect(28, y + 10, 160, 96, fill=(24, 24, 28) if cv.style == "clean" else None)
        if cv.style == "sketch":
            cv.circle(108, y + 58, 16)  # 播放按钮轮廓
        cv.text_block(204, y + 22, 220, 2)
        cv.text_block(204, y + 58, 150, 1)
    cv.rect(0, 740, 480, 60, fill=(250, 250, 252))
    for i in range(4):
        cx = 60 + i * 120
        cv.rect(cx - 14, 752, 28, 28, fill=(26, 58, 176) if (cv.style == "clean" and i == 0) else None)
        cv.text_block(cx - 16, 786, 32, 1)


def layout_content_home(cv: Canvas):
    """GT: logo, banner, feed_cards, mall_entry, tab_bar"""
    cv.rect(20, 28, 120, 40, fill=(26, 58, 176) if cv.style == "clean" else None)
    cv.text_block(36, 42, 88, 1)
    cv.rect(16, 88, 448, 96, fill=(230, 120, 40) if cv.style == "clean" else None)
    cv.text_block(150, 128, 180, 1)
    for i in range(2):  # two-column feed cards
        x = 16 + (i % 2) * 232
        y = 204 + (i // 2) * 232
        cv.rect(x, y, 216, 216, fill=(255, 255, 255))
        cv.rect(x + 10, y + 10, 196, 130, fill=(120, 130, 150) if cv.style == "clean" else None)
        cv.text_block(x + 12, y + 152, 190, 2)
        cv.text_block(x + 12, y + 186, 90, 1)
    cv.rect(16, 672, 448, 48, fill=(60, 160, 90) if cv.style == "clean" else None)
    cv.text_block(180, 690, 120, 1)
    cv.rect(0, 740, 480, 60, fill=(250, 250, 252))
    for i in range(4):
        cx = 60 + i * 120
        cv.rect(cx - 14, 752, 28, 28)
        cv.text_block(cx - 16, 786, 32, 1)


def layout_morph(cv: Canvas, t: float):
    """卡片流(t=0) → 竖直列表(t=1) 连续谱。GT: t<0.5→feed_cards, t>=0.5→list。
    插值维度：卡片宽 300→448；图区从"顶部大图"滑向"左侧缩略"；文字位置跟随。"""
    for i in range(4):
        w = int(300 + 148 * t)
        x = (480 - w) // 2
        y = 44 + i * 172
        h = 156
        cv.rect(x, y, w, h, fill=(255, 255, 255) if cv.style == "clean" else None)
        iw_full, ih_top = w - 20, int(h * 0.55)              # card：顶部大图
        iw_thumb, ih_thumb = int(w * 0.38), h - 20           # list：左侧缩略图
        iw = int(iw_full + (iw_thumb - iw_full) * t)
        ih = int(ih_top + (ih_thumb - ih_top) * t)
        cv.rect(x + 10, y + 10, iw, ih, fill=(120, 130, 150) if cv.style == "clean" else None)
        tx_b, ty_b = x + 14, y + ih_top + 12                 # card：文在图下
        tx_r, ty_r = x + iw_thumb + 24, y + 24               # list：文在图右
        tx = int(tx_b + (tx_r - tx_b) * t)
        ty = int(ty_b + (ty_r - ty_b) * t)
        cv.text_block(tx, ty, max(40, x + w - 24 - tx), 2)
        cv.text_block(tx, ty + 34, max(30, int((x + w - 24 - tx) * 0.6)), 1)
    cv.rect(0, 740, 480, 60, fill=(250, 250, 252))
    for i in range(4):
        cv.rect(60 + i * 120 - 14, 752, 28, 28)


def layout_n_components(cv: Canvas, n: int) -> list[str]:
    """恰好 n 个组件实例。n 大时自动换紧凑尺寸/多列网格（画布容量内保完整）。"""
    compact = n > 12
    grid = n > 24
    comps = ["search_bar"]
    cv.rect(16, 20, 448, 40, fill=(240, 241, 245) if cv.style == "clean" else None)
    comps.append("banner")
    cv.rect(16, 72, 448, 80, fill=(196, 62, 62) if cv.style == "clean" else None)
    y = 168
    i = 0
    while len(comps) < n - 2:  # 留 tab_bar + fab
        if grid:  # 4 列迷你卡 / 6 列图标 交替（n>24 高密度）
            if i % 2 == 0 and y + 68 < 700:
                for c in range(4):
                    if len(comps) >= n - 2:
                        break
                    cv.rect(16 + c * 116, y, 104, 62, fill=(255, 255, 255))
                    cv.rect(24 + c * 116, y + 6, 88, 30, fill=(120, 130, 150) if cv.style == "clean" else None)
                    cv.text_block(24 + c * 116, y + 42, 80, 1)
                    comps.append("card")
                y += 68
            elif y + 54 < 700:
                for c in range(6):
                    if len(comps) >= n - 2:
                        break
                    cv.circle(52 + c * 78, y + 16, 13, fill=(26, 58, 176) if cv.style == "clean" else None)
                    cv.text_block(36 + c * 78, y + 34, 32, 1)
                    comps.append("icon_button")
                y += 54
            else:
                break
        else:
            r = i % 3
            ih, ch, gh = (40, 64, 60) if compact else (64, 104, 80)
            if r == 0 and y + ih < 700:
                cv.rect(16, y, 448, ih - 4, fill=(255, 255, 255))
                cv.rect(24, y + 4, 32, 32, fill=(120, 130, 150) if cv.style == "clean" else None)
                cv.text_block(68, y + 8, 200, 2 if not compact else 1, lh=12)
                comps.append("list_item")
                y += ih
            elif r == 1 and y + ch < 700:
                for c in range(2):
                    if len(comps) >= n - 2:
                        break
                    cv.rect(16 + c * 232, y, 216, ch - 6, fill=(255, 255, 255))
                    cv.text_block(28 + c * 232, y + (ch // 3), 180, 2)
                    comps.append("card")
                y += ch
            elif y + gh < 700:
                for c in range(4):
                    if len(comps) >= n - 2:
                        break
                    cx = 76 + c * 112
                    cv.circle(cx, y + 18, 16, fill=(26, 58, 176) if cv.style == "clean" else None)
                    cv.text_block(cx - 20, y + 38, 40, 1)
                    comps.append("icon_button")
                y += gh
            else:
                break
        i += 1
    comps.append("tab_bar")
    cv.rect(0, 740, 480, 60, fill=(250, 250, 252))
    for c in range(4):
        cv.rect(60 + c * 120 - 14, 752, 28, 28)
    comps.append("fab")
    cv.circle(412, 700, 28, fill=(26, 58, 176) if cv.style == "clean" else None)
    return comps


def layout_nested(cv: Canvas, depth: int, overlay: str):
    """嵌套 depth 层容器 + 可选悬浮 overlay（modal/fab/none）。"""
    cv.rect(16, 24, 448, 44, fill=(240, 241, 245) if cv.style == "clean" else None)
    x, y, w, h = 16, 90, 448, 560
    cv.rect(x, y, w, h, fill=(243, 244, 246) if cv.style == "clean" else None)  # L1 容器
    cv.text_block(28, y + 10, 120, 1)
    for d in range(1, depth):
        x, y, w, h = x + 24, y + 40, w - 48, h - 60
        cv.rect(x, y, w, h, fill=(255, 255, 255))
        cv.text_block(x + 12, y + 8, 100, 1)
    for k in range(3):  # 最内层 3 张内容卡
        cy = y + 36 + k * ((h - 60) // 3)
        cv.rect(x + 12, cy, w - 24, (h - 60) // 3 - 12, fill=(236, 238, 241) if cv.style == "clean" else None)
        cv.text_block(x + 24, cy + 14, w - 60, 2)
    cv.rect(0, 740, 480, 60, fill=(250, 250, 252))
    for c in range(4):
        cv.rect(60 + c * 120 - 14, 752, 28, 28)
    if overlay == "fab":
        cv.circle(412, 700, 30, fill=(26, 58, 176) if cv.style == "clean" else None)
    elif overlay == "modal":
        cv.rect(60, 260, 360, 240, fill=(255, 255, 255))
        cv.text_block(90, 290, 300, 2)
        cv.rect(90, 420, 130, 44, fill=(26, 58, 176) if cv.style == "clean" else None)
        cv.text_block(120, 438, 70, 1)


LAYOUTS = {
    "video_feed": (layout_video_feed, ["search_bar", "banner", "video_feed", "tab_bar"]),
    "content_home": (layout_content_home, ["logo", "banner", "feed_cards", "mall_entry", "tab_bar"]),
}


def main(outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    gt = {}
    for name, (fn, components) in LAYOUTS.items():
        for style in ("clean", "sketch"):
            cv = Canvas(style, seed=abs(hash((name, style))) % 10000)
            fn(cv)
            p = outdir / f"{name}_{style}.png"
            write_png(p, cv.img)
            gt[p.name] = {"layout": name, "style": style, "components": components}
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        cv = Canvas("clean", seed=int(t * 100))
        layout_morph(cv, t)
        p = outdir / f"morph_{int(t*100):03d}.png"
        write_png(p, cv.img)
        gt[p.name] = {"layout": f"morph_{t}", "style": "clean",
                      "components": ["feed_cards"] if t < 0.5 else ["list"]}
    for n in (5, 10, 20, 40):
        cv = Canvas("clean", seed=n)
        comps = layout_n_components(cv, n)
        p = outdir / f"count_{n:02d}.png"
        write_png(p, cv.img)
        gt[p.name] = {"layout": f"count_{n}", "style": "clean",
                      "components": sorted(set(comps)), "instances": comps, "n_instances": len(comps)}
    for depth in (1, 2, 3):
        for overlay in ("none", "fab", "modal"):
            cv = Canvas("clean", seed=depth * 10 + len(overlay))
            layout_nested(cv, depth, overlay)
            p = outdir / f"nested_d{depth}_{overlay}.png"
            write_png(p, cv.img)
            gt[p.name] = {"layout": f"nested_d{depth}_{overlay}", "style": "clean",
                          "components": ["search_bar", "container", "content_cards", "tab_bar"]
                          + (["fab"] if overlay == "fab" else [])
                          + (["modal"] if overlay == "modal" else [])}
    (outdir / "ground_truth.json").write_text(json.dumps(gt, ensure_ascii=False, indent=1))
    print(f"generated {len(gt)} images + ground_truth.json in {outdir}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "images"))
