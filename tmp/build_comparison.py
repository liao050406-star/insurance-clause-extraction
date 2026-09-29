from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "07_Pydantic校验" / "validation" / "validation_results.json"
OUTPUT = ROOT / "10_comparison_xlsx" / "三款增额终身寿险字段对比.xlsx"

FIELD_META = [
    ("insured_age_range", "投保年龄范围", "周岁"),
    ("benefit_age_band_coverage", "给付年龄分段覆盖", ""),
    ("hesitation_period_days", "犹豫期", "天"),
    ("insurance_period", "保险期间", ""),
    ("waiting_period_days", "等待期", "天"),
    ("coverage_scope", "保障范围", ""),
    ("fixed_insured_amount_annual_growth_rate", "固定保额年增长率", "比例"),
    ("insurance_amount_growth_mechanism", "保险金额增长机制", ""),
    ("is_participating", "是否分红", ""),
    ("grace_period_days", "宽限期", "天"),
    ("policy_loan_max_ratio", "保单贷款最高比例", "比例"),
    ("policy_loan_max_term_months", "保单贷款最长期限", "月"),
]


def display(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "是" if value else "否"
    return value


def source_label(item):
    values = []
    for source in item.get("source_details", []):
        clause = source.get("source_clause")
        if not clause:
            continue
        page = source.get("source_page")
        label = f"第{clause}条" + (f"（PDF第{page}页）" if page else "")
        if label not in values:
            values.append(label)
    return "；".join(values) or "条款未载明"


payload = json.loads(INPUT.read_text(encoding="utf-8"))
products = list(dict.fromkeys(item["product_name"] for item in payload["results"]))
by_key = {(item["product_name"], item["field_name"]): item for item in payload["results"]}
field_labels = {code: label for code, label, _ in FIELD_META}

wb = Workbook()
ws = wb.active
ws.title = "字段对比"
detail = wb.create_sheet("校验明细")

navy = "1F4E78"
light = "F5F7FA"
green = "E2F0D9"
white = "FFFFFF"
gray = "666666"
thin = Side(style="thin", color="D9E1E8")

ws.sheet_view.showGridLines = False
ws.merge_cells("A1:H1")
ws["A1"] = "三款增额终身寿险字段对比"
ws["A1"].font = Font(name="Arial", size=16, bold=True, color="1F1F1F")
ws.merge_cells("A2:H2")
ws["A2"] = "数值来自抽取结果；条款出处已通过 Gold 原文、哈希及字符区间校验。null 表示条款未载明或不适用。"
ws["A2"].font = Font(name="Arial", size=10, italic=True, color=gray)

headers = ["字段", "单位"]
for product in products:
    headers += [product, "条款出处"]
for col, value in enumerate(headers, 1):
    cell = ws.cell(4, col, value)
    cell.fill = PatternFill("solid", fgColor=navy)
    cell.font = Font(name="Arial", size=10, bold=True, color=white)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)

for row, (field, label, unit) in enumerate(FIELD_META, 5):
    ws.cell(row, 1, label)
    ws.cell(row, 2, unit)
    col = 3
    for product in products:
        item = by_key[(product, field)]
        ws.cell(row, col, display(item["predicted_value"]))
        ws.cell(row, col + 1, source_label(item))
        col += 2
    for cell in ws[row]:
        cell.font = Font(name="Arial", size=10, bold=(cell.column == 1), color="222222")
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        cell.border = Border(bottom=thin)
        if row % 2 == 1:
            cell.fill = PatternFill("solid", fgColor=light)

for row in range(5, 17):
    for col in (3, 5, 7):
        if row in (11, 15) and isinstance(ws.cell(row, col).value, (int, float)):
            ws.cell(row, col).number_format = "0.00%" if row == 11 else "0%"
ws.column_dimensions["A"].width = 24
ws.column_dimensions["B"].width = 10
for col in ("C", "E", "G"):
    ws.column_dimensions[col].width = 28
for col in ("D", "F", "H"):
    ws.column_dimensions[col].width = 21
ws.row_dimensions[4].height = 42
for row in range(5, 17):
    ws.row_dimensions[row].height = 42
ws.freeze_panes = "C5"
ws.auto_filter.ref = "A4:H16"
ws.merge_cells("A18:H18")
ws["A18"] = "数据来源：三款产品保险条款 PDF；字段值来自 06_result_json，条款出处来自已通过原文校验的验证结果。"
ws.merge_cells("A19:H19")
ws["A19"] = "生成时间：2026-09-22（Asia/Shanghai）"
ws.merge_cells("A20:H20")
ws["A20"] = "说明：本表仅用于条款信息整理与课程作业，不构成保险建议、产品推荐或产品排名。"
for row in range(18, 21):
    ws.cell(row, 1).font = Font(name="Arial", size=9, italic=True, color=gray)
    ws.cell(row, 1).alignment = Alignment(vertical="top", wrap_text=True)

detail.sheet_view.showGridLines = False
detail.merge_cells("A1:I1")
detail["A1"] = "字段级校验与条款追溯"
detail["A1"].font = Font(name="Arial", size=16, bold=True, color="1F1F1F")
detail.merge_cells("A2:I2")
summary = payload["summary"]
detail["A2"] = f"共 {summary['gold_fields']} 个字段；正确 {summary['correct']}；准确率 {summary['accuracy']:.2%}。"
detail["A2"].font = Font(name="Arial", size=10, italic=True, color=gray)
detail_headers = ["产品", "字段代码", "字段名称", "预测值", "校验结果", "条款号", "PDF页码", "原文摘录", "原文匹配"]
for col, value in enumerate(detail_headers, 1):
    cell = detail.cell(4, col, value)
    cell.fill = PatternFill("solid", fgColor=navy)
    cell.font = Font(name="Arial", size=10, bold=True, color=white)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)

for row, item in enumerate(payload["results"], 5):
    sources = [x for x in item.get("source_details", []) if x.get("source_clause")]
    values = [
        item["product_name"], item["field_name"], field_labels.get(item["field_name"], item["field_name"]),
        display(item["predicted_value"]), item["result"],
        "；".join(str(x.get("source_clause", "")) for x in sources),
        "；".join(str(x.get("source_page", "")) for x in sources),
        "\n".join(str(x.get("source_text", "")) for x in sources) or "条款未载明",
        item["source_result"],
    ]
    for col, value in enumerate(values, 1):
        cell = detail.cell(row, col, value)
        cell.font = Font(name="Arial", size=10, color="222222")
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        cell.border = Border(bottom=thin)
    detail.cell(row, 5).fill = PatternFill("solid", fgColor=green)

widths = {"A": 30, "B": 35, "C": 22, "D": 25, "E": 13, "F": 13, "G": 11, "H": 72, "I": 19}
for col, width in widths.items():
    detail.column_dimensions[col].width = width
detail.row_dimensions[4].height = 30
for row in range(5, 41):
    detail.row_dimensions[row].height = 54
detail.freeze_panes = "D5"
detail.auto_filter.ref = "A4:I40"

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUTPUT)

# Reopen the exported workbook and assert the deliverable's critical structure.
check = load_workbook(OUTPUT, data_only=False)
assert check.sheetnames == ["字段对比", "校验明细"]
assert check["字段对比"].max_row == 20 and check["字段对比"].max_column == 8
assert check["校验明细"].max_row == 40 and check["校验明细"].max_column == 9
assert check["校验明细"]["E5"].value == "correct"
assert all(
    not (isinstance(cell.value, str) and cell.value.startswith(("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A")))
    for sheet in check.worksheets
    for row in sheet.iter_rows()
    for cell in row
)
print(json.dumps({"output": str(OUTPUT), "sheets": check.sheetnames, "comparison_rows": 12, "detail_rows": 36}, ensure_ascii=False))
