"""假设清单机制：把"模型的猜测"从暗处拿到明处定价（源文档 3.1 路线 2）。

推断项全部落 assumptions，人工逐条 accept/reject；
accept 的转正进树（source 标 human_confirmed），reject 的丢弃。
暗幻觉 = 树里存在客户未明说且未经确认的节点 —— 本机制下恒为 0。
"""
import copy


def confirm_assumption(report: dict, assumption_id: str, accept: bool = True) -> dict:
    """确认/驳回一条假设，返回更新后的 report（不改入参）。"""
    updated = copy.deepcopy(report)
    remaining = []
    for asm in updated["assumptions"]:
        if asm["id"] != assumption_id:
            remaining.append(asm)
            continue
        if accept:
            updated["tree"]["pages"][0]["components"].append({
                "name": asm["guess"], "confidence": 0.99,
                "source": {"modality": "human_confirmed", "from": asm["source"]}})
        # reject：直接丢弃，不进树
    updated["assumptions"] = remaining
    return updated


def dark_hallucination_count(report: dict) -> int:
    """树内无 source（或 source 为空）的节点数——合格线为 0。"""
    n = 0
    for page in report["tree"]["pages"]:
        for comp in page["components"]:
            if not comp.get("source"):
                n += 1
    return n
