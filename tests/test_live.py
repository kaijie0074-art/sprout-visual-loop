"""真实 VLM/ASR live 测试（env-gated，无凭证自动跳过）。

- VLM：VISUAL_LOOP_TEST_IMAGE 指向一张真实截图时运行
- ASR：VISUAL_LOOP_TEST_AUDIO 指向一段真实音频时运行
"""
import os
import unittest

from visual_loop.asr import AsrClient
from visual_loop.vlm import VlmClient

_TEST_IMAGE = os.environ.get("VISUAL_LOOP_TEST_IMAGE", "")
_TEST_AUDIO = os.environ.get("VISUAL_LOOP_TEST_AUDIO", "")
_HAS_KEY = bool(os.environ.get("VISUAL_LOOP_API_KEY") or os.environ.get("OPENAI_API_KEY"))


@unittest.skipIf(not (_HAS_KEY and _TEST_IMAGE), "需要 VISUAL_LOOP_API_KEY 与 VISUAL_LOOP_TEST_IMAGE")
class TestVlmLive(unittest.TestCase):
    def test_describe_returns_protocol(self):
        d = VlmClient().describe(_TEST_IMAGE)
        self.assertIn("components", d)
        self.assertIsInstance(d["requires_human_review"], bool)
        for c in d["components"]:
            self.assertIn("name", c)
            self.assertIn("confidence", c)


@unittest.skipIf(not (_HAS_KEY and _TEST_AUDIO), "需要 VISUAL_LOOP_API_KEY 与 VISUAL_LOOP_TEST_AUDIO")
class TestAsrLive(unittest.TestCase):
    def test_transcribe_returns_text(self):
        t = AsrClient().transcribe(_TEST_AUDIO)
        self.assertIn("raw", t)
        self.assertTrue(t["raw"].strip(), "转写结果不应为空")


if __name__ == "__main__":
    unittest.main()
