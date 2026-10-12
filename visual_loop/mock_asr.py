"""确定性 Mock ASR：输出带粤语口音的转写噪音（源文档 3.1 难点 4）。"""

TRANSCRIPTS = {
    "voice_msg_1": {
        "raw": "个只 logo 摆左边咯 睇下 做个好似抖音咁样嘅 稳阵",
        "lang": "yue-mixed",
    },
    "voice_msg_2": {
        "raw": "个只摆呢度 好睇啲",
        "lang": "yue-mixed",
    },
}


def transcribe(audio_key: str) -> dict:
    out = {"audio_key": audio_key}
    out.update(TRANSCRIPTS[audio_key])
    return out
