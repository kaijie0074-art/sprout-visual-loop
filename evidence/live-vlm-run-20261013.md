# 真实 VLM/ASR live 测试实跑记录 · 2026-10-13

```bash
export VISUAL_LOOP_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4   # 智谱 GLM Coding Plan
export VISUAL_LOOP_API_KEY=<凭证经环境变量注入，不入库>
export VISUAL_LOOP_VLM_MODEL=glm-5.3-flash
export VISUAL_LOOP_TEST_IMAGE=/tmp/vl_test_ui.png   # 480×800 程序生成 UI 截图（banner+feed 卡片+tab 栏）
python3 -m unittest tests.test_live -v
```

结果：

```
test_describe_returns_protocol ... ok        # 真实 VLM 返回协议正确描述（components/confidence/requires_human_review）
test_transcribe_returns_text ... skipped     # 需要音频素材；且 glm-asr 不在 Coding Plan 资源包内（429 余量不足）
Ran 2 tests in 16.229s
OK (skipped=1)
```

## 说明

- VLM 走真实多模态调用：图片 base64 → chat/completions（image_url），模型 glm-5.3-flash
- ASR 双重限制如实记录：测试需 `VISUAL_LOOP_TEST_AUDIO` 真实音频；探测端点返回 `429 余量不足或无可用资源包`（glm-asr 不含在 Coding Plan 套餐）——ASR 路径在离线场景（ScriptedAsr）已有回归覆盖，在线路径待有资源包后补测
- 离线全量测试不受影响：`python3 -m unittest discover -s tests`
