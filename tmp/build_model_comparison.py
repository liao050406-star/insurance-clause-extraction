"""Build the four-way (Gold + model A/B/C) comparison report and the
substantive-agreement review in one reproducible pass.

Strict accuracy is the machine-verified LOWER bound: `norm()` only strips
NFKC + punctuation/whitespace, so any wording/structure difference counts as
wrong.  The substantive metric is a human-curated second view: every
strict-incorrect item is either a genuine substantive error (in SUBSTANTIVE)
or a semantic-equivalent wording/structure difference (everything else).

The curated SUBSTANTIVE set is the single source of truth for both the report
and the review, so re-running this script reproduces the exact same artifacts
without clobbering any hand-written analysis.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "08_gold_csv对比" / "gold.csv"
FIELDS = [
    "insured_age_range", "waiting_period", "coverage_type",
    "benefit_before_payment_end", "benefit_after_payment_end",
    "age_benefit_ratio", "guaranteed_growth_rate",
    "effective_sum_assured_definition", "policy_loan", "reduction_rule",
    "dividend_guarantee", "dividend_type", "dividend_payment_method",
]
MODELS = [("codex_gpt5", "模型A", False), ("claude_sonnet", "模型B", True), ("claude_opus", "模型C", True)]
LABELS = {
    "insured_age_range": "投保年龄", "waiting_period": "等待期（天）", "coverage_type": "保险责任类型",
    "benefit_before_payment_end": "交费期满前给付", "benefit_after_payment_end": "交费期满后给付",
    "age_benefit_ratio": "年龄给付比例", "guaranteed_growth_rate": "固定递增系数",
    "effective_sum_assured_definition": "有效保险金额定义", "policy_loan": "保单贷款",
    "reduction_rule": "减额规则", "dividend_guarantee": "红利是否保证",
    "dividend_type": "红利类型", "dividend_payment_method": "红利领取/分配方式",
}
PRODUCT_ORDER = ["fuze_zerui_xianli", "hengan_chuanshi_ruiying_b", "cpic_xinxiangban_2025",
                 "nci_ezengfu_youxiang", "dongfang_zun_4_zhenxiang"]

# Curated substantive errors: (product_id, field_name, model_id) -> reason.
SUBSTANTIVE = {
    ("hengan_chuanshi_ruiying_b", "policy_loan", "claude_sonnet"): "漏 basis 子键（贷款额度计算基数「现金价值扣除各项欠款后余额」）",
    ("cpic_xinxiangban_2025", "policy_loan", "claude_sonnet"): "漏 basis 子键",
    ("nci_ezengfu_youxiang", "policy_loan", "claude_sonnet"): "漏 basis 子键",
    ("dongfang_zun_4_zhenxiang", "policy_loan", "claude_sonnet"): "漏 basis 子键",
    ("nci_ezengfu_youxiang", "effective_sum_assured_definition", "claude_sonnet"): "定义与增长公式混写（把保险金额写成基本保险金额×1.02^(n-1)）",
    ("hengan_chuanshi_ruiying_b", "dividend_payment_method", "claude_sonnet"): "漏记「已分配红利计入以后年度红利计算基数」",
    ("hengan_chuanshi_ruiying_b", "policy_loan", "claude_opus"): "漏 basis 子键",
    ("cpic_xinxiangban_2025", "policy_loan", "claude_opus"): "漏 basis 子键",
    ("nci_ezengfu_youxiang", "policy_loan", "claude_opus"): "漏 basis 子键",
    ("dongfang_zun_4_zhenxiang", "policy_loan", "claude_opus"): "漏 basis 子键",
    ("nci_ezengfu_youxiang", "age_benefit_ratio", "claude_opus"): "年龄边界 off-by-one（18-41/41-61 应为 18-40/41-60）",
    ("nci_ezengfu_youxiang", "effective_sum_assured_definition", "claude_opus"): "误判 null（漏抽有效保险金额定义）",
    ("hengan_chuanshi_ruiying_b", "dividend_payment_method", "claude_opus"): "漏记「已分配红利计入以后年度红利计算基数」",
}


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
        return re.sub(r"[\s，,；;：:。“”‘’、]", "", unicodedata.normalize("NFKC", value))
    if isinstance(value, list):
        return [norm(v) for v in value]
    if isinstance(value, dict):
        return {k: norm(v) for k, v in value.items()}
    return value


def fmt(v):
    if v is None:
        return "null"
    if isinstance(v, (dict, list, bool)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def load_model(model_id: str) -> tuple[dict, dict]:
    d = ROOT / "06_result_json" / "model_outputs" / model_id
    preds, metas = {}, {}
    for p in sorted(d.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        preds[data["metadata"]["product_id"]] = data["fields"]
        metas[data["metadata"]["product_id"]] = data["metadata"]
    return preds, metas


def main() -> None:
    gold_sha = hashlib.sha256(GOLD.read_bytes()).hexdigest()
    rows = list(csv.DictReader(GOLD.open("r", encoding="utf-8-sig", newline="")))
    gold = {(r["product_id"], r["field_name"]): parse_value(r["gold_value"]) for r in rows}
    models = {mid: load_model(mid) for mid, _, _ in MODELS}

    metrics = {}
    disagreements = []
    for mid, label, blind in MODELS:
        preds, _ = models[mid]
        c = Counter()
        by_field, by_product = defaultdict(Counter), defaultdict(Counter)
        equiv = subst = 0
        for r in rows:
            pid, f = r["product_id"], r["field_name"]
            pred = preds.get(pid, {}).get(f)
            if pred is None:
                status = "missing"
            elif norm(pred.get("value")) == norm(gold[(pid, f)]):
                status = "correct"
            elif (pid, f, mid) in SUBSTANTIVE:
                status, subst = "incorrect", subst + 1
            else:
                status, equiv = "incorrect", equiv + 1
            c[status] += 1
            by_field[f][status] += 1
            by_product[pid][status] += 1
        total = len(rows)
        metrics[mid] = {
            "label": label, "blind": blind, "total": total,
            "correct": c["correct"], "incorrect": c["incorrect"], "missing": c["missing"],
            "equivalent": equiv, "substantive": subst,
            "accuracy": c["correct"] / total if total else 0,
            "substantive_accuracy": (c["correct"] + equiv) / total if total else 0,
            "by_field": by_field, "by_product": by_product,
        }

    for r in rows:
        pid, f = r["product_id"], r["field_name"]
        gv = gold[(pid, f)]
        vals = {mid: models[mid][0].get(pid, {}).get(f) for mid, _, _ in MODELS}
        normed = {mid: norm(v.get("value")) if v is not None else "<missing>" for mid, v in vals.items()}
        gold_norm = norm(gv)
        differs = [mid for mid, _, _ in MODELS if normed[mid] != gold_norm]
        distinct = {json.dumps(gold_norm, ensure_ascii=False, sort_keys=True)} | \
                   {json.dumps(x, ensure_ascii=False, sort_keys=True) for x in normed.values()}
        if differs or len(distinct) > 1:
            disagreements.append({
                "product_id": pid, "field_name": f, "gold": gv,
                "models": {mid: (vals[mid].get("value") if vals[mid] is not None else None) for mid, _, _ in MODELS},
                "differs_from_gold": differs,
            })

    # ---- three_model_comparison.md ----
    lines = [
        "# 三模型（+ Gold）四方对比报告", "",
        "## 实验信息", "",
        f"- Gold：`08_gold_csv对比/gold.csv`（只读），共 {len(rows)} 行，SHA-256 `{gold_sha}`",
        "- 模型 A：`codex_gpt5`（Gold-aware 开发复核，**非盲测**，用于链路核验）",
        "- 模型 B：`claude_sonnet`（Claude Sonnet 5，**独立盲测**）",
        "- 模型 C：`claude_opus`（Claude Opus 5.5，**独立盲测**）",
        "- 输入：三模型共用同一份冻结 V3 提示词 `05_LLM_Prompt_Schema/prompts/generated_v3/`",
        "", "## 总体指标", "",
        "| 模型 | 正确 | 错误 | 缺失 | 准确率 | 盲测 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for mid, _, _ in MODELS:
        m = metrics[mid]
        lines.append(f"| {mid} | {m['correct']} | {m['incorrect']} | {m['missing']} | {m['accuracy']:.2%} | {'是' if m['blind'] else '否'} |")
    lines += ["", "## 双口径准确率（人工复核）", "",
              "严格字符比较把「语义等价差异」也判错，是**下界**；实质口径由人工逐条复核、把 13 处真实分歧单列（详见 `substantive_review.md`）。", "",
              "| 模型 | 严格准确率（机器） | 实质准确率（人工复核） |", "|---|---:|---:|",
              "| codex_gpt5 | 100.00%（Gold 副本，无泛化意义） | 100.00%（无意义） |"]
    for mid in ("claude_sonnet", "claude_opus"):
        m = metrics[mid]
        lines.append(f"| {mid} | {m['accuracy']:.2%}（{m['correct']}/65） | {m['substantive_accuracy']:.2%}（{m['correct'] + m['equivalent']}/65） |")
    lines += ["", "## 各模型字段级准确率", "", "| 字段 | " + " | ".join(mid for mid, _, _ in MODELS) + " |",
              "|---|" + "---|" * len(MODELS)]
    for f in FIELDS:
        cells = [f"{metrics[mid]['by_field'][f]['correct']}/5" for mid, _, _ in MODELS]
        lines.append(f"| {f}（{LABELS[f]}） | " + " | ".join(cells) + " |")
    lines += ["", "## 各模型产品级准确率", "", "| 产品 | " + " | ".join(mid for mid, _, _ in MODELS) + " |",
              "|---|" + "---|" * len(MODELS)]
    for pid in PRODUCT_ORDER:
        cells = [f"{metrics[mid]['by_product'][pid]['correct']}/13" for mid, _, _ in MODELS]
        lines.append(f"| {pid} | " + " | ".join(cells) + " |")
    lines += ["", "## 字段级分歧明细", "",
              "仅列出任一模型与 Gold 不一致、或三模型互不一致的行。", "",
              "| 产品 | 字段 | Gold | 模型A | 模型B | 模型C | 与Gold分歧 |",
              "|---|---|---|---|---|---|---|"]
    for d in disagreements:
        pid, f = d["product_id"], d["field_name"]
        cells = [fmt(d["gold"])] + [fmt(d["models"][mid]) for mid, _, _ in MODELS]
        differs = "、".join(d["differs_from_gold"]) if d["differs_from_gold"] else "—"
        lines.append(f"| {pid} | {f}（{LABELS[f]}） | " + " | ".join(cells) + f" | {differs} |")
    lines += ["", "## 重点分歧归因", "",
              "严格字符比较会把「语义等价但表述不同」判为错误。以下先区分「实质分歧」与「表述/结构差异」，再回到条款证据。", "",
              "### 实质分歧（真实规则或字段遗漏，需人工复核）", "",
              "| 产品 | 字段 | 模型 | 问题 |", "|---|---|---|---|"]
    for mid, _, _ in MODELS:
        for (pid, f, m), reason in SUBSTANTIVE.items():
            if m == mid:
                lines.append(f"| {pid} | {f} | {mid} | {reason} |")
    lines += ["", "### 表述/结构差异（语义等价，严格比较判为错）", "",
              "1. **精简归纳 vs 忠实摘录**：Gold 对 `effective_sum_assured_definition`、`reduction_rule` 采用精简归纳；两模型普遍直接摘录完整条款原文。事实一致，仅详略不同。",
              "2. **给付公式措辞**：`benefit_before/after_payment_end` 中，模型在「累计已交保险费」前补足「基本保险金额对应的」、「年龄给付比例」前补足「到达年龄（对应）」等限定词，公式运算层次不变。",
              "3. **JSON 形状**：Sonnet 把部分 `benefit_after_payment_end` 从字符串包成 `{\"adult_after_payment_end\": …}` 对象；恒安 `benefit_*` 用 `combination` / `rule: sum(…)` 表达「两项之和」，Gold 用 `rule: sum`。",
              "4. **字典键命名**：`age_benefit_ratio` 中 Sonnet 用条款原文边界词（「17周岁(含)以下」）代替规范键名（「0-17」），数值与边界一致。",
              "5. **个别措辞**：太保 `insured_age_range` 模型补写「被保险人」；恒安 `dividend_payment_method` 精简措辞。", "",
              "### 口径说明", "",
              "- **严格准确率**（可机器复现）：Sonnet 52.31%、Opus 58.46%。该口径把上述「语义等价差异」一并判错，是**下界**。",
              "- **实质准确率**（人工复核）：Sonnet 90.77%（59/65）、Opus 89.23%（58/65）。13 处实质分歧的逐条清单见 `substantive_review.md`；此数为人工判断，不作机器指标，引用时必须与严格口径同时给出。",
              "- **结论不变**：`codex_gpt5` 的 100% 是 Gold 副本，不代表泛化能力；独立盲测的真实水平由 B/C 体现，且需持续用未参与调优的独立测试集验证。",
              ""]
    (ROOT / "11_model_comparison" / "three_model_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---- three_model_comparison.json ----
    summary = {
        "gold_sha256": gold_sha,
        "metrics": {mid: {k: metrics[mid][k] for k in
                          ("label", "blind", "correct", "incorrect", "missing", "equivalent",
                           "substantive", "accuracy", "substantive_accuracy")} for mid, _, _ in MODELS},
        "disagreement_count": len(disagreements),
    }
    (ROOT / "11_model_comparison" / "three_model_comparison.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ---- substantive_review.md ----
    rev = ["# 实质一致复核（人工口径第二指标）", "",
           f"- Gold SHA-256：`{gold_sha}`",
           "- 本指标为**人工复核口径**，与严格字符比较（下界）并列展示，不作为机器可复现指标。",
           "- 规则：严格判错的项中，除下方「实质分歧」清单外，均视为**语义等价差异**。",
           "", "## 双口径对比", "",
           "| 模型 | 严格正确 | 语义等价 | 实质分歧 | 严格准确率 | 实质准确率 |",
           "|---|---:|---:|---:|---:|---:|"]
    for mid, _, _ in MODELS:
        m = metrics[mid]
        rev.append(f"| {mid} | {m['correct']} | {m['equivalent']} | {m['substantive']} | "
                   f"{m['accuracy']:.2%} | {m['substantive_accuracy']:.2%} |")
    rev += ["", "## 实质分歧清单（13 处，需人工复核）", "",
            "| 产品 | 字段 | 模型 | 原因 |", "|---|---|---|---|"]
    for mid, _, _ in MODELS:
        for (pid, f, m), reason in SUBSTANTIVE.items():
            if m == mid:
                rev.append(f"| {pid} | {f} | {mid} | {reason} |")
    rev += ["", "## 口径边界", "",
            "- 「语义等价」只覆盖表述、结构、键名、详略差异；**不覆盖**数值/边界变化、null 误判、子键遗漏、定义混写。",
            "- 实质准确率是人工判断，不能替代严格准确率；对外引用两者必须同时给出。",
            ""]
    (ROOT / "11_model_comparison" / "substantive_review.md").write_text("\n".join(rev) + "\n", encoding="utf-8")
    (ROOT / "11_model_comparison" / "substantive_review.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
