# 变更日志

遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased] - 2026-10-14

自主深潜研究（docs/research/deep-dive-20261014.md，61 次真实 VLM 调用）驱动的两项修复：

### 修复
- **容错 JSON 解析** `vlm.py::parse_model_json`：实测 glm-4v-flash 在深嵌套页面 6/40 次输出畸形 JSON（`{ {` 双开括号 + 配对尾括号、截断），原实现 `json.loads` 直接抛异常中断 intake——现逐级修复（code fence/双括号/补尾括号），5/5 真实故障输出回放通过。
- **自一致置信** `vlm.py::describe_stable` + `intent_tree.build_intent_tree(stable_k=3)`：实测自报 confidence 坍缩为常数 1.0（校准失效）且同图 5 次采样 3 种组件集合（非确定性），幻觉组件以 present=true+conf=1.0 直通需求树。现在组件 confidence = 跨采样一致率（缺席=反对票），<0.85 自动落回 assumptions——live 验证：歧义密集页全部组件转人工，清晰格式塔页 3/3 直通。

### 新增
- 回归测试 7 项（共 29）：真实畸形输出回放、经验置信度、幻觉组件端到端路由（`tests/test_research_fixes.py`）。
- 研究证据链 `evidence/deep-dive-20261014/`：确定性实验位图生成器、串行节流 harness、评分器、原始结果（results.jsonl）与复现命令。

## [v1.0.0] - 2026-10-13

修复问题报告（Issue #1）输入侧 5 类难点与输出侧验证缺失，18/18 测试通过。

### 新增
- **意图树构建** `intent_tree.py`：页面→组件→修改意图三级结构；每个节点带 `source`（哪条消息/哪张图）与 `confidence`；**只有明说证据进树**。
- **假设清单机制** `assumptions.py`：幻觉补全（present=False）、低置信判定（<0.85）、指代未闭合全部落 assumptions 供人工逐条 accept/reject；确认后转正（source=human_confirmed）；`dark_hallucination_count` 合格线 0。
- **共指消解** `coref.py`：对话实体表 + 指代链；同轮多实体/无先行 → 闭合失败进 assumptions（显式问人，不瞎猜）。
- **粤语归一** `normalize.py`：词表级方言映射（摆呢度→放这里 等），归一前置保证指代链不断。
- **分层置信路由**：清晰截图直接解析；手绘稿强制 `requires_human_review` 人工确认页。
- **参考图对齐** `align.py`：『像抖音那样』→ 最近模板 + 3 条差异清单，`copy_all=False` 禁止全量仿制。
- **提案式修改** `proposals.py`：模糊尺寸 → 3 候选（+15%/+30%/重排）；模糊色彩 → 6 色候选色卡；每候选附 PPM 预览截图。
- **确定性渲染器** `render.py` + **像素 diff** `pixel_diff.py`：配置→截图→变化率/区域 bbox（借 pixelmatch 思想的零依赖实现）。
- **属性断言** `assertions.py`：声明的每条改动逐条机检——"说改了但没改"必被抓住（输出侧唯一可 100% 自动化的环节）。
- **往返升级** `rounds.py`：同一处修改第 3 轮未确认 → 升级转人工 + 事件留痕。
- 测试 18 项（输入侧 12 + 输出侧 6）；CI（Python 3.11）。

## [v0.1.0] - 2026-10-13

缺陷基线（现状快照）：VLM/ASR 输出直接当需求文档的直通管线。

- 无假设清单（暗幻觉直通）、无置信路由、无归一/共指、修改后不验证、单点拍板、无往返计数。
- 同一套测试 15 项失败——复现材料（docs/02）。
