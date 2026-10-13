#!/usr/bin/env python3
"""评分：VLM 组件名 → 规范类目（同义词表），对照 ground_truth 算 recall/precision/置信度。"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent

SYNONYMS = {
    "search_bar": ["search", "searchbar", "search_bar", "search_box", "搜索"],
    "banner": ["banner", "ad", "ads", "advert", "advertisement", "promo", "promotion", "carousel"],
    "video_feed": ["video", "video_feed", "videofeed", "video_card", "player", "播放"],
    "tab_bar": ["tab_bar", "tabbar", "bottom_nav", "bottom_navigation", "navigation_bar",
                "nav_bar", "navbar", "menu_bar", "bottom_menu", "bottom_tab"],
    "logo": ["logo", "brand", "branding", "app_name"],
    "feed_cards": ["feed_card", "feed_cards", "card_feed", "card_grid", "grid_card",
                   "product_card", "cards_flow", "feed"],
    "card": ["card", "cards", "content_card_list"],
    "mall_entry": ["mall", "mall_entry", "shop", "store", "shop_entry", "entry_button"],
    "list_item": ["list", "list_item", "listitem", "list_view", "listrow", "list_row",
                  "text_list", "row", "item", "items"],
    "icon_button": ["icon", "icons", "icon_button", "icon_grid", "circle_icon", "category",
                    "category_icon", "avatar", "avatars", "icon_entry", "avatar_icon"],
    "fab": ["fab", "floating_button", "float_button", "floating_action_button"],
    "container": ["container", "card_container", "panel", "section", "section_header", "group"],
    "content_cards": ["content_card", "content_cards", "inner_card", "content_area"],
    "modal": ["modal", "dialog", "popup", "dialog_box", "modal_dialog"],
    "top_bar": ["top_bar", "topbar", "header", "app_bar", "action_bar"],
}


def canon(name: str) -> str | None:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower().strip()).strip("_")
    for cat, syns in SYNONYMS.items():  # 先精确匹配（避免 floating_button→button 类碰撞）
        if s in syns:
            return cat
    for cat, syns in SYNONYMS.items():  # 再词元匹配
        for syn in syns:
            if s == syn or re.search(rf"(^|_){re.escape(syn)}(_|$)", s):
                return cat
    return None


def score() -> dict:
    gt = json.loads((HERE / "images" / "ground_truth.json").read_text())
    rows = [json.loads(l) for l in (HERE / "results.jsonl").read_text().splitlines() if l.strip()]
    out = []
    for r in rows:
        g = gt.get(r["image"])
        if not g:
            continue
        if r["parsed"].get("parse_error"):
            out.append({"image": r["image"], "model": r["model"], "latency_s": r["latency_s"],
                        "style": g["style"], "layout": g["layout"], "parse_error": True,
                        "recall": None, "missed": [], "spurious": [], "n_detected": 0,
                        "n_gt": len(g["components"]), "mean_conf": None, "review": None,
                        "page_kind": r["parsed"].get("page_kind"), "raw_names": [],
                        "raw_confs": [], "instances": None})
            continue
        detected = []
        for c in r["parsed"]["components"]:
            if c.get("present", True):
                detected.append((c["name"], c.get("confidence", 0), canon(c["name"])))
        det_cats = [d[2] for d in detected if d[2]]
        gt_cats = set(g["components"])
        hit = {c for c in det_cats if c in gt_cats}
        # 实例级计数（count_* 实验）
        inst = None
        if "instances" in g:
            gt_cnt = defaultdict(int)
            for i in g["instances"]:
                gt_cnt[i] += 1
            det_cnt = defaultdict(int)
            for c in det_cats:
                det_cnt[c] += 1
            inst = {k: [gt_cnt[k], det_cnt[k]] for k in gt_cnt}
        out.append({
            "image": r["image"], "model": r["model"], "latency_s": r["latency_s"],
            "style": g["style"], "layout": g["layout"],
            "recall": round(len(hit) / len(gt_cats), 3) if gt_cats else None,
            "missed": sorted(gt_cats - hit),
            "spurious": sorted({c for c in det_cats if c not in gt_cats}),
            "n_detected": len(detected), "n_gt": len(gt_cats),
            "mean_conf": round(sum(d[1] for d in detected) / len(detected), 3) if detected else 0,
            "review": r["parsed"]["requires_human_review"],
            "page_kind": r["parsed"].get("page_kind"),
            "raw_names": [d[0] for d in detected],
            "raw_confs": [d[1] for d in detected],
            "instances": inst,
        })
    return out


if __name__ == "__main__":
    filter_prefix = sys.argv[1] if len(sys.argv) > 1 else ""
    for row in score():
        if filter_prefix and not row["image"].startswith(filter_prefix):
            continue
        print(json.dumps(row, ensure_ascii=False))
