"""visual_loop —— 视觉反馈闭环（问题②+④）。

输入侧（②）：多模态脏输入 → 需求意图树 + 假设清单（反幻觉）
输出侧（④）：提案式修改 + 属性断言 + 像素 diff + 往返升级（半自动闭环）
"""

__version__ = "1.0.0"

from .api import (align_reference, build_intent_tree, confirm_assumption,  # noqa: F401
                  dark_hallucination_count, diff_configs, propose,
                  record_round, verify_change)
