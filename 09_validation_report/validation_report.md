# 新版 Gold Schema 验证报告

生成时间：2026-09-23T09:57:06+08:00

## 结果

- Gold 字段数：36
- 正确：36；错误：0
- 缺失产品：0；缺失字段：0
- 待人工复核：0
- 自动准确率：1.0
- Gold 原文摘录匹配：31/31
- Canonical 哈希匹配：32/32
- 字符区间直接还原：32/32

## 方法与范围

- 验收范围为富泽泽瑞一生、东方嘉富东方尊 4.0、恒安标准传世瑞盈 B 款三款终身寿险。
- 代码负责 PDF 文本提取、canonical 文本生成、章节切分、Prompt 组装、JSON Schema 校验、Gold 对比和对比表生成。
- LLM 用于根据条款正文生成结构化 JSON；本流程未使用 RAG，也未从 Gold 反填预测值。

## Prompt 版本与关键修改

- V1 初版：规定固定 JSON 形状、null/0 区分、比例单位、责任名称和免责原文逐字摘录。
- V2 最终版：补充具体投保年龄未载明必须为 null、固定比例递增与红利保险金额累加分开判断、保险期间表达归一化检查及输出前静默自检。
- 初版和最终版分别保存在 `prompts/v1_initial.md` 与 `prompts/v2_final.md`。

## 已修复问题

- 修复恒安条款只写“符合我们的要求”时投保年龄被错误补全的问题。
- 修复“至被保险人身故时终止”未被校验视为终身的问题。
- 修复红利保险金额累加被误判为固定比例保额增长的问题。
- 将不属于正式 30 字段业务 Schema 的保单贷款期限放入独立评估扩展结果，并保留条款 source。

## 未解决事项

- 本次 36 个 Gold 字段无未解决数值错误。其他未进入 Gold 的长文本责任与免责内容仍建议在正式使用前人工复核。

## 明细

| 产品 | 字段 | 结果 | Gold | 预测 | 来源校验 |
|---|---|---|---|---|---|
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | insured_age_range | correct | 0周岁（须出生满28日）至70周岁 | 0周岁(须出生满28日)至70周岁 | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | benefit_age_band_coverage | correct | 全年龄段覆盖 | 全年龄段覆盖 | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | hesitation_period_days | correct | 15 | 15 | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | insurance_period | correct | 终身 | 终身 | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | waiting_period_days | correct | None | None | not_applicable |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | coverage_scope | correct | 身故或全残 | 身故或全残 | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | fixed_insured_amount_annual_growth_rate | correct | 0.0175 | 0.0175 | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | insurance_amount_growth_mechanism | correct | 固定比例复利增长 | 固定比例复利增长 | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | is_participating | correct | True | True | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | grace_period_days | correct | 60 | 60 | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | policy_loan_max_ratio | correct | 0.8 | 0.8 | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | policy_loan_max_term_months | correct | 6 | 6 | matched_strict |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | insured_age_range | correct | 0周岁（须出生满28日）至75周岁 | 0周岁（须出生满28日）至75周岁 | matched_strict |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | benefit_age_band_coverage | correct | 全年龄段覆盖 | 全年龄段覆盖 | matched_strict |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | hesitation_period_days | correct | 15 | 15 | matched_strict |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | insurance_period | correct | 终身 | 终身 | matched_strict |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | waiting_period_days | correct | None | None | not_applicable |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | coverage_scope | correct | 身故或全残 | 身故或全残 | matched_strict |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | fixed_insured_amount_annual_growth_rate | correct | 0.02 | 0.02 | matched_strict |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | insurance_amount_growth_mechanism | correct | 固定比例复利增长 | 固定比例复利增长 | matched_strict |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | is_participating | correct | None | None | not_applicable |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | grace_period_days | correct | 60 | 60 | matched_strict |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | policy_loan_max_ratio | correct | 0.8 | 0.8 | matched_strict |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | policy_loan_max_term_months | correct | 6 | 6 | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | insured_age_range | correct | None | None | not_applicable |
| 恒安标准传世瑞盈B款终身寿险（分红型） | benefit_age_band_coverage | correct | 全年龄段覆盖 | 全年龄段覆盖 | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | hesitation_period_days | correct | 15 | 15 | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | insurance_period | correct | 终身 | 终身 | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | waiting_period_days | correct | 90 | 90 | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | coverage_scope | correct | 身故 | 身故 | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | fixed_insured_amount_annual_growth_rate | correct | None | None | not_applicable |
| 恒安标准传世瑞盈B款终身寿险（分红型） | insurance_amount_growth_mechanism | correct | 红利保险金额累加（非固定增长） | 红利保险金额累加（非固定增长） | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | is_participating | correct | True | True | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | grace_period_days | correct | 60 | 60 | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | policy_loan_max_ratio | correct | 0.8 | 0.8 | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | policy_loan_max_term_months | correct | 6 | 6 | matched_strict |

## 说明

- 数值准确率与 source 完整性分开统计。
- Gold 摘录仅做 NFKC 与空白归一化后执行连续子串匹配。
- 不从 Gold 反填预测值。
- 本报告及产品对比仅用于条款信息整理与课程作业，不构成保险建议、产品推荐或产品排名。
