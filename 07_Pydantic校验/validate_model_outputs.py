from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    "insured_age_range", "waiting_period", "coverage_type",
    "benefit_before_payment_end", "benefit_after_payment_end",
    "age_benefit_ratio", "guaranteed_growth_rate",
    "effective_sum_assured_definition", "policy_loan", "reduction_rule",
    "dividend_guarantee", "dividend_type", "dividend_payment_method",
]


def parse_value(raw: str):
    raw = raw.strip()
    if raw in {"null", "true", "false"} or raw.startswith(("{", "[", '"')):
        return json.loads(raw)
    try:
        return float(raw) if "." in raw else int(raw)
    except ValueError:
        return raw


def norm(value):
    if isinstance(value, str):
        s = unicodedata.normalize("NFKC", value)
        return re.sub(r"[\s，,；;：:。“”‘’、]", "", s)
    if isinstance(value, list):
        return [norm(v) for v in value]
    if isinstance(value, dict):
        return {k: norm(v) for k, v in value.items()}
    return value


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-id", default="codex_gpt5")
    args = ap.parse_args()
    gold_path = ROOT / "08_gold_csv对比" / "gold.csv"
    before = hashlib.sha256(gold_path.read_bytes()).hexdigest()
    rows = list(csv.DictReader(gold_path.open("r", encoding="utf-8-sig", newline="")))
    model_dir = ROOT / "06_result_json" / "model_outputs" / args.model_id
    predictions = {}
    metadata = {}
    for path in sorted(model_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        pid = data["metadata"]["product_id"]
        predictions[pid] = data["fields"]
        metadata[pid] = data["metadata"]
    details, counts = [], Counter()
    by_field, by_product = defaultdict(Counter), defaultdict(Counter)
    for row in rows:
        pid, field = row["product_id"], row["field_name"]
        pred = predictions.get(pid, {}).get(field)
        if pred is None:
            status, got = "missing", None
        else:
            got = pred.get("value")
            status = "correct" if norm(got) == norm(parse_value(row["gold_value"])) else "incorrect"
        counts[status] += 1
        by_field[field][status] += 1
        by_product[pid][status] += 1
        details.append({"product_id": pid, "field_name": field, "status": status,
                        "predicted": got, "gold": parse_value(row["gold_value"])})
    total = len(rows)
    summary = {
        "model_id": args.model_id,
        "gold_sha256": before,
        "total": total,
        "correct": counts["correct"], "incorrect": counts["incorrect"], "missing": counts["missing"],
        "accuracy": counts["correct"] / total if total else 0,
        "independent_blind_test": all(m.get("independent_blind_test") is True for m in metadata.values()),
        "by_field": {f: dict(by_field[f]) for f in FIELDS},
        "by_product": {p: dict(v) for p, v in by_product.items()},
        "details": details,
    }
    out_dir = ROOT / "07_Pydantic校验" / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"validation_results_{args.model_id}.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    worst = sorted(FIELDS, key=lambda f: (by_field[f]["correct"], f))[:3]
    md = [f"# {args.model_id} 13字段验证报告", "",
          f"- Gold SHA-256：`{before}`", f"- 总项数：{total}",
          f"- 正确 / 错误 / 缺失：{counts['correct']} / {counts['incorrect']} / {counts['missing']}",
          f"- 准确率：{summary['accuracy']:.2%}",
          f"- 独立盲测：{'是' if summary['independent_blind_test'] else '否（开发复核）'}", "",
          "## 最弱三个字段", ""]
    for f in worst:
        md.append(f"- `{f}`：{by_field[f]['correct']}/5 正确")
    md += ["", "## 产品汇总", "", "| product_id | 正确 | 错误 | 缺失 |", "|---|---:|---:|---:|"]
    for pid, c in by_product.items():
        md.append(f"| {pid} | {c['correct']} | {c['incorrect']} | {c['missing']} |")
    report = ROOT / "09_validation_report" / f"validation_report_{args.model_id}.md"
    report.write_text("\n".join(md) + "\n", encoding="utf-8")
    after = hashlib.sha256(gold_path.read_bytes()).hexdigest()
    if before != after:
        raise RuntimeError("gold.csv changed unexpectedly")
    print(json.dumps({k: summary[k] for k in ("total", "correct", "incorrect", "missing", "accuracy", "independent_blind_test")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
