"""方言/转写噪音归一：粤语词表映射 + 口水词剔除（源文档 3.1 难点 4）。

归一是共指消解的前置：『摆呢度』不归一成『放这里』，指代链就断了。
"""

CANTO_MAP = {
    "摆呢度": "放这里", "摆左边": "放左边", "摆右边": "放右边",
    "睇下": "看一下", "好睇": "好看", "稳阵": "可靠",
    "个只": "那个", "好似": "像", "咁样": "那样", "嘅": "的",
    "咯": "", "啲": "一些", "唔使": "不用", "系": "是",
}

FILLERS = {"咯", "呀", "啦", "嘛", "喎"}


def normalize(text: str) -> str:
    """粤语混合转写 → 标准中文表达（词表级替换，保序）。"""
    out = text
    for k in sorted(CANTO_MAP, key=len, reverse=True):
        out = out.replace(k, CANTO_MAP[k])
    out = " ".join(w for w in out.split() if w not in FILLERS)
    return " ".join(out.split())
