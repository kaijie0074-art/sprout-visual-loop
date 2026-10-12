# sprout-visual-loop（缺陷基线 v0.1.0）

> ⚠️ **缺陷基线快照**：VLM/ASR 输出直接当需求文档用的直通管线，用于复现问题报告的输入侧 6 类难点与输出侧 5 类缺失。

## 现状

- 无假设清单：幻觉补全（客户没提的登录页）直接混进需求树（暗幻觉）；
- 无置信路由：手绘稿低置信判定照样直接采用；
- 无归一/无共指：粤语转写、『那个』指代一律不解；
- 参考图 = 全量仿制；修改后不验证；模糊指令单点拍板；无往返计数。

## 复现

```bash
python3 -m unittest discover -s tests
# Ran 18 tests ... FAILED (failures=13, errors=2)
```

失败清单与难点对位见主仓库 `docs/02-复现材料.md`；修复版见 [sprout-visual-loop](../sprout-visual-loop)（v1.0.0，18/18 通过）。
