"""VLM 输出场景语料（测试夹具，仅 tests/ 内使用；产品代码不含脚本化模型）。

经 tests.providers.ScriptedVlm 注入 build_intent_tree，回归分层置信路由与
反幻觉行为（清晰截图 / 组件类型拿不准 / 手绘稿 / 幻觉补全，对应源文档 3.1 难点）。
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
