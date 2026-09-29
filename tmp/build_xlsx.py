"""Build the three-model (+ Gold) four-way comparison workbook.

Reuses the shared comparison logic (norm / SUBSTANTIVE) from
build_model_comparison so the xlsx numbers match the markdown report exactly.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import xlsxwriter

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tmp"))
from build_model_comparison import SUBSTANTIVE, norm, parse_value, FIELDS, LABELS  # noqa: E402

GOLD = ROOT / "08_gold_csv对比" / "gold.csv"
MODELS = [("codex_gpt5", "模型A", False), ("claude_sonnet", "模型B", True), ("claude_opus", "模型C", True)]
PRODUCT_ORDER = ["fuze_zerui_xianli", "hengan_chuanshi_ruiying_b", "cpic_xinxiangban_2025",
                 "nci_ezengfu_youxiang", "dongfang_zun_4_zhenxiang"]
STATUS_LABEL = {"correct": "正确", "equivalent": "语义等价", "substantive": "实质分歧", "missing": "缺失"}


def load_model(model_id: str) -> dict:
    d = ROOT / "06_result_json" / "model_outputs" / model_id
    out = {}
    for p in sorted(d.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        out[data["metadata"]["product_id"]] = data["fields"]
    return out


def fmt(v):
    if v is None:
        return "null"
    if isinstance(v, (dict, list, bool)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def main() -> None:
    gold_sha = hashlib.sha256(GOLD.read_bytes()).hexdigest()
    rows = list(csv.DictReader(GOLD.open("r", encoding="utf-8-sig", newline="")))
    gold = {(r["product_id"], r["field_name"]): parse_value(r["gold_value"]) for r in rows}
    product_names = {r["product_id"]: r["product_name"] for r in rows}
    models = {mid: load_model(mid) for mid, _, _ in MODELS}

    out = ROOT / "10_comparison_xlsx" / "三模型四方对比.xlsx"
    wb = xlsxwriter.Workbook(out)
    title = wb.add_format({"font_name": "Arial", "font_size": 15, "bold": True, "font_color": "#0b1f3a"})
    sub = wb.add_format({"font_name": "Arial", "font_size": 10, "italic": True, "font_color": "#5d6b78"})
    head = wb.add_format({"font_name": "Arial", "font_size": 10, "bold": True, "font_color": "white", "bg_color": "#1f4e78", "align": "center", "valign": "vcenter", "text_wrap": True})
    body = wb.add_format({"font_name": "Arial", "font_size": 9.5, "font_color": "#222222", "valign": "top", "text_wrap": True})
    goldcell = wb.add_format({"font_name": "Arial", "font_size": 9.5, "font_color": "#222222", "valign": "top", "text_wrap": True, "bg_color": "#f4f6f7"})
    ok = wb.add_format({"font_name": "Arial", "font_size": 9.5, "font_color": "#0c684b", "bg_color": "#e2f0d9", "valign": "top"})
    eqv = wb.add_format({"font_name": "Arial", "font_size": 9.5, "font_color": "#7b5413", "bg_color": "#fff3cd", "valign": "top"})
    bad = wb.add_format({"font_name": "Arial", "font_size": 9.5, "font_color": "#a14d2e", "bg_color": "#f8d7d4", "valign": "top"})
    stfmt = {"correct": ok, "equivalent": eqv, "substantive": bad}

    # ---- 总览 ----
    ws = wb.add_worksheet("总览")
    ws.hide_gridlines(2)
    ws.merge_range("A1:E1", "三模型 + Gold 四方对比总览", title)
    ws.merge_range("A2:E2", "严格准确率为机器可复现口径（下界）；实质准确率为人工复核口径（把语义等价差异单列）。", sub)
    ws.write_row("A4", ["模型", "严格正确", "语义等价", "实质分歧", "严格/实质准确率"], head)
    r = 4
    for mid, label, blind in MODELS:
        preds = models[mid]
        c = Counter()
        for rr in rows:
            pid, f = rr["product_id"], rr["field_name"]
            p = preds.get(pid, {}).get(f)
            if p is None:
                c["missing"] += 1
            elif norm(p.get("value")) == norm(gold[(pid, f)]):
                c["correct"] += 1
            elif (pid, f, mid) in SUBSTANTIVE:
                c["substantive"] += 1
            else:
                c["equivalent"] += 1
        total = len(rows)
        acc = c["correct"] / total
        sub_acc = (c["correct"] + c["equivalent"]) / total
        tag = f"{label}（{'盲测' if blind else '开发复核·非盲测'}）"
        ws.write_row(r, 0, [f"{mid} {tag}", c["correct"], c["equivalent"], c["substantive"],
                            f"严格 {acc:.2%} / 实质 {sub_acc:.2%}"], body)
        r += 1
    ws.write_row(r + 1, 0, [f"Gold SHA-256", gold_sha, "", "", "共 65 行（5 款 × 13 字段）"], body)
    ws.set_column("A:A", 34); ws.set_column("B:D", 12); ws.set_column("E:E", 30)

    # ---- 四方对比（65 行明细） ----
    ws = wb.add_worksheet("四方对比")
    ws.hide_gridlines(2)
    ws.merge_range("A1:H1", "65 项四方对比明细", title)
    ws.write_row("A3", ["product_id", "产品", "字段", "Gold", "模型A", "模型B", "模型C", "状态（vs Gold）"], head)
    r = 3
    for pid in PRODUCT_ORDER:
        for f in FIELDS:
            vals = [fmt(models[mid].get(pid, {}).get(f, {}).get("value")) for mid, _, _ in MODELS]
            statuses = []
            for mid, _, _ in MODELS:
                p = models[mid].get(pid, {}).get(f)
                if p is None:
                    statuses.append("missing")
                elif norm(p.get("value")) == norm(gold[(pid, f)]):
                    statuses.append("correct")
                elif (pid, f, mid) in SUBSTANTIVE:
                    statuses.append("substantive")
                else:
                    statuses.append("equivalent")
            ws.write_row(r, 0, [pid, product_names[pid], f"{f}（{LABELS[f]}）", fmt(gold[(pid, f)])], goldcell)
            for ci in range(3):
                ws.write(r, 4 + ci, vals[ci], stfmt.get(statuses[ci], body))
            ws.write(r, 7, " / ".join(f"{MODELS[i][1]}={STATUS_LABEL[statuses[i]]}" for i in range(3)), body)
            r += 1
    ws.freeze_panes(3, 3)
    ws.set_column("A:A", 24); ws.set_column("B:B", 20); ws.set_column("C:C", 26)
    ws.set_column("D:G", 40); ws.set_column("H:H", 30)

    # ---- 实质分歧 ----
    ws = wb.add_worksheet("实质分歧")
    ws.hide_gridlines(2)
    ws.merge_range("A1:D1", "实质分歧清单（13 处，需人工复核）", title)
    ws.write_row("A3", ["产品", "字段", "模型", "原因"], head)
    r = 3
    for (pid, f, mid), reason in SUBSTANTIVE.items():
        ws.write_row(r, 0, [pid, f"{f}（{LABELS[f]}）", mid, reason], body)
        r += 1
    ws.set_column("A:A", 26); ws.set_column("B:B", 28); ws.set_column("C:C", 16); ws.set_column("D:D", 70)

    wb.close()
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
