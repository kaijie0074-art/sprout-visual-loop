"""输出侧（问题④）回归：提案式修改 / 属性断言 / 像素 diff / 往返升级。"""
import tempfile
import unittest
from pathlib import Path

from visual_loop.api import diff_configs, propose, record_round, verify_change

SITE = {
    "siteName": "演示站",
    "pages": [{
        "pageId": "home",
        "components": [
            {"type": "logo", "props": {"x": 40, "y": 8, "w": 16, "h": 16}},
            {"type": "banner", "props": {}},
        ],
    }],
}


def _patched(w):
    import copy
    cfg = copy.deepcopy(SITE)
    cfg["pages"][0]["components"][0]["props"]["w"] = w
    return cfg


class TestProposals(unittest.TestCase):
    def test_resize_proposes_three_candidates_with_previews(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = propose(SITE, {"kind": "resize", "target": "logo", "direction": "bigger"}, tmp)
            self.assertGreaterEqual(len(out["candidates"]), 3, "模糊指令必须给多候选")
            widths = set()
            for c in out["candidates"]:
                self.assertTrue(Path(c["preview"]).exists(), "每候选必须附预览截图")
                for op in c["patch"]:
                    if op["path"].endswith("/w"):
                        widths.add(op["value"])
            self.assertGreaterEqual(len(widths), 2, "候选间方案必须有差异")

    def test_color_proposes_palette_not_single(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = propose(SITE, {"kind": "color", "target": "banner", "hint": "高级的蓝"}, tmp)
            cands = out["candidates"]
            self.assertEqual(len(cands), 6, "模糊色彩 → 6 色候选色卡")
            for c in cands:
                val = c["patch"][0]["value"]
                self.assertTrue(val.startswith("#") and len(val) == 7, f"色卡必须是 #RRGGBB：{val}")


class TestAssertions(unittest.TestCase):
    def test_declared_change_verified(self):
        declared = [{"path": "/pages/0/components/0/props/w",
                     "expect_from": 16, "expect_to": 21}]
        report = verify_change(declared, SITE, _patched(21))
        self.assertTrue(report["all_passed"])

    def test_noop_change_caught(self):
        """『Agent 说改了但没改』——属性断言必须抓住（可 100% 自动化的部分）。"""
        declared = [{"path": "/pages/0/components/0/props/w",
                     "expect_from": 16, "expect_to": 21}]
        report = verify_change(declared, SITE, SITE)   # after 根本没变
        self.assertFalse(report["all_passed"], "声明改动与实际不符必须报失败")
        self.assertFalse(report["results"][0]["passed"])


class TestPixelDiff(unittest.TestCase):
    def test_logo_resize_detected_in_local_region(self):
        d = diff_configs(SITE, _patched(21))
        self.assertGreater(d["changed_ratio"], 0.0, "变化必须被检出")
        self.assertLess(d["changed_ratio"], 0.5, "logo 放大不应是全图级变化")
        self.assertIsNotNone(d["box"])
        self.assertEqual(d["box"][0], 40 + 16, "变化区域起点应是 logo 右缘（16→21 加宽 5px）")

    def test_identical_configs_zero_change(self):
        d = diff_configs(SITE, SITE)
        self.assertEqual(d["changed_ratio"], 0.0)
        self.assertIsNone(d["box"])


class TestRoundEscalation(unittest.TestCase):
    def test_third_unconfirmed_round_escalates(self):
        with tempfile.TemporaryDirectory() as tmp:
            r1 = record_round(tmp, "logo_size", confirmed=False)
            r2 = record_round(tmp, "logo_size", confirmed=False)
            self.assertFalse(r1["escalated"])
            self.assertFalse(r2["escalated"])
            r3 = record_round(tmp, "logo_size", confirmed=False)
            self.assertTrue(r3["escalated"], "第 3 轮未确认必须升级转人工")
            self.assertTrue((Path(tmp) / "rounds_events.jsonl").exists(),
                            "升级必须留事件记录")
            r_reset = record_round(tmp, "logo_size", confirmed=True)
            self.assertEqual(r_reset["rounds"], 0, "客户确认后计数归零")


if __name__ == "__main__":
    unittest.main()
