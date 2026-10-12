"""【缺陷基线·现状】visual_loop 直通管线包入口。"""
__version__ = "0.1.0"

from .api import (align_reference, build_intent_tree, confirm_assumption,  # noqa: F401
                  dark_hallucination_count, diff_configs, propose,
                  record_round, verify_change)
