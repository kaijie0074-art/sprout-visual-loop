"""输入侧（问题②）回归：反幻觉 / 分层置信路由 / 共指 / 归一 / 模板对齐。

同一套测试在 baseline（直通管线）上失败 = 复现材料（docs/02）。
"""
import unittest

from visual_loop.api import (align_reference, build_intent_tree,
                             confirm_assumption, dark_hallucination_count)
from visual_loop.normalize import normalize

T_LOGO = [{"turn": 1, "text": "个只 logo 摆左边咯 睇下 做个好似抖音咁样嘅 稳阵"}]
T_BANNER = [{"turn": 1, "text": "首页要一个大 banner"},
            {"turn": 2, "text": "个只摆呢度 好睇啲"}]           # 那个放这里（唯一先行= banner）
T_DANGLING = [{"turn": 1, "text": "个只摆呢度 好睇啲"}]         # 那个放这里（无先行实体）
T_AMBIGUOUS = [{"turn": 1, "text": "加个 banner 和视频模块"},
               {"turn": 2, "text": "个只摆呢度 好睇啲"}]         # 同轮双实体：指代歧义

def _names(report):
    return [c["name"] for p in report["tree"]["pages"] for c in p["components"]]


class TestNormalize(unittest.TestCase):
    def test_cantonese_normalized(self):
        self.assertIn("看一下", normalize("睇下"))
        self.assertIn("放这里", normalize("摆呢度"))
        self.assertIn("放左边", normalize("个只 logo 摆左边咯 睇下"))


class TestAntiHallucination(unittest.TestCase):
    def test_hallucinated_component_captured(self):
        """客户没提登录页：VLM 自信补全 → 必须进 assumptions，绝不进树。"""
        report = build_intent_tree({"images": [{"key": "shot", "scenario": "hallucinated"}]})
        self.assertIn("login_screen", [a["guess"] for a in report["assumptions"]],
                      "幻觉项必须被假设清单捕获")
        self.assertNotIn("login_screen", _names(report), "幻觉项不得混入需求树")

    def test_dark_hallucination_zero(self):
        """树内全部节点有明说证据（source 非空）——暗幻觉恒为 0。"""
        inputs = {"transcript": T_BANNER + [{"turn": 3, "text": "加个社区模块"}],
                  "images": [{"key": "s1", "scenario": "screenshot_clear"},
                             {"key": "s2", "scenario": "hallucinated"},
                             {"key": "s3", "scenario": "screenshot_uncertain"}]}
        report = build_intent_tree(inputs)
        self.assertEqual(dark_hallucination_count(report), 0)

    def test_low_confidence_to_assumptions(self):
        """组件类型判定不稳（0.55）：进 assumptions 强制人工确认。"""
        report = build_intent_tree({"images": [{"key": "s", "scenario": "screenshot_uncertain"}]})
        self.assertIn("feed_cards", [a["guess"] for a in report["assumptions"]])
        self.assertNotIn("feed_cards", _names(report))

    def test_confirm_moves_node_into_tree(self):
        report = build_intent_tree({"images": [{"key": "s", "scenario": "hallucinated"}]})
        asm_id = report["assumptions"][0]["id"]
        updated = confirm_assumption(report, asm_id, accept=True)
        self.assertEqual(updated["assumptions"], [])
        self.assertIn("login_screen", [c["name"] for c in updated["tree"]["pages"][0]["components"]])
        self.assertTrue(all(c["source"].get("modality") == "human_confirmed"
                            for c in updated["tree"]["pages"][0]["components"]
                            if c["name"] == "login_screen"))
        # reject 路径：不进树
        rejected = confirm_assumption(report, asm_id, accept=False)
        self.assertNotIn("login_screen", _names(rejected))


class TestConfidenceRouting(unittest.TestCase):
    def test_handdrawn_routes_to_human_review(self):
        report = build_intent_tree({"images": [{"key": "draft", "scenario": "handdrawn"}]})
        self.assertTrue(report["requires_human_review"], "手绘稿必须强制人工确认页")


class TestCoreference(unittest.TestCase):
    def test_reference_resolved_to_last_entity(self):
        """『那个放这里』→ 指代上一轮的 banner，修改意图绑定正确目标。"""
        report = build_intent_tree({"transcript": T_BANNER})
        mods = report["tree"]["pages"][0]["modifications"]
        self.assertEqual(len(mods), 1)
        self.assertEqual(mods[0]["target"], "banner")
    def test_ambiguous_reference_goes_to_assumptions(self):
        """同轮提及两个实体时『那个』无法唯一闭合 → 进 assumptions 问人（难点 3 的显式处理）。"""
        report = build_intent_tree({"transcript": T_AMBIGUOUS})
        self.assertEqual(report["tree"]["pages"][0]["modifications"], [])
        self.assertTrue(any("指代" in a["reason"] for a in report["assumptions"]))


    def test_cantonese_logo_position_understood(self):
        report = build_intent_tree({"transcript": T_LOGO})
        mods = report["tree"]["pages"][0]["modifications"]
        self.assertEqual(mods[0]["target"], "logo")
        self.assertEqual(mods[0]["value"], "left")
        self.assertTrue(report["reference_hints"], "『像抖音那样』应标记为参考提示")

    def test_unresolved_reference_to_assumptions(self):
        """无先行实体的『那个』→ 指代闭合失败进 assumptions。"""
        report = build_intent_tree({"transcript": T_DANGLING})
        self.assertTrue(report["assumptions"], "闭合失败必须显式记录")
        self.assertEqual(len(report["unresolved_refs"]), 1)


class TestReferenceAlignment(unittest.TestCase):
    def test_align_to_template_with_diffs(self):
        out = align_reference("做个像抖音那样的")
        self.assertEqual(out["template"]["id"], "tpl_short_video")
        self.assertGreater(out["similarity"], 0.5)
        self.assertFalse(out["copy_all"], "禁止全量仿制")
        self.assertGreaterEqual(len(out["diffs"]), 2, "必须给出差异清单供逐项确认")


if __name__ == "__main__":
    unittest.main()
