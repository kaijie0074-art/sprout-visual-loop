"""参考图对齐：『做个像抖音那样的』→ 最近模板 + 差异清单（源文档 3.1 路线 5）。

不解析成全量仿制（侵权 + 范围失控），而是映射到平台模板库最接近的模板，
把差异点显式列出让客户确认。
"""

TEMPLATES = {
    "tpl_short_video": {"name": "短视频模板", "tags": ["短视频", "竖屏", "信息流"]},
    "tpl_ecommerce":   {"name": "电商带货模板", "tags": ["商城", "购物", "优惠券"]},
    "tpl_community":   {"name": "社区论坛模板", "tags": ["社区", "帖子", "评论"]},
}

# 参考产品 → 模板相似度（人工标注的先验，演示用）
REF_ALIGNED = {
    "抖音": ("tpl_short_video", 0.82),
    "快手": ("tpl_short_video", 0.76),
    "淘宝": ("tpl_ecommerce", 0.80),
    "小红书": ("tpl_community", 0.71),
}

DEFAULT_DIFFS = [
    {"area": "首页信息流", "template_has": "单列全屏上下滑", "customer_ref": "双列瀑布流卡片"},
    {"area": "底部导航", "template_has": "5 tab 标准", "customer_ref": "截图为 4 tab"},
    {"area": "广告位", "template_has": "信息流第 4 位原生广告", "customer_ref": "参考图未见广告位"},
]


def align_reference(ref_text: str) -> dict:
    """参考表达 → 最接近模板 + 差异清单；绝不返回『照抄整站』。"""
    for name, (tpl_id, sim) in REF_ALIGNED.items():
        if name in ref_text:
            return {
                "reference": ref_text,
                "template": {"id": tpl_id, **TEMPLATES[tpl_id]},
                "similarity": sim,
                "diffs": DEFAULT_DIFFS,
                "copy_all": False,
                "note": "以模板为底 + 差异清单逐项确认，禁止全量仿制参考产品",
            }
    return {
        "reference": ref_text,
        "template": None,
        "similarity": 0.0,
        "diffs": [],
        "copy_all": False,
        "note": "未匹配到模板：转人工确认参考意图",
    }
