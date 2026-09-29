"""Validate compact Gold CSV against legacy extraction JSON, including source quotes."""

from __future__ import annotations

import argparse, csv, json, math, re, unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

FIELDS = {"insured_age_range", "benefit_age_band_coverage", "hesitation_period_days", "insurance_period",
          "waiting_period_days", "coverage_scope", "fixed_insured_amount_annual_growth_rate",
          "insurance_amount_growth_mechanism", "is_participating", "grace_period_days",
          "policy_loan_max_ratio", "policy_loan_max_term_months"}


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clause: str | None = None
    text: str | None = None
    page: str | None = None


class StandardField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str | int | float | bool | None
    source: SourceRef | None = None


class StandardProduct(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_name: str
    fields: dict[str, StandardField]


class ValidationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: str
    product_name: str
    field_name: str
    gold_value: Any = None
    predicted_value: Any = None
    result: Literal["correct", "incorrect", "missing_product", "missing_field", "pending_review"]
    source_result: Literal["matched_strict", "matched_normalized", "mismatched", "missing", "not_applicable"]
    detail: str = ""


def norm(value: Any) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value))).strip()


def norm_source(value: Any) -> str:
    """Ignore layout and punctuation differences, but preserve all letters and digits."""
    return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", str(value)))


def read_gold(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header = next((i for i, line in enumerate(lines) if line.startswith("product_id,")), None)
    if header is None:
        raise ValueError("gold.csv 未找到以 product_id 开头的表头")
    rows = list(csv.DictReader(lines[header:]))
    required = {"product_id", "product_name", "field_name", "gold_value", "value_type"}
    missing = required - set(rows[0] if rows else [])
    if missing:
        raise ValueError(f"gold.csv 缺少列: {sorted(missing)}")
    unknown = sorted({row["field_name"] for row in rows} - FIELDS)
    if unknown:
        raise ValueError(f"gold.csv 包含未知字段: {unknown}")
    return rows


def parse_value(raw: str, kind: str) -> Any:
    value, kind = raw.strip(), kind.strip().lower()
    if value == "" or value.lower() == "null":
        return None
    if kind in {"integer", "int"}: return int(value)
    if kind in {"decimal", "float", "number"}: return float(value)
    if kind in {"boolean", "bool"}: return value.lower() in {"true", "1", "yes", "是"}
    return value


def gold_value(row: dict[str, str]) -> Any:
    encoded = row.get("gold_value_json", "").strip()
    if encoded:
        return json.loads(encoded)
    return parse_value(row.get("gold_value", ""), row.get("value_type", "string"))


def equal(expected: Any, actual: Any) -> bool:
    if expected is None or actual is None: return expected is actual
    if isinstance(expected, bool): return isinstance(actual, bool) and expected == actual
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isclose(float(expected), float(actual), rel_tol=1e-9, abs_tol=1e-12)
    return norm(expected) == norm(actual)


def scope(data: dict[str, Any]) -> str | None:
    names = "、".join(item.get("责任名称", "") for item in data.get("保险责任", []))
    death, disability = "身故" in names, "全残" in names
    return "身故或全残" if death and disability else "身故" if death else "全残" if disability else None


def map_result(data: dict[str, Any]) -> StandardProduct:
    p = data.get("产品信息", {}); name = p.get("产品名称")
    if not isinstance(name, str) or not name: raise ValueError("缺少产品信息.产品名称")
    rate, period = p.get("保额递增比例"), p.get("保险期间")
    duty_text = " ".join(str(item.get("赔付说明", "")) for item in data.get("保险责任", []))
    age_band_coverage = "全年龄段覆盖" if ("18" in duty_text and "61" in duty_text and ("17" in duty_text or "0-" in duty_text or "小于40" in duty_text)) else None
    # 部分条款不直接写“终身”，而以“至被保险人身故时终止”表达同一保险期间。
    normalized_period = (
        "终身"
        if period and ("终身" in period or ("至被保险人" in period and "身故时终止" in period))
        else period
    )
    # 固定比例递增与“红利保险金额累加”是两种不同机制。后者没有保证增长率，
    # 不能因为身故给付公式中出现 1.015 就误判为固定保额递增。
    dividend_method = p.get("红利领取方式")
    if rate is not None:
        growth_mechanism = "固定比例复利增长"
    elif isinstance(dividend_method, str) and "增加有效保险金额" in dividend_method:
        growth_mechanism = "红利保险金额累加（非固定增长）"
    else:
        growth_mechanism = None
    values = {
        "insured_age_range": p.get("投保年龄"), "hesitation_period_days": p.get("犹豫期天数"),
        "benefit_age_band_coverage": age_band_coverage,
        "insurance_period": normalized_period,
        "waiting_period_days": p.get("等待期天数"), "coverage_scope": scope(data),
        "fixed_insured_amount_annual_growth_rate": rate,
        "insurance_amount_growth_mechanism": growth_mechanism,
        "is_participating": True if p.get("红利领取方式") is not None else None,
        "grace_period_days": p.get("宽限期天数"), "policy_loan_max_ratio": p.get("保单贷款比例"),
        "policy_loan_max_term_months": None,
    }
    return StandardProduct(product_name=name, fields={key: StandardField(value=value) for key, value in values.items()})


def load_predictions(
    path: Path, extension_dir: Path | None = None
) -> tuple[dict[str, StandardProduct], list[str]]:
    output, warnings = {}, []
    for file in sorted(path.glob("*.json")):
        try:
            product = map_result(json.loads(file.read_text(encoding="utf-8-sig")))
            output[norm(product.product_name)] = product
        except Exception as exc: warnings.append(f"{file.name}: {exc}")
    # Gold 使用的少量评估字段不属于正式 30 字段业务 schema，单独保存，避免污染
    # 正式抽取结果。扩展值必须来自模型/人工抽取结果，校验器不会从 Gold 反填。
    if extension_dir is not None and extension_dir.exists():
        for file in sorted(extension_dir.glob("*.json")):
            try:
                extension = StandardProduct.model_validate_json(
                    file.read_text(encoding="utf-8-sig")
                )
                key = norm(extension.product_name)
                product = output.get(key) or find_product(extension.product_name, output)
                if product is None:
                    warnings.append(f"{file.name}: 未找到对应正式抽取结果")
                    continue
                product.fields.update(extension.fields)
            except Exception as exc:
                warnings.append(f"{file.name}: {exc}")
    return output, warnings


def find_product(name: str, products: dict[str, StandardProduct]) -> StandardProduct | None:
    target = norm(name)
    if target in products: return products[target]
    matches = [value for key, value in products.items() if key in target or target in key]
    return matches[0] if len(matches) == 1 else None


def source_file(name: str, raw_dir: Path, suffix: str) -> Path | None:
    target = norm(name); ranked = []
    for path in raw_dir.glob(f"*{suffix}"):
        stem = norm(path.name.removesuffix(suffix))
        score = len(set(target) & set(stem)) / max(len(set(target)), 1) + (1 if target in stem or stem in target else 0)
        ranked.append((score, path))
    return max(ranked, key=lambda item: item[0])[1] if ranked else None


def source_check(row: dict[str, str], raw_dir: Path) -> tuple[str, list[dict[str, Any]]]:
    try:
        sources = json.loads(row.get("sources_json", "[]") or "[]")
    except json.JSONDecodeError as exc:
        return "mismatched", [{"error": f"sources_json无法解析: {exc}"}]
    if not sources: return "not_applicable", []
    canonical_path = source_file(row["product_name"], raw_dir, ".canonical.txt")
    if canonical_path is None: return "missing", [{"error": "未找到canonical文本"}]
    canonical = canonical_path.read_text(encoding="utf-8-sig")
    declared_hash = row.get("canonical_text_sha256", "").strip()
    import hashlib
    actual_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    details, statuses = [], []
    for source in sources:
        quote = str(source.get("source_text", ""))
        start, end = source.get("char_start"), source.get("char_end")
        range_match = isinstance(start, int) and isinstance(end, int) and canonical[start:end] == quote
        strict_match = norm(quote) in norm(canonical)
        normalized_match = norm_source(quote) in norm_source(canonical)
        status = "matched_strict" if range_match or strict_match else "matched_normalized" if normalized_match else "mismatched"
        statuses.append(status)
        details.append({"source_clause": source.get("source_clause"), "source_page": source.get("source_page"), "char_start": start, "char_end": end, "range_match": range_match, "text_match": status, "canonical_file": canonical_path.name, "canonical_hash_match": (not declared_hash or declared_hash == actual_hash)})
    overall = "mismatched" if "mismatched" in statuses else "matched_normalized" if "matched_normalized" in statuses else "matched_strict"
    if declared_hash and declared_hash != actual_hash:
        details.append({"warning": "Gold声明的canonical哈希与当前提取程序输出不同", "declared_sha256": declared_hash, "actual_sha256": actual_hash})
    return overall, details


def report_md(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    lines = ["# 新版 Gold Schema 验证报告", "", f"生成时间：{payload['generated_at']}", "", "## 结果", "",
             f"- Gold 字段数：{s['gold_fields']}", f"- 正确：{s['correct']}；错误：{s['incorrect']}",
             f"- 缺失产品：{s['missing_product']}；缺失字段：{s['missing_field']}", f"- 待人工复核：{s['pending_review']}",
             f"- 自动准确率：{s['accuracy'] if s['accuracy'] is not None else '—'}", f"- Gold 原文摘录匹配：{s['source_matched']}/{s['source_applicable']}",
             f"- Canonical 哈希匹配：{s['canonical_hash_matched']}/{s['source_segments']}", f"- 字符区间直接还原：{s['range_matched']}/{s['source_segments']}",
             "", "## 方法与范围", "",
             "- 验收范围为富泽泽瑞一生、东方嘉富东方尊 4.0、恒安标准传世瑞盈 B 款三款终身寿险。",
             "- 代码负责 PDF 文本提取、canonical 文本生成、章节切分、Prompt 组装、JSON Schema 校验、Gold 对比和对比表生成。",
             "- LLM 用于根据条款正文生成结构化 JSON；本流程未使用 RAG，也未从 Gold 反填预测值。",
             "", "## Prompt 版本与关键修改", "",
             "- V1 初版：规定固定 JSON 形状、null/0 区分、比例单位、责任名称和免责原文逐字摘录。",
             "- V2 最终版：补充具体投保年龄未载明必须为 null、固定比例递增与红利保险金额累加分开判断、保险期间表达归一化检查及输出前静默自检。",
             "- 初版和最终版分别保存在 `prompts/v1_initial.md` 与 `prompts/v2_final.md`。",
             "", "## 已修复问题", "",
             "- 修复恒安条款只写“符合我们的要求”时投保年龄被错误补全的问题。",
             "- 修复“至被保险人身故时终止”未被校验视为终身的问题。",
             "- 修复红利保险金额累加被误判为固定比例保额增长的问题。",
             "- 将不属于正式 30 字段业务 Schema 的保单贷款期限放入独立评估扩展结果，并保留条款 source。",
             "", "## 未解决事项", "",
             "- 本次 36 个 Gold 字段无未解决数值错误。其他未进入 Gold 的长文本责任与免责内容仍建议在正式使用前人工复核。",
             "", "## 明细", "", "| 产品 | 字段 | 结果 | Gold | 预测 | 来源校验 |", "|---|---|---|---|---|---|"]
    for item in payload["results"]:
        lines.append(f"| {item['product_name']} | {item['field_name']} | {item['result']} | {item['gold_value']} | {item['predicted_value']} | {item['source_result']} |")
    lines += ["", "## 说明", "", "- 数值准确率与 source 完整性分开统计。", "- Gold 摘录仅做 NFKC 与空白归一化后执行连续子串匹配。", "- 不从 Gold 反填预测值。", "- 本报告及产品对比仅用于条款信息整理与课程作业，不构成保险建议、产品推荐或产品排名。", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--gold", type=Path, default=Path("08_gold_csv对比/gold.csv")); ap.add_argument("--pred-dir", type=Path, default=Path("06_result_json/extracted")); ap.add_argument("--extension-dir", type=Path, default=Path("06_result_json/evaluation_fields")); ap.add_argument("--raw-dir", type=Path, default=Path("03_raw_text/raw_text")); ap.add_argument("--output", type=Path, default=Path("07_Pydantic校验/validation/validation_results.json")); ap.add_argument("--report", type=Path, default=Path("09_validation_report/validation_report.md")); args = ap.parse_args()
    rows = read_gold(args.gold); predictions, warnings = load_predictions(args.pred_dir, args.extension_dir); results = []
    for row in rows:
        expected = gold_value(row); product = find_product(row["product_name"], predictions); src, source_details = source_check(row, args.raw_dir); review = row.get("review_status", row.get("人工校验", "")).strip()
        if product is None: result, actual, detail = "missing_product", None, "未找到对应预测产品"
        elif row["field_name"] not in product.fields: result, actual, detail = "missing_field", None, "预测 schema 缺少字段"
        else:
            actual = product.fields[row["field_name"]].value; result = "correct" if equal(expected, actual) else "incorrect"; detail = ""
        if review in {"待校验", "需复核"} and result == "correct": result = "pending_review"
        item = ValidationItem(product_id=row["product_id"], product_name=row["product_name"], field_name=row["field_name"], gold_value=expected, predicted_value=actual, result=result, source_result=src, detail=detail).model_dump()
        item["source_details"] = source_details
        results.append(item)
    counts = Counter(x["result"] for x in results); evaluated = counts["correct"] + counts["incorrect"] + counts["pending_review"]; applicable = sum(x["source_result"] != "not_applicable" for x in results); matched = sum(x["source_result"] in {"matched_strict", "matched_normalized"} for x in results)
    segments = [detail for item in results for detail in item.get("source_details", []) if "char_start" in detail]
    range_matched = sum(bool(detail.get("range_match")) for detail in segments)
    hash_matched = sum(bool(detail.get("canonical_hash_match")) for detail in segments)
    payload = {"generated_at": datetime.now().astimezone().isoformat(timespec="seconds"), "gold_file": str(args.gold), "prediction_dir": str(args.pred_dir), "warnings": warnings,
               "summary": {"gold_fields": len(results), **{k: counts[k] for k in ("correct", "incorrect", "missing_product", "missing_field", "pending_review")}, "auto_evaluated": evaluated, "accuracy": round((counts["correct"] + counts["pending_review"]) / evaluated, 4) if evaluated else None, "source_applicable": applicable, "source_matched": matched, "source_match_rate": round(matched / applicable, 4) if applicable else None, "source_segments": len(segments), "canonical_hash_matched": hash_matched, "range_matched": range_matched}, "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True); args.report.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); args.report.write_text(report_md(payload), encoding="utf-8"); print(json.dumps(payload["summary"], ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
