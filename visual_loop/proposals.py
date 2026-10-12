"""提案式修改：把开放式审美问题降维成选择题（源文档 3.2 路线 1/2/4）。

- 模糊尺寸指令（『logo 大一点』）→ 3 个候选（+15% / +30% / 布局重排）；
- 模糊色彩指令（『高级点的蓝』）→ 6 色候选色卡，不直接拍色值；
- 每候选附预览截图（render → PPM），客户点选后才应用。
"""
import copy
from pathlib import Path

from .render import render_to_file

# 「高级的蓝」候选色卡：深海军蓝 → 浅雾蓝（低饱和、去荧光感）
BLUE_PALETTE = ["#0F2A5C", "#16407F", "#1B5AA6", "#2F6FB8", "#4A86C8", "#6FA3D6"]


def _find_component(config: dict, target: str) -> int:
    for i, comp in enumerate(config["pages"][0]["components"]):
        if comp.get("type") == target:
            return i
    raise ValueError(f"配置中找不到目标组件 {target}")


def _apply(config: dict, patch: list) -> dict:
    cfg = copy.deepcopy(config)
    for op in patch:
        node = cfg
        segs = [s for s in op["path"].split("/") if s]
        for s in segs[:-1]:
            node = node[int(s)] if isinstance(node, list) else node[s]
        last = segs[-1]
        if isinstance(node, list):
            node[int(last)] = op["value"]
        else:
            node[last] = op["value"]
    return cfg


def propose(config: dict, instruction: dict, out_dir) -> dict:
    """instruction = {kind: resize|color, target, direction?|hint?} → 候选集 + 预览。"""
    idx = _find_component(config, instruction["target"])
    base = f"/pages/0/components/{idx}/props"
    kind = instruction["kind"]

    if kind == "resize":
        props = config["pages"][0]["components"][idx]["props"]
        w, h, x, y = props.get("w", 16), props.get("h", 16), props.get("x", 4), props.get("y", 8)
        specs = [
            ("A", [{"op": "replace", "path": f"{base}/w", "value": round(w * 1.15)}],
             "+15%：稳妥放大，不挤压周边"),
            ("B", [{"op": "replace", "path": f"{base}/w", "value": round(w * 1.30)}],
             "+30%：明显放大"),
            ("C", [{"op": "replace", "path": f"{base}/w", "value": round(w * 1.20)},
                   {"op": "replace", "path": f"{base}/h", "value": round(h * 1.35)},
                   {"op": "replace", "path": f"{base}/x", "value": max(0, x - 4)},
                   {"op": "replace", "path": f"{base}/y", "value": max(0, y - 2)}],
             "重排方案：放大并上移视觉重心"),
        ]
    elif kind == "color":
        specs = [(f"C{i+1}", [{"op": "replace", "path": f"{base}/color", "value": hexv}],
                  f"色卡 {i+1}：{hexv}") for i, hexv in enumerate(BLUE_PALETTE)]
    else:
        raise ValueError(f"不支持的指令类型 {kind}")

    out = Path(out_dir)
    candidates = []
    for cid, patch, rationale in specs:
        preview = render_to_file(_apply(config, patch), out / f"proposal_{cid}.ppm")
        candidates.append({"id": cid, "patch": patch, "preview": preview, "rationale": rationale})

    return {
        "instruction": instruction,
        "candidates": candidates,
        "note": "提案式交互：客户点选后才应用 patch；同一处修改超过 2 轮未确认转人工",
    }
