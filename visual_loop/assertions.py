"""属性断言：『Agent 说改了』必须机检为『配置里真的改了』（源文档 3.2 路线 3）。

这是输出侧唯一可 100% 自动化的环节：patch 声明的每条 from→to 变化，
逐条比对配置前后的实际值。防止"说改了但没改"的低级事故流入客户预览。
"""


def _get(config: dict, path: str):
    node = config
    for s in (x for x in path.split("/") if x):
        node = node[int(s)] if isinstance(node, list) else node[s]
    return node


def verify(declared: list, config_before: dict, config_after: dict) -> dict:
    """declared = [{path, expect_from, expect_to}] → 逐条机检报告。"""
    results = []
    for d in declared:
        actual_from = _get(config_before, d["path"])
        actual_to = _get(config_after, d["path"])
        results.append({
            "path": d["path"],
            "declared_from": d["expect_from"], "actual_from": actual_from,
            "declared_to": d["expect_to"], "actual_to": actual_to,
            "passed": actual_from == d["expect_from"] and actual_to == d["expect_to"],
        })
    return {"all_passed": all(r["passed"] for r in results), "results": results,
            "summary": "属性断言：所有声明的修改必须与配置实际变化一致"}
