"""研究驱动的回归：真实模型实测缺陷 → 工程修复（evidence/deep-dive-20261014）。

1. parse_model_json：glm-4v-flash 实测 6/40 次输出畸形 JSON（双开括号 `{ {`、截断），
   原实现 json.loads 直接崩——这里用捕获的原始输出回放验证修复。
2. describe_stable：自报 confidence 退化为常数 1.0 + 同图多次采样结果漂移（非确定性），
   一致率作为经验置信度，让 0.85 阈值路由重新生效。
"""
import unittest

from visual_loop.vlm import VlmClient, parse_model_json

# 捕获自真实 glm-4v-flash 响应（evidence/deep-dive-20261014/json_failure_fixtures.json）
REAL_DOUBLE_BRACE = (
    "```json\n{\n    {\n        \"page_kind\": \"unknown\",\n"
    "        \"requires_human_review\": false,\n        \"components\": [\n"
    "            {\n                \"name\": \"banner\",\n"
    "                \"present\": true,\n                \"confidence\": 1\n            },\n"
    "            {\n                \"name\": \"login_screen\",\n"
    "                \"present\": true,\n                \"confidence\": 1\n            }\n"
    "        ]\n    }\n}"
)
REAL_TRUNCATED = (
    "```json\n{\"page_kind\": \"unknown\", \"requires_human_review\": false, "
    "\"components\": [{\"name\": \"tab_bar\", \"present\": true, \"confidence\": 1"
)
REAL_CLEAN_FENCED = (
    "```json\n{\"page_kind\": \"home\", \"requires_human_review\": false, "
    "\"components\": [{\"name\": \"banner\", \"present\": true, \"confidence\": 0.9}]}\n```"
)


class TestParseModelJson(unittest.TestCase):
    def test_clean_fenced_untouched(self):
        out = parse_model_json(REAL_CLEAN_FENCED)
        self.assertEqual(out["page_kind"], "home")
        self.assertEqual(out["components"][0]["name"], "banner")

    def test_double_open_brace_repaired(self):
        """实测缺陷：`{ {` 双开括号（6/40 次复现，深嵌套页面高发）。"""
        out = parse_model_json(REAL_DOUBLE_BRACE)
        self.assertEqual(out["page_kind"], "unknown")
        self.assertEqual([c["name"] for c in out["components"]], ["banner", "login_screen"])

    def test_truncated_json_balanced(self):
        """实测缺陷：输出截断，右括号缺失。"""
        out = parse_model_json(REAL_TRUNCATED)
        self.assertEqual(out["components"][0]["name"], "tab_bar")
        self.assertTrue(out["components"][0]["present"])

    def test_unrepairable_raises_original_error(self):
        with self.assertRaises(ValueError):
            parse_model_json("完全不是 JSON 的输出")


class _ScriptedVlm(VlmClient):
    """无网络回放：按脚本顺序返回不同 describe 结果（模拟同图采样漂移）。"""

    def __init__(self, script):
        super().__init__(api_key="test-key")
        self.script = list(script)
        self.calls = []

    def describe(self, image_path, scenario=""):
        self.calls.append(image_path)
        return self.script.pop(0)


FLAKY_SCRIPT = [
    {"page_kind": "video_feed_home", "requires_human_review": False, "components": [
        {"name": "video_feed", "present": True, "confidence": 1.0},
        {"name": "login_screen", "present": True, "confidence": 1.0},  # 幻觉：只出现 1/3
    ]},
    {"page_kind": "video_feed_home", "requires_human_review": False, "components": [
        {"name": "video_feed", "present": True, "confidence": 1.0},
    ]},
    {"page_kind": "home", "requires_human_review": False, "components": [
        {"name": "video_feed", "present": True, "confidence": 1.0},
    ]},
]


class TestDescribeStable(unittest.TestCase):
    def test_empirical_confidence_replaces_self_report(self):
        vlm = _ScriptedVlm(FLAKY_SCRIPT)
        out = vlm.describe_stable("x.png", k=3)
        self.assertEqual(out["n_samples"], 3)
        by_name = {c["name"]: c for c in out["components"]}
        # video_feed 3/3 一致 → 经验置信 1.0
        self.assertEqual(by_name["video_feed"]["confidence"], 1.0)
        self.assertEqual(by_name["video_feed"]["self_reported_confidence"], 1.0)
        # login_screen 1/3 出现 → 一致率 0.333，被压低（不再直通需求树）
        self.assertAlmostEqual(by_name["login_screen"]["confidence"], 0.333, places=3)
        self.assertEqual(by_name["login_screen"]["self_reported_confidence"], 1.0)  # 自报仍是满分=反证校准失效

    def test_unstable_page_kind_flagged(self):
        vlm = _ScriptedVlm(FLAKY_SCRIPT)
        out = vlm.describe_stable("x.png", k=3)
        self.assertFalse(out["page_kind_stable"])
        self.assertEqual(out["page_kind"], "video_feed_home")  # 众数

    def test_intent_tree_routes_flaky_component_to_assumptions(self):
        """端到端：stable_k=3 时，1/3 出现的幻觉组件进 assumptions 而非需求树。"""
        from visual_loop.intent_tree import build_intent_tree
        vlm = _ScriptedVlm(FLAKY_SCRIPT)
        report = build_intent_tree(
            {"transcript": [], "images": [{"key": "img1", "path": "x.png"}]},
            vlm=vlm, stable_k=3)
        tree_names = {c["name"] for c in report["tree"]["pages"][0]["components"]}
        asm_guesses = {a["guess"] for a in report["assumptions"]}
        self.assertEqual(tree_names, {"video_feed"})
        self.assertIn("login_screen", asm_guesses)
        self.assertEqual(len(vlm.calls), 3)


if __name__ == "__main__":
    unittest.main()
