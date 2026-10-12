"""确定性 Mock VLM：按场景脚本化输出对 截图/手绘稿 的结构描述。

关键设计：每个组件带 `present`（图中是否真有）与 `confidence`。
  - present=False 的项无论置信度多高，都是幻觉补全——必须进 assumptions；
  - present=True 但 confidence 低（手绘稿/组件类型拿不准）→ 进 assumptions
    强制人工确认（分层置信路由，源文档 3.1 路线 4）。
"""
SCENARIOS = {
    # 清晰竞品截图：布局拓扑 + 组件类型都拿得准
    "screenshot_clear": {
        "page_kind": "video_feed_home",
        "requires_human_review": False,
        "components": [
            {"name": "video_feed", "present": True, "confidence": 0.92},
            {"name": "banner", "present": True, "confidence": 0.9},
        ],
    },
    # 组件类型拿不准：卡片流还是列表？（源文档 3.1 难点 1）
    "screenshot_uncertain": {
        "page_kind": "home",
        "requires_human_review": False,
        "components": [
            {"name": "feed_cards", "present": True, "confidence": 0.55},
        ],
    },
    # 手绘稿：识别率骤降（难点 2）→ 强制人工确认
    "handdrawn": {
        "page_kind": "unknown",
        "requires_human_review": True,
        "components": [
            {"name": "video_feed", "present": True, "confidence": 0.31},
            {"name": "tab_bar", "present": True, "confidence": 0.4},
        ],
    },
    # 幻觉补全：客户没提登录页，模型按"常见 APP 该有的样子"加上（难点 5，最危险）
    "hallucinated": {
        "page_kind": "video_feed_home",
        "requires_human_review": False,
        "components": [
            {"name": "video_feed", "present": True, "confidence": 0.9},
            {"name": "login_screen", "present": False, "confidence": 0.95},  # 自信的私货
        ],
    },
}


def describe(image_key: str, scenario: str = "screenshot_clear") -> dict:
    out = {"image_key": image_key, "scenario": scenario}
    out.update(SCENARIOS[scenario])
    return out


def supported_scenarios() -> list:
    return sorted(SCENARIOS)
