# 多模型结果目录

每个模型使用独立目录，文件名必须包含模型标识，避免覆盖和答案串线。

```text
model_outputs/
├─ codex_gpt5/
│  └─ <product_id>__codex_gpt5.json     # Gold-aware 开发复核（非盲测，值为 Gold 副本）
├─ claude_sonnet/
│  └─ <product_id>__claude_sonnet.json  # Claude Sonnet 5 独立盲测
└─ claude_opus/
   └─ <product_id>__claude_opus.json    # Claude Opus 5.5 独立盲测
```

当前已完成的三个模型标识：

- `codex_gpt5`：Gold-aware 开发复核，`independent_blind_test=false`，仅用于验证结构与报告链路，不计入独立盲测准确率。
- `claude_sonnet`：Claude Sonnet 5 独立盲测，`independent_blind_test=true`。
- `claude_opus`：Claude Opus 5.5 独立盲测，`independent_blind_test=true`。

模型之间不得共享结果。三方对比报告见 `11_model_comparison/three_model_comparison.md`，实质复核见 `11_model_comparison/substantive_review.md`。
