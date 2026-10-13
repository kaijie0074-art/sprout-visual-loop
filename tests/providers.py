"""测试替身 VLM（仅 tests/ 内使用；产品代码零脚本化模型）。

ScriptedVlm：按场景语料返回结构化页面描述，驱动意图树分层置信路由的
确定性回归。接口与 visual_loop.vlm.VlmClient.describe 相同。
"""
from vlm_scenarios import SCENARIOS


class ScriptedVlm:
    def __init__(self, default_scenario: str = "screenshot_clear"):
        self.default_scenario = default_scenario

    def describe(self, image_path: str, scenario: str = "") -> dict:
        out = {"image": image_path, "scenario": scenario or self.default_scenario}
        out.update(SCENARIOS[scenario or self.default_scenario])
        return out


class ScenarioMapVlm:
    """按 inputs.images[].scenario 字段路由语料（原测试形态的等价替身）。"""

    def __init__(self, fallback: str = "screenshot_clear"):
        self.fallback = fallback

    def describe(self, image_path: str, scenario: str = "") -> dict:
        out = {"image": image_path, "scenario": scenario or self.fallback}
        out.update(SCENARIOS[scenario or self.fallback])
        return out
