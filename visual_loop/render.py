"""确定性渲染器：站点配置 → PPM 截图（问题④的预览截图基础设施）。

同一配置永远渲染同一像素——像素 diff 才有可判性。组件类型注册制：
渲染器不认识的组件不画（低代码平台新组件上线时，截图管线自动跟进）。
"""
from pathlib import Path

from .images import blank, draw_rect, write_ppm

CANVAS = (96, 64)  # W, H —— 小画布足够验证像素语义，测试也快

DEFAULT_COLORS = {
    "logo": (26, 58, 176),    # 品牌蓝
    "banner": (196, 62, 62),  # 促销红
    "video": (24, 24, 28),    # 播放器黑
}


def render_page(config: dict) -> list:
    img = blank(*CANVAS)
    for page in config.get("pages", []):
        for i, comp in enumerate(page.get("components", [])):
            props = comp.get("props", {})
            kind = comp.get("type")
            rgb = _parse_color(props.get("color"), DEFAULT_COLORS.get(kind, (120, 120, 120)))
            if kind == "banner":
                draw_rect(img, 0, 4, CANVAS[0], 12, rgb)
            elif kind in ("logo", "video"):
                draw_rect(img, props.get("x", 4), props.get("y", 8),
                          props.get("w", 16), props.get("h", 16), rgb)
            # 未知类型：跳过（渲染器容错）
    return img


def render_to_file(config: dict, path) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_ppm(path, render_page(config))
    return str(path)


def _parse_color(hexcolor, default):
    if not hexcolor:
        return default
    hexcolor = hexcolor.lstrip("#")
    if len(hexcolor) != 6:
        return default
    try:
        return tuple(int(hexcolor[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return default
