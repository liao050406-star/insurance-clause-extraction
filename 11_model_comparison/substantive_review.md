# 实质一致复核（人工口径第二指标）

- Gold SHA-256：`e76ddd93c670b1581d686af81228273319b09b0a7a2f19ff1fa15cab38959942`
- 本指标为**人工复核口径**，与严格字符比较（下界）并列展示，不作为机器可复现指标。
- 规则：严格判错的项中，除下方「实质分歧」清单外，均视为**语义等价差异**。

## 双口径对比

| 模型 | 严格正确 | 语义等价 | 实质分歧 | 严格准确率 | 实质准确率 |
|---|---:|---:|---:|---:|---:|
| codex_gpt5 | 65 | 0 | 0 | 100.00% | 100.00% |
| claude_sonnet | 34 | 25 | 6 | 52.31% | 90.77% |
| claude_opus | 38 | 20 | 7 | 58.46% | 89.23% |

## 实质分歧清单（13 处，需人工复核）

| 产品 | 字段 | 模型 | 原因 |
|---|---|---|---|
| hengan_chuanshi_ruiying_b | policy_loan | claude_sonnet | 漏 basis 子键（贷款额度计算基数「现金价值扣除各项欠款后余额」） |
| cpic_xinxiangban_2025 | policy_loan | claude_sonnet | 漏 basis 子键 |
| nci_ezengfu_youxiang | policy_loan | claude_sonnet | 漏 basis 子键 |
| dongfang_zun_4_zhenxiang | policy_loan | claude_sonnet | 漏 basis 子键 |
| nci_ezengfu_youxiang | effective_sum_assured_definition | claude_sonnet | 定义与增长公式混写（把保险金额写成基本保险金额×1.02^(n-1)） |
| hengan_chuanshi_ruiying_b | dividend_payment_method | claude_sonnet | 漏记「已分配红利计入以后年度红利计算基数」 |
| hengan_chuanshi_ruiying_b | policy_loan | claude_opus | 漏 basis 子键 |
| cpic_xinxiangban_2025 | policy_loan | claude_opus | 漏 basis 子键 |
| nci_ezengfu_youxiang | policy_loan | claude_opus | 漏 basis 子键 |
| dongfang_zun_4_zhenxiang | policy_loan | claude_opus | 漏 basis 子键 |
| nci_ezengfu_youxiang | age_benefit_ratio | claude_opus | 年龄边界 off-by-one（18-41/41-61 应为 18-40/41-60） |
| nci_ezengfu_youxiang | effective_sum_assured_definition | claude_opus | 误判 null（漏抽有效保险金额定义） |
| hengan_chuanshi_ruiying_b | dividend_payment_method | claude_opus | 漏记「已分配红利计入以后年度红利计算基数」 |

## 口径边界

- 「语义等价」只覆盖表述、结构、键名、详略差异；**不覆盖**数值/边界变化、null 误判、子键遗漏、定义混写。
- 实质准确率是人工判断，不能替代严格准确率；对外引用两者必须同时给出。

