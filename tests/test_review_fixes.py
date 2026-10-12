"""评审轮修复验证（PR #2 评审意见 R3-1/R3-2 的回归测试）。"""
import unittest

from visual_loop.api import build_intent_tree, confirm_assumption
from visual_loop.images import blank
from visual_loop.pixel_diff import diff


class TestReviewFixes(unittest.TestCase):
    def test_r3_1_unknown_assumption_id_raises(self):
        """R3-1：未知 assumption_id 必须显式报错，不得静默无操作。"""
        report = build_intent_tree(
            {"images": [{"key": "s", "scenario": "hallucinated"}]})
        with self.assertRaises(ValueError):
            confirm_assumption(report, "ASM-999", accept=True)
        # 报告本身不被破坏，正确 id 仍可确认
        ok = confirm_assumption(report, report["assumptions"][0]["id"], accept=True)
        self.assertEqual(ok["assumptions"], [])

    def test_r3_2_diff_size_mismatch_raises(self):
        """R3-2：尺寸不等的两图显式 ValueError（带尺寸信息），不是裸 IndexError。"""
        a = blank(96, 64)
        b = blank(64, 96)
        with self.assertRaises(ValueError) as ctx:
            diff(a, b)
        self.assertIn("96x64", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
