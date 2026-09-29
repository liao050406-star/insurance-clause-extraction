# 三模型（+ Gold）四方对比报告

## 实验信息

- Gold：`08_gold_csv对比/gold.csv`（只读），共 65 行，SHA-256 `e76ddd93c670b1581d686af81228273319b09b0a7a2f19ff1fa15cab38959942`
- 模型 A：`codex_gpt5`（Gold-aware 开发复核，**非盲测**，用于链路核验）
- 模型 B：`claude_sonnet`（Claude Sonnet 5，**独立盲测**）
- 模型 C：`claude_opus`（Claude Opus 5.5，**独立盲测**）
- 输入：三模型共用同一份冻结 V3 提示词 `05_LLM_Prompt_Schema/prompts/generated_v3/`

## 总体指标

| 模型 | 正确 | 错误 | 缺失 | 准确率 | 盲测 |
|---|---:|---:|---:|---:|---|
| codex_gpt5 | 65 | 0 | 0 | 100.00% | 否 |
| claude_sonnet | 34 | 31 | 0 | 52.31% | 是 |
| claude_opus | 38 | 27 | 0 | 58.46% | 是 |

## 双口径准确率（人工复核）

严格字符比较把「语义等价差异」也判错，是**下界**；实质口径由人工逐条复核、把 13 处真实分歧单列（详见 `substantive_review.md`）。

| 模型 | 严格准确率（机器） | 实质准确率（人工复核） |
|---|---:|---:|
| codex_gpt5 | 100.00%（Gold 副本，无泛化意义） | 100.00%（无意义） |
| claude_sonnet | 52.31%（34/65） | 90.77%（59/65） |
| claude_opus | 58.46%（38/65） | 89.23%（58/65） |

## 各模型字段级准确率

| 字段 | codex_gpt5 | claude_sonnet | claude_opus |
|---|---|---|---|
| insured_age_range（投保年龄） | 5/5 | 4/5 | 4/5 |
| waiting_period（等待期（天）） | 5/5 | 5/5 | 5/5 |
| coverage_type（保险责任类型） | 5/5 | 5/5 | 5/5 |
| benefit_before_payment_end（交费期满前给付） | 5/5 | 0/5 | 0/5 |
| benefit_after_payment_end（交费期满后给付） | 5/5 | 0/5 | 0/5 |
| age_benefit_ratio（年龄给付比例） | 5/5 | 0/5 | 4/5 |
| guaranteed_growth_rate（固定递增系数） | 5/5 | 5/5 | 5/5 |
| effective_sum_assured_definition（有效保险金额定义） | 5/5 | 0/5 | 0/5 |
| policy_loan（保单贷款） | 5/5 | 1/5 | 1/5 |
| reduction_rule（减额规则） | 5/5 | 0/5 | 0/5 |
| dividend_guarantee（红利是否保证） | 5/5 | 5/5 | 5/5 |
| dividend_type（红利类型） | 5/5 | 5/5 | 5/5 |
| dividend_payment_method（红利领取/分配方式） | 5/5 | 4/5 | 4/5 |

## 各模型产品级准确率

| 产品 | codex_gpt5 | claude_sonnet | claude_opus |
|---|---|---|---|
| fuze_zerui_xianli | 13/13 | 8/13 | 9/13 |
| hengan_chuanshi_ruiying_b | 13/13 | 6/13 | 7/13 |
| cpic_xinxiangban_2025 | 13/13 | 6/13 | 7/13 |
| nci_ezengfu_youxiang | 13/13 | 7/13 | 7/13 |
| dongfang_zun_4_zhenxiang | 13/13 | 7/13 | 8/13 |

## 字段级分歧明细

仅列出任一模型与 Gold 不一致、或三模型互不一致的行。

| 产品 | 字段 | Gold | 模型A | 模型B | 模型C | 与Gold分歧 |
|---|---|---|---|---|---|---|
| fuze_zerui_xianli | benefit_before_payment_end（交费期满前给付） | {"under_18": "max(累计已交保险费,现金价值)", "adult_before_payment_end": "max(累计已交保险费×年龄给付比例,现金价值)"} | {"under_18": "max(累计已交保险费,现金价值)", "adult_before_payment_end": "max(累计已交保险费×年龄给付比例,现金价值)"} | {"under_18": "max(基本保险金额对应的累计已交保险费, 基本保险金额对应的现金价值)", "adult_before_payment_end": "max(基本保险金额对应的累计已交保险费 × 到达年龄给付比例, 基本保险金额对应的现金价值)"} | {"under_18": "max(累计已交保险费, 现金价值)", "adult_before_payment_end": "max(累计已交保险费×到达年龄对应给付比例, 现金价值)"} | claude_sonnet、claude_opus |
| fuze_zerui_xianli | benefit_after_payment_end（交费期满后给付） | max(累计已交保险费×年龄给付比例,现金价值,当年度保险金额) | max(累计已交保险费×年龄给付比例,现金价值,当年度保险金额) | {"adult_after_payment_end": "max(基本保险金额对应的累计已交保险费 × 到达年龄给付比例, 基本保险金额对应的现金价值, 当年度保险金额)"} | max(累计已交保险费×到达年龄对应给付比例, 现金价值, 当年度保险金额) | claude_sonnet、claude_opus |
| fuze_zerui_xianli | age_benefit_ratio（年龄给付比例） | {"0-17": 1.0, "18-40": 1.6, "41-60": 1.4, "61+": 1.2} | {"0-17": 1.0, "18-40": 1.6, "41-60": 1.4, "61+": 1.2} | {"17周岁(含)以下": 1.0, "18-40周岁": 1.6, "41-60周岁": 1.4, "61周岁(含)以上": 1.2} | {"0-17": 1.0, "18-40": 1.6, "41-60": 1.4, "61+": 1.2} | claude_sonnet |
| fuze_zerui_xianli | effective_sum_assured_definition（有效保险金额定义） | 首个保单年度当年度保险金额=基本保险金额；第二个保单年度起按上一保单年度保险金额×1.0175递增 | 首个保单年度当年度保险金额=基本保险金额；第二个保单年度起按上一保单年度保险金额×1.0175递增 | 本合同首个保单年度内,当年度保险金额为基本保险金额;从第二个保单年度起,年度保险金额每年按基本保险金额的 1.75%以年复利增加,即当年度保险金额等于上一个保单年度保险金额乘以(1+1.75%)。 | 当年度保险金额:本合同首个保单年度内,当年度保险金额为基本保险金额;从第二个保单年度起,年度保险金额每年按基本保险金额的1.75%以年复利增加,即当年度保险金额等于上一保单年度保险金额乘以(1+1.75%)。 | claude_sonnet、claude_opus |
| fuze_zerui_xianli | reduction_rule（减额规则） | 第5个保单周年日（含）后可减保；每个保单年度累计减少部分对应现金价值≤累计已交全部保费20%；减后基本保额不得低于规定最低金额 | 第5个保单周年日（含）后可减保；每个保单年度累计减少部分对应现金价值≤累计已交全部保费20%；减后基本保额不得低于规定最低金额 | 本合同有效且在本合同第五个保单周年日(含)以后可申请减少基本保险金额;每个保单年度累计减少的基本保险金额对应的现金价值之和不得超过已交纳的全部保险费的20%;减少后的基本保险金额不得低于申请时规定的最低金额。 | 本合同有效且自第五个保单周年日(含)以后可书面申请减少基本保险金额;每个保单年度累计减少的基本保险金额对应的现金价值之和不得超过已交纳的全部保险费的20%;减少后的基本保险金额不得低于申请时规定的最低金额。 | claude_sonnet、claude_opus |
| hengan_chuanshi_ruiying_b | benefit_before_payment_end（交费期满前给付） | {"rule": "sum", "part1": "max(已交付保险费×年龄给付比例,初始保险金额对应现金价值)", "part2": "累计红利保险金额对应现金价值", "condition": "交费期满日（含）之前身故，或身故时未满18周岁"} | {"rule": "sum", "part1": "max(已交付保险费×年龄给付比例,初始保险金额对应现金价值)", "part2": "累计红利保险金额对应现金价值", "condition": "交费期满日（含）之前身故，或身故时未满18周岁"} | {"part1": "max(已交付的保险费 × 给付比例, 初始保险金额对应的现金价值)", "part2": "累计红利保险金额对应的现金价值", "combination": "sum"} | {"condition": "若被保险人于交费期满日(含)之前身故,或被保险人身故时未满18周岁", "rule": "sum(part1, part2)", "part1": "max(已交付保险费×身故时年龄对应给付比例, 初始保险金额对应的现金价值)", "part2": "累计红利保险金额对应的现金价值"} | claude_sonnet、claude_opus |
| hengan_chuanshi_ruiying_b | benefit_after_payment_end（交费期满后给付） | {"rule": "sum", "part1": "max(初始保险金额×1.015^(n-1),已交付保险费×年龄给付比例,初始保险金额对应现金价值)", "part2": "max(累计红利保险金额×1.015^(n-1),累计红利保险金额对应现金价值)", "condition": "交费期满日（不含）之后且已满18周岁"} | {"rule": "sum", "part1": "max(初始保险金额×1.015^(n-1),已交付保险费×年龄给付比例,初始保险金额对应现金价值)", "part2": "max(累计红利保险金额×1.015^(n-1),累计红利保险金额对应现金价值)", "condition": "交费期满日（不含）之后且已满18周岁"} | {"part1": "max(初始保险金额 × 1.015^(n-1), 已交付的保险费 × 给付比例, 初始保险金额对应的现金价值)", "part2": "max(累计红利保险金额 × 1.015^(n-1), 累计红利保险金额对应的现金价值)", "combination": "sum"} | {"condition": "若被保险人于交费期满日(不含)之后身故,且被保险人身故时已满18周岁", "rule": "sum(part1, part2)", "part1": "max(初始保险金额×1.015^(n-1), 已交付保险费×身故时年龄对应给付比例, 初始保险金额对应的现金价值)", "part2": "max(累计红利保险金额×1.015^(n-1), 累计红利保险金额对应的现金价值)"} | claude_sonnet、claude_opus |
| hengan_chuanshi_ruiying_b | age_benefit_ratio（年龄给付比例） | {"0-17": 1.0, "18-41": 1.6, "42-61": 1.4, "62+": 1.2} | {"0-17": 1.0, "18-41": 1.6, "42-61": 1.4, "62+": 1.2} | {"0-17周岁": 1.0, "18-41周岁": 1.6, "42-61周岁": 1.4, "62周岁及以上": 1.2} | {"0-17": 1.0, "18-41": 1.6, "42-61": 1.4, "62+": 1.2} | claude_sonnet |
| hengan_chuanshi_ruiying_b | effective_sum_assured_definition（有效保险金额定义） | 初始保险金额+各保单年度累计已分配的红利保险金额 | 初始保险金额+各保单年度累计已分配的红利保险金额 | 有效保险金额为初始保险金额与各保单年度累计已分配的红利保险金额之和,发生变更的以变更后的金额为准;红利保险金额指因分配年度红利所增加的保险金额,已分配的红利保险金额计入以后各年度的红利计算基数。 | 有效保险金额为初始保险金额与各保单年度累计已分配的红利保险金额之和;初始保险金额由投保时约定并在保险单中载明;红利保险金额是指因分配年度红利所增加的保险金额,已分配的红利保险金额计入以后各年度的红利计算基数。 | claude_sonnet、claude_opus |
| hengan_chuanshi_ruiying_b | policy_loan（保单贷款） | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "basis": "现金价值扣除各项欠款后余额"} | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "basis": "现金价值扣除各项欠款后余额"} | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "after_free_look_period": true} | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true} | claude_sonnet、claude_opus |
| hengan_chuanshi_ruiying_b | reduction_rule（减额规则） | 初始保险金额和累计红利保险金额同比例减少；同一保单年度累计减少初始保险金额≤合同生效时初始保险金额20% | 初始保险金额和累计红利保险金额同比例减少；同一保单年度累计减少初始保险金额≤合同生效时初始保险金额20% | 本合同有效期内可书面申请减少保额;同一保单年度内累计申请减少的初始保险金额之和不得超过本合同生效时初始保险金额的20%;减少的初始保险金额和减少后的初始保险金额均需符合规定限额。 | 在本合同有效期内可书面申请减少保额,初始保险金额和累计红利保险金额按相同比例减少;同一保单年度内累计申请减少的初始保险金额之和不得超过本合同生效时初始保险金额的20%;减少的初始保险金额和减少后的初始保险金额均需符合申请时的规定限额。 | claude_sonnet、claude_opus |
| hengan_chuanshi_ruiying_b | dividend_payment_method（红利领取/分配方式） | {"年度红利": "增加红利保险金额并计入以后年度红利计算基数", "终了红利": "合同终止时以现金方式支付"} | {"年度红利": "增加红利保险金额并计入以后年度红利计算基数", "终了红利": "合同终止时以现金方式支付"} | {"年度红利": "增加有效保险金额", "终了红利": "以现金方式支付"} | {"年度红利": "计算红利保险金额,用于增加本合同的有效保险金额", "终了红利": "在本合同终止时以现金方式支付"} | claude_sonnet、claude_opus |
| cpic_xinxiangban_2025 | insured_age_range（投保年龄） | 女性：0周岁（须出生满30日）至75周岁；男性：0周岁（须出生满30日）至71周岁 | 女性：0周岁（须出生满30日）至75周岁；男性：0周岁（须出生满30日）至71周岁 | 女性被保险人:0周岁(须出生满30日)至75周岁;男性被保险人:0周岁(须出生满30日)至71周岁 | 女性被保险人:0周岁(须出生满30日)至75周岁;男性被保险人:0周岁(须出生满30日)至71周岁 | claude_sonnet、claude_opus |
| cpic_xinxiangban_2025 | benefit_before_payment_end（交费期满前给付） | {"under_18": "max(已支付保险费,现金价值)", "adult_before_payment_end": "max(已支付保险费×年龄比例,现金价值)"} | {"under_18": "max(已支付保险费,现金价值)", "adult_before_payment_end": "max(已支付保险费×年龄比例,现金价值)"} | {"under_18": "max(已支付的保险费, 现金价值)", "adult_before_payment_end": "max(已支付的保险费 × 到达年龄比例, 现金价值)"} | {"under_18": "max(已支付的保险费, 现金价值)", "adult_before_payment_end": "max(已支付的保险费×到达年龄对应比例, 现金价值)"} | claude_sonnet、claude_opus |
| cpic_xinxiangban_2025 | benefit_after_payment_end（交费期满后给付） | max(已支付保险费×年龄比例,现金价值,有效保险金额) | max(已支付保险费×年龄比例,现金价值,有效保险金额) | {"adult_after_payment_end": "max(已支付的保险费 × 到达年龄比例, 现金价值, 有效保险金额)"} | max(已支付的保险费×到达年龄对应比例, 现金价值, 有效保险金额) | claude_sonnet、claude_opus |
| cpic_xinxiangban_2025 | age_benefit_ratio（年龄给付比例） | {"<=40": 1.6, "41-60": 1.4, "61+": 1.2} | {"<=40": 1.6, "41-60": 1.4, "61+": 1.2} | {"40周岁及以下": 1.6, "41-60周岁": 1.4, "61周岁及以上": 1.2} | {"<=40": 1.6, "41-60": 1.4, "61+": 1.2} | claude_sonnet |
| cpic_xinxiangban_2025 | effective_sum_assured_definition（有效保险金额定义） | 生效时有效保险金额=基本保险金额；以后每满1个保单年度按前一年度有效保险金额×1.02递增 | 生效时有效保险金额=基本保险金额；以后每满1个保单年度按前一年度有效保险金额×1.02递增 | 本合同生效时的有效保险金额等于基本保险金额;每满1个保单年度,有效保险金额按约定的额度增加一次,增加额度为前一个保单年度有效保险金额的2.0%。 | 本合同生效时的有效保险金额等于基本保险金额;每满1个保单年度,有效保险金额增加一次,增加额度为前一个保单年度有效保险金额的2.0%;若发生基本保险金额减少或约定其他情形导致有效保险金额变更的,有效保险金额按基本保险金额减少比例或约定情形相应调整。 | claude_sonnet、claude_opus |
| cpic_xinxiangban_2025 | policy_loan（保单贷款） | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "after_free_look_period": true, "basis": "现金价值扣除各项欠款后余额"} | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "after_free_look_period": true, "basis": "现金价值扣除各项欠款后余额"} | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "after_free_look_period": true} | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "after_free_look_period": true} | claude_sonnet、claude_opus |
| cpic_xinxiangban_2025 | reduction_rule（减额规则） | 每年累计减少基本保险金额≤合同生效时基本保险金额20%；减保后保费不得低于规定最低标准 | 每年累计减少基本保险金额≤合同生效时基本保险金额20%；减保后保费不得低于规定最低标准 | 在本合同保险期间内可申请减少基本保险金额;每年累计申请减少的基本保险金额之和不得超过本合同生效时基本保险金额的20%;基本保险金额减少后保险费不得低于规定的最低标准。 | 在本合同保险期间内可申请减少基本保险金额;每年累计申请减少的基本保险金额之和不得超过本合同生效时基本保险金额的20%;基本保险金额减少后,本合同保险费不低于规定的最低标准。 | claude_sonnet、claude_opus |
| nci_ezengfu_youxiang | benefit_before_payment_end（交费期满前给付） | {"under_18": "max(实际交纳保险费,现金价值)", "adult_before_payment_end": "max(实际交纳保险费×给付系数,现金价值)"} | {"under_18": "max(实际交纳保险费,现金价值)", "adult_before_payment_end": "max(实际交纳保险费×给付系数,现金价值)"} | {"under_18": "max(实际交纳的保险费, 现金价值)", "adult_before_payment_end": "max(实际交纳的保险费 × 给付系数, 现金价值)"} | {"under_18": "max(实际交纳的保险费, 现金价值)", "adult_before_payment_end": "max(实际交纳的保险费×给付系数, 现金价值)"} | claude_sonnet、claude_opus |
| nci_ezengfu_youxiang | benefit_after_payment_end（交费期满后给付） | max(实际交纳保险费×给付系数,现金价值,基本保险金额×1.02^(n-1)) | max(实际交纳保险费×给付系数,现金价值,基本保险金额×1.02^(n-1)) | {"adult_after_payment_end": "max(实际交纳的保险费 × 给付系数, 现金价值, 基本保险金额 × (1+2%)^(n-1))"} | max(实际交纳的保险费×给付系数, 现金价值, 基本保险金额×(1+2%)^(n-1)) | claude_sonnet、claude_opus |
| nci_ezengfu_youxiang | age_benefit_ratio（年龄给付比例） | {"18-40": 1.6, "41-60": 1.4, "61+": 1.2} | {"18-40": 1.6, "41-60": 1.4, "61+": 1.2} | {"18-40周岁": 1.6, "41-60周岁": 1.4, "61周岁及以上": 1.2} | {"18-41": 1.6, "41-61": 1.4, "61+": 1.2} | claude_sonnet、claude_opus |
| nci_ezengfu_youxiang | effective_sum_assured_definition（有效保险金额定义） | 保险金额根据基本保险金额及第五条保险责任计算；交费期满后的首个保单周年日起第三项按基本保险金额×1.02^(n-1)计算 | 保险金额根据基本保险金额及第五条保险责任计算；交费期满后的首个保单周年日起第三项按基本保险金额×1.02^(n-1)计算 | 本合同保险金额按基本保险金额进行计算确定,即基本保险金额×(1+2%)^(n-1),其中n为被保险人身故或身体全残时的保单年度数。 | null | claude_sonnet、claude_opus |
| nci_ezengfu_youxiang | policy_loan（保单贷款） | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "after_free_look_period": true, "basis": "申请贷款时现金价值的80%扣除各项欠款后的余额"} | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "after_free_look_period": true, "basis": "申请贷款时现金价值的80%扣除各项欠款后的余额"} | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "after_free_look_period": true} | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "after_free_look_period": true} | claude_sonnet、claude_opus |
| nci_ezengfu_youxiang | reduction_rule（减额规则） | 每个保单年度累计减少基本保险金额≤合同生效时基本保险金额20%；减保后保费不得低于最低标准 | 每个保单年度累计减少基本保险金额≤合同生效时基本保险金额20%；减保后保费不得低于最低标准 | 在本合同保险期间内可申请减保,基本保险金额同比例减少;每个保单年度累计申请减少的基本保险金额之和不得超过本合同生效时基本保险金额的20%;减保后保险费不得低于规定的最低标准。 | 在本合同保险期间内可申请减保,经审核同意后基本保险金额同比例减少;每个保单年度累计申请减少的基本保险金额之和不得超过本合同生效时基本保险金额的20%;减保后保险费不得低于规定的最低标准。 | claude_sonnet、claude_opus |
| dongfang_zun_4_zhenxiang | benefit_before_payment_end（交费期满前给付） | {"under_18": "max(已支付保险费,现金价值)", "adult_before_payment_end": "max(已支付保险费×年龄比例,现金价值)"} | {"under_18": "max(已支付保险费,现金价值)", "adult_before_payment_end": "max(已支付保险费×年龄比例,现金价值)"} | {"under_18": "max(已支付的保险费, 现金价值)", "adult_before_payment_end": "max(已支付的保险费 × 到达年龄比例, 现金价值)"} | {"under_18": "max(已支付的保险费, 现金价值)", "adult_before_payment_end": "max(已支付的保险费×到达年龄对应比例, 现金价值)"} | claude_sonnet、claude_opus |
| dongfang_zun_4_zhenxiang | benefit_after_payment_end（交费期满后给付） | max(有效保险金额,已支付保险费×年龄比例,现金价值) | max(有效保险金额,已支付保险费×年龄比例,现金价值) | {"adult_after_payment_end": "max(有效保险金额, 已支付的保险费 × 到达年龄比例, 现金价值)"} | max(有效保险金额, 已支付的保险费×到达年龄对应比例, 现金价值) | claude_sonnet、claude_opus |
| dongfang_zun_4_zhenxiang | age_benefit_ratio（年龄给付比例） | {"<=40": 1.6, "41-60": 1.4, "61+": 1.2} | {"<=40": 1.6, "41-60": 1.4, "61+": 1.2} | {"40周岁(含)以下": 1.6, "41周岁(含)-60周岁(含)": 1.4, "61周岁(含)及以上": 1.2} | {"<=40": 1.6, "41-60": 1.4, "61+": 1.2} | claude_sonnet |
| dongfang_zun_4_zhenxiang | effective_sum_assured_definition（有效保险金额定义） | 第一个保单年度有效保险金额=基本保险金额；第二个保单年度起=上一保单年度有效保险金额×1.02 | 第一个保单年度有效保险金额=基本保险金额；第二个保单年度起=上一保单年度有效保险金额×1.02 | 本合同第一个保单年度的有效保险金额等于本合同的基本保险金额;从第二个保单年度起,各保单年度的有效保险金额在上一保单年度的有效保险金额的基础上增加2%,即当年度的有效保险金额等于上一保单年度的有效保险金额乘以(1+2%)。 | 本合同第一个保单年度的有效保险金额等于基本保险金额;从第二个保单年度起,各保单年度的有效保险金额在上一保单年度有效保险金额的基础上增加2%,即当年度有效保险金额等于上一保单年度有效保险金额乘以(1+2%);若后续申请减保,有效保险金额作相应比例调整。 | claude_sonnet、claude_opus |
| dongfang_zun_4_zhenxiang | policy_loan（保单贷款） | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "basis": "现金价值扣除各项欠款后余额"} | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "basis": "现金价值扣除各项欠款后余额"} | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true} | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true} | claude_sonnet、claude_opus |
| dongfang_zun_4_zhenxiang | reduction_rule（减额规则） | 第5个保单周年日起可减保；每个保单年度累计减少部分对应现金价值≤已支付实际保险费20%；减后基本保险金额不得低于规定最低限额 | 第5个保单周年日起可减保；每个保单年度累计减少部分对应现金价值≤已支付实际保险费20%；减后基本保险金额不得低于规定最低限额 | 自本合同第5个保单周年日开始可申请减少基本保险金额;每个保单年度累计减少的基本保险金额对应的现金价值之和不得超过已支付的实际保险费的20%;减少后的基本保险金额不得低于申请时规定的最低限额。 | 自本合同第5个保单周年日开始可申请减少基本保险金额;每个保单年度累计减少的基本保险金额对应的现金价值之和不得超过已支付的实际保险费的20%;减少后的基本保险金额不得低于申请时规定的最低限额;若已变更为减额交清保险,则不受理减保申请。 | claude_sonnet、claude_opus |

## 重点分歧归因

严格字符比较会把「语义等价但表述不同」判为错误。以下先区分「实质分歧」与「表述/结构差异」，再回到条款证据。

### 实质分歧（真实规则或字段遗漏，需人工复核）

| 产品 | 字段 | 模型 | 问题 |
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

### 表述/结构差异（语义等价，严格比较判为错）

1. **精简归纳 vs 忠实摘录**：Gold 对 `effective_sum_assured_definition`、`reduction_rule` 采用精简归纳；两模型普遍直接摘录完整条款原文。事实一致，仅详略不同。
2. **给付公式措辞**：`benefit_before/after_payment_end` 中，模型在「累计已交保险费」前补足「基本保险金额对应的」、「年龄给付比例」前补足「到达年龄（对应）」等限定词，公式运算层次不变。
3. **JSON 形状**：Sonnet 把部分 `benefit_after_payment_end` 从字符串包成 `{"adult_after_payment_end": …}` 对象；恒安 `benefit_*` 用 `combination` / `rule: sum(…)` 表达「两项之和」，Gold 用 `rule: sum`。
4. **字典键命名**：`age_benefit_ratio` 中 Sonnet 用条款原文边界词（「17周岁(含)以下」）代替规范键名（「0-17」），数值与边界一致。
5. **个别措辞**：太保 `insured_age_range` 模型补写「被保险人」；恒安 `dividend_payment_method` 精简措辞。

### 口径说明

- **严格准确率**（可机器复现）：Sonnet 52.31%、Opus 58.46%。该口径把上述「语义等价差异」一并判错，是**下界**。
- **实质准确率**（人工复核）：Sonnet 90.77%（59/65）、Opus 89.23%（58/65）。13 处实质分歧的逐条清单见 `substantive_review.md`；此数为人工判断，不作机器指标，引用时必须与严格口径同时给出。
- **结论不变**：`codex_gpt5` 的 100% 是 Gold 副本，不代表泛化能力；独立盲测的真实水平由 B/C 体现，且需持续用未参与调优的独立测试集验证。

