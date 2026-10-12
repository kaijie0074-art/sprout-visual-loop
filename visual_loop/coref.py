"""共指消解：对话实体表 + 指代链（源文档 3.1 难点 3）。

『那个放左边』的『那个』指上一轮聊的 banner 还是刚发的视频模块？
——维护 实体 → 最近提及轮次 的登记表；解析取最近提及者；
同轮多活跃实体或无先行语 → 闭合失败 → 调用方转 assumptions。
"""


class EntityTable:
    def __init__(self):
        self._entities = {}   # entity_id -> {"name", "turns": [..]}
        self._order = []      # 提及时间线：entity_id 序列

    def mention(self, entity_id: str, name: str, turn: int):
        if entity_id not in self._entities:
            self._entities[entity_id] = {"name": name, "turns": []}
        self._entities[entity_id]["turns"].append(turn)
        self._order.append(entity_id)

    def resolve(self, token: str = "那个") -> str | None:
        """返回指代实体 id；无法唯一闭合返回 None。"""
        if not self._order:
            return None
        last_turn = max(self._entities[e]["turns"][-1] for e in self._order)
        candidates = {e for e in self._order
                      if self._entities[e]["turns"][-1] == last_turn}
        if len(candidates) != 1:
            return None          # 同轮多实体：闭合不了，转人工确认
        return next(iter(candidates))

    def name_of(self, entity_id: str) -> str:
        return self._entities[entity_id]["name"]


REF_TOKENS = {"那个", "这个", "那只", "呢个"}


def is_reference_token(text: str) -> bool:
    return any(t in text for t in REF_TOKENS)
