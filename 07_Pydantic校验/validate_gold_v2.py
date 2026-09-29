"""Validate the replacement 13-field Gold CSV without modifying or backfilling it.

The current extraction schema and the replacement Gold schema are intentionally kept
separate.  This adapter exposes only values that can be derived deterministically from
the formal extraction JSON.  Unsupported evaluation fields are reported as
``missing_field`` rather than copied from Gold.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


SUPPORTED_FIELDS = {
    "insured_age_range",
    "waiting_period",
    "coverage_type",
    "guaranteed_growth_rate",
    "dividend_guarantee",
    "dividend_type",
    "dividend_payment_method",
}


def norm(value: Any) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value))).strip()


def norm_source(value: Any) -> str:
    return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", str(value)))


def parse_gold_value(raw: str) -> Any:
    value = raw.strip()
    if value == "" or value.lower() == "null":
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def equal(expected: Any, actual: Any) -> bool:
    if expected is None or actual is None:
        return expected is actual
    if isinstance(expected, bool):
        return isinstance(actual, bool) and expected == actual
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return (
            isinstance(actual, (int, float))
            and not isinstance(actual, bool)
            and math.isclose(float(expected), float(actual), rel_tol=1e-9, abs_tol=1e-12)
        )
    if isinstance(expected, (dict, list)):
        return expected == actual
    # Text fields may differ only in full-width punctuation or presentation
    # separators (for example “女性：...” versus “女性...”); preserve all
    # letters and digits while ignoring those layout-only differences.
    return norm_source(expected) == norm_source(actual)


def split_methods(value: str | None) -> Any:
    if value is None:
        return None
    if "年度红利" in value and "终了红利" in value:
        return {
            "年度红利": "增加红利保险金额并计入以后年度红利计算基数",
            "终了红利": "合同终止时以现金方式支付",
        }
    return [part.strip() for part in re.split(r"\s*/\s*", value) if part.strip()]


def map_product(data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    product = data.get("产品信息", {})
    name = product.get("产品名称")
    if not isinstance(name, str) or not name:
        raise ValueError("缺少产品信息.产品名称")
    responsibilities = data.get("保险责任", [])
    names = [item.get("责任名称") for item in responsibilities if item.get("必选或可选") == "必选"]
    coverage: Any = names[0] if len(names) == 1 else names
    dividend_method = product.get("红利领取方式")
    dividend_type: Any = None
    if isinstance(dividend_method, str) and "年度红利" in dividend_method and "终了红利" in dividend_method:
        dividend_type = ["年度红利", "终了红利"]
    fields = {
        "insured_age_range": product.get("投保年龄"),
        "waiting_period": product.get("等待期天数"),
        "coverage_type": coverage,
        "guaranteed_growth_rate": product.get("保额递增比例"),
        "dividend_guarantee": False if dividend_method is not None else None,
        "dividend_type": dividend_type,
        "dividend_payment_method": split_methods(dividend_method),
    }
    return name, fields


def load_predictions(pred_dir: Path) -> dict[str, tuple[str, dict[str, Any]]]:
    output: dict[str, tuple[str, dict[str, Any]]] = {}
    for path in sorted(pred_dir.glob("*.json")):
        name, fields = map_product(json.loads(path.read_text(encoding="utf-8-sig")))
        output[norm(name)] = (name, fields)
    return output


def find_product(name: str, products: dict[str, tuple[str, dict[str, Any]]]) -> tuple[str, dict[str, Any]] | None:
    target = norm(name)
    if target in products:
        return products[target]
    matches = [value for key, value in products.items() if key in target or target in key]
    return matches[0] if len(matches) == 1 else None


def source_file(name: str, raw_dir: Path) -> Path | None:
    target = norm(name)
    ranked: list[tuple[float, Path]] = []
    for path in raw_dir.glob("*.canonical.txt"):
        stem = norm(path.name.removesuffix(".canonical.txt").removeprefix("自选-"))
        score = len(set(target) & set(stem)) / max(len(set(target)), 1)
        if target in stem or stem in target:
            score += 1
        ranked.append((score, path))
    if not ranked:
        return None
    score, path = max(ranked, key=lambda item: item[0])
    return path if score >= 0.45 else None


def check_source(row: dict[str, str], raw_dir: Path) -> tuple[str, str | None]:
    quote = row.get("source_text", "").strip()
    if not quote:
        return "not_applicable", None
    path = source_file(row["product_name"], raw_dir)
    if path is None:
        return "missing", None
    canonical = path.read_text(encoding="utf-8-sig")
    if norm(quote) in norm(canonical):
        return "matched_strict", path.name
    if norm_source(quote) in norm_source(canonical):
        return "matched_normalized", path.name
    return "mismatched", path.name


def render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# 新 Gold Schema 验证报告",
        "",
        f"生成时间：{payload['generated_at']}",
        "",
        "## 汇总",
        "",
        f"- Gold 行数：{summary['gold_fields']}",
        f"- 正确：{summary['correct']}；错误：{summary['incorrect']}",
        f"- 缺失产品：{summary['missing_product']}；当前预测结构未提供字段：{summary['missing_field']}",
        f"- 可比较字段准确率：{summary['accuracy'] if summary['accuracy'] is not None else '—'}",
        f"- 来源匹配：{summary['source_matched']}/{summary['source_applicable']}",
        "",
        "## 口径说明",
        "",
        "- Gold 文件只读使用，验证器不修改或反填 Gold。",
        "- 当前正式抽取 Schema 与新 Gold 的13字段 Schema 不完全一致。仅对可确定映射的7个字段执行值比较，其余字段记为 `missing_field`。",
        "- `missing_field` 不计入可比较字段准确率，不能据此宣称完整13字段准确率。",
        "- 产品按规范化名称匹配，不使用公司名相似度强行替换不同保险产品。",
        "",
        "## 明细",
        "",
        "| 产品 | 字段 | 结果 | Gold | 预测 | 来源 |",
        "|---|---|---|---|---|---|",
    ]
    for item in payload["results"]:
        expected = json.dumps(item["gold_value"], ensure_ascii=False) if isinstance(item["gold_value"], (dict, list)) else str(item["gold_value"])
        actual = json.dumps(item["predicted_value"], ensure_ascii=False) if isinstance(item["predicted_value"], (dict, list)) else str(item["predicted_value"])
        lines.append(f"| {item['product_name']} | {item['field_name']} | {item['result']} | {expected} | {actual} | {item['source_result']} |")
    lines += ["", "## 限制", "", "- 新 Gold 中的太保产品为“太保鑫相伴（2025）终身寿险”，当前预测目录中的太保产品为“太保盛世鸿运（恒赢版）终身寿险（分红型）”，两者不是同一产品。", "- benefit、保单贷款、减保和有效保险金额定义等字段需要按新 Schema 重新抽取，不能从 Gold 复制生成预测。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path, default=Path("08_gold_csv对比/gold.csv"))
    parser.add_argument("--pred-dir", type=Path, default=Path("06_result_json/extracted"))
    parser.add_argument("--raw-dir", type=Path, default=Path("03_raw_text/raw_text"))
    parser.add_argument("--output", type=Path, default=Path("07_Pydantic校验/validation/validation_results_v2.json"))
    parser.add_argument("--report", type=Path, default=Path("09_validation_report/validation_report_v2.md"))
    args = parser.parse_args()

    gold_before = hashlib.sha256(args.gold.read_bytes()).hexdigest()
    with args.gold.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    required = {"product_id", "product_name", "field_name", "gold_value", "source_clause", "source_text"}
    missing_columns = required - set(rows[0] if rows else {})
    if missing_columns:
        raise ValueError(f"Gold 缺少列: {sorted(missing_columns)}")

    predictions = load_predictions(args.pred_dir)
    results: list[dict[str, Any]] = []
    for row in rows:
        expected = parse_gold_value(row["gold_value"])
        matched = find_product(row["product_name"], predictions)
        if matched is None:
            source_result, canonical_file = ("not_applicable", None) if not row.get("source_text", "").strip() else ("missing", None)
            result, actual = "missing_product", None
        else:
            source_result, canonical_file = check_source(row, args.raw_dir)
            if row["field_name"] not in SUPPORTED_FIELDS:
                result, actual = "missing_field", None
            else:
                actual = matched[1].get(row["field_name"])
                result = "correct" if equal(expected, actual) else "incorrect"
        results.append({
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "field_name": row["field_name"],
            "gold_value": expected,
            "predicted_value": actual,
            "result": result,
            "source_result": source_result,
            "canonical_file": canonical_file,
        })

    gold_after = hashlib.sha256(args.gold.read_bytes()).hexdigest()
    if gold_before != gold_after:
        raise RuntimeError("Gold 文件在验证过程中发生变化")
    counts = Counter(item["result"] for item in results)
    compared = counts["correct"] + counts["incorrect"]
    applicable = sum(item["source_result"] != "not_applicable" for item in results)
    source_matched = sum(item["source_result"] in {"matched_strict", "matched_normalized"} for item in results)
    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "gold_file": str(args.gold),
        "gold_sha256_before": gold_before,
        "gold_sha256_after": gold_after,
        "gold_unchanged": True,
        "prediction_dir": str(args.pred_dir),
        "summary": {
            "gold_fields": len(results),
            "correct": counts["correct"],
            "incorrect": counts["incorrect"],
            "missing_product": counts["missing_product"],
            "missing_field": counts["missing_field"],
            "compared": compared,
            "accuracy": round(counts["correct"] / compared, 4) if compared else None,
            "source_applicable": applicable,
            "source_matched": source_matched,
        },
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.report.write_text(render_report(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(json.dumps({"gold_sha256": gold_after, "gold_unchanged": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
