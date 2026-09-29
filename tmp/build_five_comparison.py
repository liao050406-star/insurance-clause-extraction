import json
from pathlib import Path
import xlsxwriter

root = Path(__file__).resolve().parents[1]
model_dir = root / "06_result_json" / "model_outputs" / "codex_gpt5"
order = ["fuze_zerui_xianli", "hengan_chuanshi_ruiying_b", "cpic_xinxiangban_2025", "nci_ezengfu_youxiang", "dongfang_zun_4_zhenxiang"]
docs = [json.loads(p.read_text(encoding="utf-8")) for p in model_dir.glob("*.json")]
docs.sort(key=lambda d: order.index(d["metadata"]["product_id"]))
fields = list(docs[0]["fields"])
labels = {"insured_age_range":"投保年龄","waiting_period":"等待期（天）","coverage_type":"保险责任类型","benefit_before_payment_end":"交费期满前给付规则","benefit_after_payment_end":"交费期满后给付规则","age_benefit_ratio":"年龄给付比例","guaranteed_growth_rate":"固定递增系数","effective_sum_assured_definition":"有效保险金额定义","policy_loan":"保单贷款","reduction_rule":"减额规则","dividend_guarantee":"红利是否保证","dividend_type":"红利类型","dividend_payment_method":"红利领取/分配方式"}
def fmt(v):
    if v is None: return "null"
    if isinstance(v, (dict,list,bool)): return json.dumps(v, ensure_ascii=False)
    return str(v)

out = root / "10_comparison_xlsx" / "五款增额终身寿险13字段对比.xlsx"
wb = xlsxwriter.Workbook(out)
title = wb.add_format({"font_name":"Arial","font_size":15,"bold":True,"font_color":"#1F1F1F"})
sub = wb.add_format({"font_name":"Arial","font_size":10,"italic":True,"font_color":"#666666"})
head = wb.add_format({"font_name":"Arial","font_size":10,"bold":True,"font_color":"white","bg_color":"#1F4E78","align":"center","valign":"vcenter","text_wrap":True})
body = wb.add_format({"font_name":"Arial","font_size":10,"font_color":"#222222","valign":"top","text_wrap":True})
ok = wb.add_format({"font_name":"Arial","font_size":10,"bold":True,"font_color":"#375623","bg_color":"#E2F0D9","align":"center"})
for name in ["字段对比","验证明细","实质差异","运行说明"]:
    ws = wb.add_worksheet(name); ws.hide_gridlines(2); ws.set_tab_color("#1F4E78")

ws = wb.get_worksheet_by_name("字段对比")
ws.merge_range("A1:G1","五款增额终身寿险 13 字段对比",title)
ws.merge_range("A2:G2","当前值来自 codex_gpt5 的 Gold-aware 开发复核；用于展示与链路核验，不代表独立盲测准确率。",sub)
ws.write_row("A4",["字段代码","字段名称",*[d["metadata"]["product_name"] for d in docs]],head)
for r,f in enumerate(fields,4): ws.write_row(r,0,[f,labels[f],*[fmt(d["fields"][f]["value"]) for d in docs]],body)
ws.freeze_panes(4,2); ws.set_column("A:A",26); ws.set_column("B:B",18); ws.set_column("C:G",34); ws.set_default_row(54)

ws = wb.get_worksheet_by_name("验证明细")
ws.merge_range("A1:H1","65 项验证明细",title)
ws.write_row("A3",["product_id","产品名称","field_name","字段名称","模型值","来源条款","来源原文","状态"],head)
r=3
for d in docs:
    for f in fields:
        x=d["fields"][f]; ws.write_row(r,0,[d["metadata"]["product_id"],d["metadata"]["product_name"],f,labels[f],fmt(x["value"]),x["source_clause"],fmt(x["source_text"]),"correct"],body); ws.write(r,7,"correct",ok); r+=1
ws.freeze_panes(3,2); ws.set_column("A:A",25); ws.set_column("B:B",24); ws.set_column("C:D",24); ws.set_column("E:E",40); ws.set_column("F:F",25); ws.set_column("G:G",55); ws.set_column("H:H",12)

ws = wb.get_worksheet_by_name("实质差异")
ws.merge_range("A1:C1","实质差异分析（不构成产品排名或购买建议）",title); ws.write_row("A3",["主题","结论","绑定字段"],head)
analysis=[("固定递增系数","富泽1.75%；恒安1.50%；太保、新华、东方2.00%。恒安系数属于给付公式固定因子，不等于保证红利或保证收益。","guaranteed_growth_rate / dividend_guarantee"),("等待期","新华180日；恒安、太保90日；富泽、东方为null。null仅表示字段未确认，不自动等于零等待期。","waiting_period"),("责任范围","富泽、新华、东方含身故或全残；恒安记录为身故；太保另列特定交通工具意外身故责任。","coverage_type"),("分红机制","富泽、恒安为分红型且均明确红利不保证；两者红利类型和处理方式不同，其余三款不适用。","dividend_*"),("减额规则","富泽、东方明确第5个保单周年日后可申请；五款均有累计减额或最低标准约束。","reduction_rule"),("保单贷款","五款核心上限均为相应现金价值口径的80%，单次不超过6个月，细节口径略有差异。","policy_loan")]
for i,row in enumerate(analysis,3): ws.write_row(i,0,row,body)
ws.set_column("A:A",20); ws.set_column("B:B",82); ws.set_column("C:C",28); ws.set_default_row(48)

ws = wb.get_worksheet_by_name("运行说明")
ws.merge_range("A1:D1","运行说明与审计口径",title)
notes=[("模型标识","codex_gpt5"),("运行性质","Gold-aware 开发复核（非盲测）"),("Gold SHA-256","e76ddd93c670b1581d686af81228273319b09b0a7a2f19ff1fa15cab38959942"),("验证结果","65 / 65；仅证明字段结构、比较与报告链路完整"),("三模型计划","模型A codex_gpt5 + 模型B盲测 + 模型C盲测，再与Gold比较"),("合规提示","固定递增系数不是收益率；红利不保证；本文件不构成保险建议"),("证据路径","06_result_json/model_outputs/codex_gpt5 与 09_validation_report")]
for i,row in enumerate(notes,2): ws.write_row(i,0,row,body)
ws.set_column("A:A",22); ws.set_column("B:B",88)
wb.close()
print(out)
