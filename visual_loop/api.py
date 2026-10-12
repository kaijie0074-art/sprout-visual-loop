"""稳定 API 表面：baseline（直通版）与最终态共用同一组签名，构成回归对比。"""
from .align import align_reference
from .assumptions import confirm_assumption, dark_hallucination_count
from .intent_tree import build_intent_tree
from .pixel_diff import diff_configs
from .proposals import propose
from .rounds import record_round
from .assertions import verify as verify_change

__all__ = ["build_intent_tree", "confirm_assumption", "dark_hallucination_count",
           "align_reference", "propose", "verify_change", "diff_configs", "record_round"]
