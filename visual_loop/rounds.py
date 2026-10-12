"""往返计数与升级：同一处修改超过 2 轮未确认 → 人工优先（源文档 3.2 路线 5）。

防止 Agent 在审美死胡同里烧 token：升级事件落盘，转设计师流程。
"""
import json
import time
from pathlib import Path

ESCALATE_AFTER = 3   # 第 3 轮仍未确认 → 升级


def record_round(base_dir, target: str, confirmed: bool = False) -> dict:
    state_path = Path(base_dir) / "rounds.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}

    if confirmed:
        state[target] = 0
        state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        return {"target": target, "rounds": 0, "escalated": False}

    rounds = state.get(target, 0) + 1
    state[target] = rounds
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    escalated = rounds >= ESCALATE_AFTER
    if escalated:
        ev = Path(base_dir) / "rounds_events.jsonl"
        with ev.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": round(time.time(), 3), "type": "escalate_to_human",
                                "target": target, "rounds": rounds}, ensure_ascii=False) + "\n")
    return {"target": target, "rounds": rounds, "escalated": escalated}
