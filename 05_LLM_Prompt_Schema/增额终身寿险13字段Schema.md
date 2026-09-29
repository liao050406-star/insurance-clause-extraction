# 增额终身寿险 13 字段评估 Schema

本 Schema 用于五款产品的统一抽取、Gold 验证和多模型比较。每份条款输出一个 JSON 对象，字段名固定，不得增删。所有值只能来自当前条款正文。

## 输出结构

```json
{
  "metadata": {
    "model_id": "实际模型短名",
    "product_id": "稳定产品标识",
    "product_name": "条款标题中的产品名称",
    "prompt_version": "v3_gold_schema",
    "independent_blind_test": true
  },
  "fields": {
    "insured_age_range": {"value": null, "source_clause": null, "source_text": null},
    "waiting_period": {"value": null, "source_clause": null, "source_text": null},
    "coverage_type": {"value": null, "source_clause": null, "source_text": null},
    "benefit_before_payment_end": {"value": null, "source_clause": null, "source_text": null},
    "benefit_after_payment_end": {"value": null, "source_clause": null, "source_text": null},
    "age_benefit_ratio": {"value": null, "source_clause": null, "source_text": null},
    "guaranteed_growth_rate": {"value": null, "source_clause": null, "source_text": null},
    "effective_sum_assured_definition": {"value": null, "source_clause": null, "source_text": null},
    "policy_loan": {"value": null, "source_clause": null, "source_text": null},
    "reduction_rule": {"value": null, "source_clause": null, "source_text": null},
    "dividend_guarantee": {"value": null, "source_clause": null, "source_text": null},
    "dividend_type": {"value": null, "source_clause": null, "source_text": null},
    "dividend_payment_method": {"value": null, "source_clause": null, "source_text": null}
  }
}
```

## 通用规则

1. 条款未载明或字段不适用时，`value` 填 `null`，对应 `source_clause` 和 `source_text` 也填 `null`。
2. `source_text` 必须是直接支持字段值的连续原文，不得改写或拼接多个不连续片段。
3. 比例使用小数，例如 2% 写为 `0.02`，160% 写为 `1.6`。
4. 等待期使用整数天数；条款未设置等待期填 `null`。
5. 数组保持条款列示顺序；对象键名严格采用本 Schema 规定的名称。
6. 不得从产品名称、行业惯例、其他产品、样例或 Gold 推测字段值。

## 字段定义

### insured_age_range

- 类型：字符串或 `null`。
- 内容：条款明确载明的被保险人投保年龄上下限；男女不同时分别列示。
- 仅写“符合我们的要求”而没有数字范围时填 `null`。

### waiting_period

- 类型：整数或 `null`。
- 内容：疾病或非意外原因导致保险事故时适用的等待日数。
- 条款没有等待期规则时填 `null`。

### coverage_type

- 类型：字符串、字符串数组或 `null`。
- 内容：逐字记录保险责任小标题。只有一项时用字符串，多项时用数组。

### benefit_before_payment_end

- 类型：对象、字符串或 `null`。
- 内容：交费期满相关分界日前的主保险责任计算公式。
- 常用对象键：`under_18`、`adult_before_payment_end`；复杂产品可使用 `rule`、`part1`、`part2`、`condition`。
- 公式使用 `max(...)`、`sum`、乘号 `×` 等统一表达，但不得改变原计算层次。

### benefit_after_payment_end

- 类型：对象、字符串或 `null`。
- 内容：交费期满相关分界日及以后的主保险责任计算公式。
- “先分别取大再相加”必须保留为对象，不能压缩为一次 `max(...)`。

### age_benefit_ratio

- 类型：对象或 `null`。
- 内容：到达年龄对应的已交保费给付比例完整分段。
- 键使用条款边界，例如 `0-17`、`18-40`、`<=40`、`61+`。

### guaranteed_growth_rate

- 类型：小数或 `null`。
- 内容：条款明确写入保证给付公式或有效保险金额公式的年度复利增长系数。
- 它不是收益率、预定利率或红利水平。
- 若固定系数仅作用于初始保险金额或保证给付部分，仍记录该明确保证系数；红利金额本身的不确定性由分红字段表达。

### effective_sum_assured_definition

- 类型：字符串或 `null`。
- 内容：有效保险金额、当年度保险金额或相关保证金额的条款定义及递增方式。

### policy_loan

- 类型：对象或 `null`。
- 支持键：`max_cash_value_ratio`、`max_term_months`、`insured_consent_required`、`after_free_look_period`、`basis`。
- 只保留条款明确载明的键，不明确的键省略。

### reduction_rule

- 类型：字符串或 `null`。
- 内容：减保起始条件、年度上限计算基数及减保后的最低限制。

### dividend_guarantee

- 类型：布尔值或 `null`。
- 分红型且条款明确红利不保证时填 `false`；非分红产品填 `null`。

### dividend_type

- 类型：字符串数组或 `null`。
- 内容：条款明确区分的红利类型，例如年度红利、终了红利；没有明确分类或非分红产品填 `null`。

### dividend_payment_method

- 类型：字符串数组、对象或 `null`。
- 内容：红利领取或实现方式。简单并列方式用数组；不同红利类型对应不同处理方法时用对象。
