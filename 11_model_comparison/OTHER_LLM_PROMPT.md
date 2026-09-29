# 另外两个 LLM 的盲测提示词

> 状态：本提示词已按此执行。模型 B=`claude_sonnet`、模型 C=`claude_opus` 的盲测输出见 `06_result_json/model_outputs/`，四方对比见 `three_model_comparison.md`。此文件保留作为人工/第三方复现的原始说明。

请分别在模型 B、模型 C 的独立新会话中发送以下文字，并附上对应产品的
`05_LLM_Prompt_Schema/prompts/generated_v3/<product_id>__v3_prompt.md` 全文。

```text
你正在参加保险条款结构化抽取盲测。请只依据我随后提供的 V3 提示词和其中的保险条款文本完成抽取。

硬性要求：
1. 不得查看或推测 gold.csv，不得参考其他模型答案。
2. 输出必须是一个合法 JSON 对象，不要使用 Markdown 代码围栏，不要补充解释。
3. 保留 V3 要求的 13 个字段及每个字段的 value、source_clause、source_text。
4. 无法由原文确认时填 null，禁止用行业常识补值。
5. source_text 必须是原文连续证据，不得拼接或改写；若一个字段涉及多处规则，优先引用能直接支持结构化结论的完整条款段落。
6. metadata.model_id 填你的实际模型短名；metadata.product_id 使用提示词给出的 product_id；metadata.independent_blind_test 填 true。

现在请处理下面这份 V3 提示词：
```

文件命名规则：`<product_id>__<model_id>.json`。模型 B、C 分别放入
`06_result_json/model_outputs/<model_id>/`，随后运行三模型差异脚本。
