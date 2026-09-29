# claude_sonnet 13字段验证报告

- Gold SHA-256：`e76ddd93c670b1581d686af81228273319b09b0a7a2f19ff1fa15cab38959942`
- 总项数：65
- 正确 / 错误 / 缺失：34 / 31 / 0
- 准确率：52.31%
- 独立盲测：是

## 最弱三个字段

- `age_benefit_ratio`：0/5 正确
- `benefit_after_payment_end`：0/5 正确
- `benefit_before_payment_end`：0/5 正确

## 产品汇总

| product_id | 正确 | 错误 | 缺失 |
|---|---:|---:|---:|
| fuze_zerui_xianli | 8 | 5 | 0 |
| hengan_chuanshi_ruiying_b | 6 | 7 | 0 |
| cpic_xinxiangban_2025 | 6 | 7 | 0 |
| nci_ezengfu_youxiang | 7 | 6 | 0 |
| dongfang_zun_4_zhenxiang | 7 | 6 | 0 |
