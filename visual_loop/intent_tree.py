"""需求意图树（问题②输出物）：页面 → 组件 → 修改意图，节点全部带 source 与 confidence。

铁律（反幻觉核心，源文档 3.1 路线 1-2）：
  - 只有**明说证据**（transcript 关键词 / 图中真实存在且置信度达标）的需求才能进树；
  - 一切推断项（无证据组件、低置信判定、指代未闭合）进 assumptions 待人工逐条确认；
  - "像 X 那样"不进树——标记为参考提示，走模板对齐（align），不做全量仿制。
"""
from .coref import EntityTable, is_reference_token
from .normalize import normalize
from .vlm import VlmClient

CONF_THRESHOLD = 0.85   # 组件类型判定置信阈值

COMPONENT_KEYWORDS = {
    "短视频": "video_feed", "视频": "video_feed", "banner": "banner", "横幅": "banner",
    "logo": "logo", "社区": "community", "论坛": "community", "商城": "mall",
    "登录": "login_screen", "搜索": "search",
}

POS_MAP = {"放左边": "left", "放右边": "right", "放上面": "top",
           "放下面": "bottom", "放这里": "here", "放大": "bigger"}


def build_intent_tree(inputs: dict, vlm=None) -> dict:
    """inputs = {transcript: [{turn, text}], images: [{key, path}]} → IntentReport。

    vlm 缺省时构造真实 VLM 客户端（OpenAI 兼容多模态，需环境变量凭证）。
    """
    # 惰性解析：纯 transcript 输入不触达 VLM，无需凭证即可运行
    if vlm is None and inputs.get("images"):
        vlm = VlmClient()
    home = {"pageId": "home", "components": [], "modifications": []}
    assumptions, unresolved, ref_hints = [], [], []
    entities = EntityTable()
    counter = [0]

    def add_asm(guess, reason, source):
        counter[0] += 1
        assumptions.append({"id": f"ASM-{counter[0]:03d}", "guess": guess,
                            "reason": reason, "source": source})

    # ---------- 语音/文字轮次：显式需求进树，指代走实体表 ----------
    for t in inputs.get("transcript", []):
        text = normalize(t.get("text", ""))
        turn = t.get("turn", 0)
        mentioned = set()
        for kw in sorted(COMPONENT_KEYWORDS, key=len, reverse=True):
            comp = COMPONENT_KEYWORDS[kw]
            if kw in text and comp not in mentioned:
                mentioned.add(comp)
                entities.mention(comp, comp, turn)
                home["components"].append({
                    "name": comp, "confidence": 1.0,
                    "source": {"turn": turn, "modality": "transcript"}})

        pos = next((v for k, v in POS_MAP.items() if k in text), None)
        if pos:
            if is_reference_token(text):
                target = entities.resolve()
                if target:
                    home["modifications"].append({
                        "target": target, "action": "resize" if pos == "bigger" else "move",
                        "value": pos, "source": {"turn": turn, "modality": "transcript"}})
                else:
                    add_asm(f"指代目标不明（{pos}）", "『那个』无唯一先行实体，指代未闭合",
                            {"turn": turn, "modality": "transcript"})
                    unresolved.append({"turn": turn, "text": text})

        if ("像" in text or "参考" in text) and ("那样" in text or "一样" in text or "风格" in text):
            ref_hints.append({"turn": turn, "text": text,
                              "hint": "参考表达：走模板对齐+差异清单，禁止全量仿制"})

    # ---------- 图片：分层置信路由 ----------
    review = False
    for img in inputs.get("images", []):
        d = vlm.describe(img.get("path", img["key"]), img.get("scenario", ""))
        if d["requires_human_review"]:
            review = True   # 手绘稿：强制人工确认页（难点 2）
        for c in d["components"]:
            src = {"image": img["key"], "modality": "vlm", "confidence": c["confidence"]}
            if not c["present"]:
                add_asm(c["name"], "幻觉补全捕获：图中无此组件，客户未明说", src)
            elif c["confidence"] >= CONF_THRESHOLD:
                home["components"].append(
                    {"name": c["name"], "confidence": c["confidence"], "source": src})
            else:
                add_asm(c["name"],
                        f"置信度 {c['confidence']:.2f} < {CONF_THRESHOLD}，组件类型判定不稳",
                        src)

    return {"tree": {"pages": [home]}, "assumptions": assumptions,
            "requires_human_review": review, "unresolved_refs": unresolved,
            "reference_hints": ref_hints}
