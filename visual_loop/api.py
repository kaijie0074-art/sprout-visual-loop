"""【缺陷基线·现状】直通管线：VLM/ASR 输出直接当需求文档用。

现状问题（docs/01）：
  - 无假设清单：幻觉补全（客户没提的登录页）直接混进需求树（暗幻觉）；
  - 无置信路由：手绘稿低置信判定照样直接采用；
  - 无归一/无共指：粤语转写、『那个』指代一律不解，修改意图绑定不了目标；
  - 修改后不验证：声明改了就算改了（无属性断言、无像素对比）；
  - 模糊指令单点拍板：『大一点』直接给一个数，不出候选色卡/预览；
  - 无往返计数：审美死胡同里无限打转。
"""
from .assumptions import dark_hallucination_count  # 计数函数本身是中性的
from .mock_asr import transcribe  # noqa: F401
from .mock_vlm import describe

_KEYWORDS = {"banner": "banner", "logo": "logo", "视频": "video_feed",
             "社区": "community", "商城": "mall", "登录": "login_screen"}


def build_intent_tree(inputs: dict) -> dict:
    """现状：关键词直接进树（无 source/无归一/无共指/无假设），VLM 全采信。"""
    components = []
    for t in inputs.get("transcript", []):
        text = t.get("text", "")                    # 现状：不归一，粤语原样
        for kw, comp in _KEYWORDS.items():
            if kw in text:
                components.append({"name": comp})   # 现状：无 source、无 confidence
    for img in inputs.get("images", []):
        d = describe(img["key"], img.get("scenario", "screenshot_clear"))
        for c in d["components"]:                   # 现状：present=False 也进树（暗幻觉）
            components.append({"name": c["name"]})
    return {"tree": {"pages": [{"pageId": "home", "components": components,
                                "modifications": []}]},   # 现状：指代不解，无修改意图
            "assumptions": [], "requires_human_review": False,
            "unresolved_refs": [], "reference_hints": []}


def confirm_assumption(report: dict, assumption_id: str, accept: bool = True) -> dict:
    return report  # 现状：没有确认机制，原样返回


def align_reference(ref_text: str) -> dict:
    # 现状：参考图= 全量仿制（侵权 + 范围失控）
    return {"reference": ref_text, "template": {"id": "full_copy"}, "similarity": 1.0,
            "diffs": [], "copy_all": True}


def propose(config: dict, instruction: dict, out_dir) -> dict:
    # 现状：模糊指令单点拍板，一个候选，无预览
    return {"instruction": instruction,
            "candidates": [{"id": "only", "patch": [
                {"op": "replace", "path": "/pages/0/components/0/props/w", "value": 24}],
                "preview": None, "rationale": "模型拍板"}],
            "note": "现状：单点执行"}


def verify_change(declared: list, config_before: dict, config_after: dict) -> dict:
    # 现状：声明了就算改了，不做机检
    return {"all_passed": True, "results": [], "summary": "现状：无验证"}


def diff_configs(config_a: dict, config_b: dict, threshold: int = 30) -> dict:
    # 现状：输出侧无像素对比能力
    return {"changed_ratio": 0.0, "changed_pixels": 0, "box": None, "max_delta": 0}


def record_round(base_dir, target: str, confirmed: bool = False) -> dict:
    # 现状：无往返计数，永不升级
    return {"target": target, "rounds": 1, "escalated": False}
