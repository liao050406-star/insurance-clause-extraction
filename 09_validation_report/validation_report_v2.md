# 新 Gold Schema 验证报告

生成时间：2026-09-29T16:12:18+08:00

## 汇总

- Gold 行数：65
- 正确：34；错误：1
- 缺失产品：0；当前预测结构未提供字段：30
- 可比较字段准确率：0.9714
- 来源匹配：34/53

## 口径说明

- Gold 文件只读使用，验证器不修改或反填 Gold。
- 当前正式抽取 Schema 与新 Gold 的13字段 Schema 不完全一致。仅对可确定映射的7个字段执行值比较，其余字段记为 `missing_field`。
- `missing_field` 不计入可比较字段准确率，不能据此宣称完整13字段准确率。
- 产品按规范化名称匹配，不使用公司名相似度强行替换不同保险产品。

## 明细

| 产品 | 字段 | 结果 | Gold | 预测 | 来源 |
|---|---|---|---|---|---|
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | insured_age_range | correct | 0周岁（须出生满28日）至70周岁 | 0周岁(须出生满28日)至70周岁 | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | waiting_period | correct | None | None | not_applicable |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | coverage_type | correct | 身故或全残保险金 | 身故或全残保险金 | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | benefit_before_payment_end | missing_field | {"under_18": "max(累计已交保险费,现金价值)", "adult_before_payment_end": "max(累计已交保险费×年龄给付比例,现金价值)"} | None | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | benefit_after_payment_end | missing_field | max(累计已交保险费×年龄给付比例,现金价值,当年度保险金额) | None | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | age_benefit_ratio | missing_field | {"0-17": 1.0, "18-40": 1.6, "41-60": 1.4, "61+": 1.2} | None | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | guaranteed_growth_rate | correct | 0.0175 | 0.0175 | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | effective_sum_assured_definition | missing_field | 首个保单年度当年度保险金额=基本保险金额；第二个保单年度起按上一保单年度保险金额×1.0175递增 | None | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | policy_loan | missing_field | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "after_free_look_period": true} | None | matched_normalized |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | reduction_rule | missing_field | 第5个保单周年日（含）后可减保；每个保单年度累计减少部分对应现金价值≤累计已交全部保费20%；减后基本保额不得低于规定最低金额 | None | mismatched |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | dividend_guarantee | correct | False | False | matched_strict |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | dividend_type | correct | None | None | not_applicable |
| 富泽泽瑞一生（献礼版）终身寿险（分红型） | dividend_payment_method | correct | ["现金领取", "累积生息", "购买交清增额保险"] | ["现金领取", "累积生息", "购买交清增额保险"] | mismatched |
| 恒安标准传世瑞盈B款终身寿险（分红型） | insured_age_range | correct | None | None | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | waiting_period | correct | 90 | 90 | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | coverage_type | correct | 身故保险金 | 身故保险金 | matched_normalized |
| 恒安标准传世瑞盈B款终身寿险（分红型） | benefit_before_payment_end | missing_field | {"rule": "sum", "part1": "max(已交付保险费×年龄给付比例,初始保险金额对应现金价值)", "part2": "累计红利保险金额对应现金价值", "condition": "交费期满日（含）之前身故，或身故时未满18周岁"} | None | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | benefit_after_payment_end | missing_field | {"rule": "sum", "part1": "max(初始保险金额×1.015^(n-1),已交付保险费×年龄给付比例,初始保险金额对应现金价值)", "part2": "max(累计红利保险金额×1.015^(n-1),累计红利保险金额对应现金价值)", "condition": "交费期满日（不含）之后且已满18周岁"} | None | mismatched |
| 恒安标准传世瑞盈B款终身寿险（分红型） | age_benefit_ratio | missing_field | {"0-17": 1.0, "18-41": 1.6, "42-61": 1.4, "62+": 1.2} | None | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | guaranteed_growth_rate | incorrect | 0.015 | None | matched_normalized |
| 恒安标准传世瑞盈B款终身寿险（分红型） | effective_sum_assured_definition | missing_field | 初始保险金额+各保单年度累计已分配的红利保险金额 | None | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | policy_loan | missing_field | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "basis": "现金价值扣除各项欠款后余额"} | None | mismatched |
| 恒安标准传世瑞盈B款终身寿险（分红型） | reduction_rule | missing_field | 初始保险金额和累计红利保险金额同比例减少；同一保单年度累计减少初始保险金额≤合同生效时初始保险金额20% | None | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | dividend_guarantee | correct | False | False | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | dividend_type | correct | ["年度红利", "终了红利"] | ["年度红利", "终了红利"] | matched_strict |
| 恒安标准传世瑞盈B款终身寿险（分红型） | dividend_payment_method | correct | {"年度红利": "增加红利保险金额并计入以后年度红利计算基数", "终了红利": "合同终止时以现金方式支付"} | {"年度红利": "增加红利保险金额并计入以后年度红利计算基数", "终了红利": "合同终止时以现金方式支付"} | matched_strict |
| 太保鑫相伴（2025）终身寿险 | insured_age_range | correct | 女性：0周岁（须出生满30日）至75周岁；男性：0周岁（须出生满30日）至71周岁 | 女性0周岁(须出生满30日)至75周岁；男性0周岁(须出生满30日)至71周岁 | matched_strict |
| 太保鑫相伴（2025）终身寿险 | waiting_period | correct | 90 | 90 | matched_strict |
| 太保鑫相伴（2025）终身寿险 | coverage_type | correct | ["身故保险金", "特定客运交通工具意外身故保险金"] | ["身故保险金", "特定客运交通工具意外身故保险金"] | mismatched |
| 太保鑫相伴（2025）终身寿险 | benefit_before_payment_end | missing_field | {"under_18": "max(已支付保险费,现金价值)", "adult_before_payment_end": "max(已支付保险费×年龄比例,现金价值)"} | None | mismatched |
| 太保鑫相伴（2025）终身寿险 | benefit_after_payment_end | missing_field | max(已支付保险费×年龄比例,现金价值,有效保险金额) | None | mismatched |
| 太保鑫相伴（2025）终身寿险 | age_benefit_ratio | missing_field | {"<=40": 1.6, "41-60": 1.4, "61+": 1.2} | None | matched_strict |
| 太保鑫相伴（2025）终身寿险 | guaranteed_growth_rate | correct | 0.02 | 0.02 | mismatched |
| 太保鑫相伴（2025）终身寿险 | effective_sum_assured_definition | missing_field | 生效时有效保险金额=基本保险金额；以后每满1个保单年度按前一年度有效保险金额×1.02递增 | None | mismatched |
| 太保鑫相伴（2025）终身寿险 | policy_loan | missing_field | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "after_free_look_period": true, "basis": "现金价值扣除各项欠款后余额"} | None | matched_normalized |
| 太保鑫相伴（2025）终身寿险 | reduction_rule | missing_field | 每年累计减少基本保险金额≤合同生效时基本保险金额20%；减保后保费不得低于规定最低标准 | None | matched_strict |
| 太保鑫相伴（2025）终身寿险 | dividend_guarantee | correct | None | None | not_applicable |
| 太保鑫相伴（2025）终身寿险 | dividend_type | correct | None | None | not_applicable |
| 太保鑫相伴（2025）终身寿险 | dividend_payment_method | correct | None | None | not_applicable |
| 新华人寿E增福优享版终身寿险（互联网） | insured_age_range | correct | 0周岁（须出生满30日）至70周岁 | 0周岁(须出生满30日)至70周岁 | mismatched |
| 新华人寿E增福优享版终身寿险（互联网） | waiting_period | correct | 180 | 180 | mismatched |
| 新华人寿E增福优享版终身寿险（互联网） | coverage_type | correct | 身故或身体全残保险金 | 身故或身体全残保险金 | matched_strict |
| 新华人寿E增福优享版终身寿险（互联网） | benefit_before_payment_end | missing_field | {"under_18": "max(实际交纳保险费,现金价值)", "adult_before_payment_end": "max(实际交纳保险费×给付系数,现金价值)"} | None | matched_strict |
| 新华人寿E增福优享版终身寿险（互联网） | benefit_after_payment_end | missing_field | max(实际交纳保险费×给付系数,现金价值,基本保险金额×1.02^(n-1)) | None | matched_normalized |
| 新华人寿E增福优享版终身寿险（互联网） | age_benefit_ratio | missing_field | {"18-40": 1.6, "41-60": 1.4, "61+": 1.2} | None | mismatched |
| 新华人寿E增福优享版终身寿险（互联网） | guaranteed_growth_rate | correct | 0.02 | 0.02 | matched_normalized |
| 新华人寿E增福优享版终身寿险（互联网） | effective_sum_assured_definition | missing_field | 保险金额根据基本保险金额及第五条保险责任计算；交费期满后的首个保单周年日起第三项按基本保险金额×1.02^(n-1)计算 | None | matched_strict |
| 新华人寿E增福优享版终身寿险（互联网） | policy_loan | missing_field | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "after_free_look_period": true, "basis": "申请贷款时现金价值的80%扣除各项欠款后的余额"} | None | mismatched |
| 新华人寿E增福优享版终身寿险（互联网） | reduction_rule | missing_field | 每个保单年度累计减少基本保险金额≤合同生效时基本保险金额20%；减保后保费不得低于最低标准 | None | mismatched |
| 新华人寿E增福优享版终身寿险（互联网） | dividend_guarantee | correct | None | None | not_applicable |
| 新华人寿E增福优享版终身寿险（互联网） | dividend_type | correct | None | None | not_applicable |
| 新华人寿E增福优享版终身寿险（互联网） | dividend_payment_method | correct | None | None | not_applicable |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | insured_age_range | correct | 0周岁（须出生满28日）至75周岁 | 0周岁（须出生满28日）至75周岁 | mismatched |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | waiting_period | correct | None | None | not_applicable |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | coverage_type | correct | 身故或全残保险金 | 身故或全残保险金 | matched_strict |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | benefit_before_payment_end | missing_field | {"under_18": "max(已支付保险费,现金价值)", "adult_before_payment_end": "max(已支付保险费×年龄比例,现金价值)"} | None | mismatched |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | benefit_after_payment_end | missing_field | max(有效保险金额,已支付保险费×年龄比例,现金价值) | None | mismatched |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | age_benefit_ratio | missing_field | {"<=40": 1.6, "41-60": 1.4, "61+": 1.2} | None | mismatched |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | guaranteed_growth_rate | correct | 0.02 | 0.02 | matched_normalized |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | effective_sum_assured_definition | missing_field | 第一个保单年度有效保险金额=基本保险金额；第二个保单年度起=上一保单年度有效保险金额×1.02 | None | matched_strict |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | policy_loan | missing_field | {"max_cash_value_ratio": 0.8, "max_term_months": 6, "insured_consent_required": true, "basis": "现金价值扣除各项欠款后余额"} | None | matched_normalized |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | reduction_rule | missing_field | 第5个保单周年日起可减保；每个保单年度累计减少部分对应现金价值≤已支付实际保险费20%；减后基本保险金额不得低于规定最低限额 | None | mismatched |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | dividend_guarantee | correct | None | None | not_applicable |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | dividend_type | correct | None | None | not_applicable |
| 东方嘉富东方尊4.0（臻享版）终身寿险 | dividend_payment_method | correct | None | None | not_applicable |

## 限制

- 新 Gold 中的太保产品为“太保鑫相伴（2025）终身寿险”，当前预测目录中的太保产品为“太保盛世鸿运（恒赢版）终身寿险（分红型）”，两者不是同一产品。
- benefit、保单贷款、减保和有效保险金额定义等字段需要按新 Schema 重新抽取，不能从 Gold 复制生成预测。
