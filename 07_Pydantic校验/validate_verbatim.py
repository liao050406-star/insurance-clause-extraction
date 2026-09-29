"""Validate the verbatim gold subset (责任名称 + 免责原文) against the extraction JSON.

Two checks per row:
1. grounding —— gold_text 逐字落在对应 canonical 文本中（证明金标本身出自条款原文）；
   逐句比对，并忽略分页标记 `<<<PAGE N>>>`，以容忍页脚和释义脚注把正文打断。
2. extraction —— 抽取结果中的责任名称 / 免责原文与 gold_text 逐字一致（NFKC + 去空白后）。

本脚本只读 gold_verbatim.csv，不修改、不反填。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD_VERBATIM = ROOT / "08_gold_csv对比" / "gold_verbatim.csv"

# product_id -> 提取结果文件名关键词 / canonical 文件名关键词
KEYWORDS = {
    "fuze_zerui_xianli": ("富泽", "富泽泽瑞一生"),
    "hengan_chuanshi_ruiying_b": ("恒安", "恒安标准传世瑞盈B款"),
    "cpic_xinxiangban_2025": ("太保", "太保鑫相伴"),
    "nci_ezengfu_youxiang": ("增福", "新华人寿"),
    "dongfang_zun_4_zhenxiang": ("东方", "东方嘉富东方尊4.0"),
}

PAGE_MARK = re.compile(r"<<<PAGE\s*\d+>>>")


def norm(value) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value)))


def strip_page_markers(text: str) -> str:
    return PAGE_MARK.sub("", text)


def sentences(text: str) -> list[str]:
    parts = text.split("。")
    return [p + "。" for p in parts if p.strip()]


def load_extracted(pred_dir: Path) -> dict[str, dict]:
    out = {}
    for p in sorted(pred_dir.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8-sig"))
        name = data.get("产品信息", {}).get("产品名称") or ""
        out[norm(name)] = data
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred-dir", type=Path, default=ROOT / "06_result_json" / "extracted")
    ap.add_argument("--raw-dir", type=Path, default=ROOT / "03_raw_text" / "raw_text")
    ap.add_argument("--out-json", type=Path, default=ROOT / "07_Pydantic校验" / "validation" / "validation_verbatim.json")
    ap.add_argument("--out-md", type=Path, default=ROOT / "09_validation_report" / "validation_report_verbatim.md")
    args = ap.parse_args()

    gold_sha = hashlib.sha256(GOLD_VERBATIM.read_bytes()).hexdigest()
    rows = list(csv.DictReader(GOLD_VERBATIM.open("r", encoding="utf-8-sig", newline="")))
    extracted = load_extracted(args.pred_dir)

    # canonical texts keyed by keyword
    canon_map = {}
    for p in sorted((args.raw_dir).glob("*.canonical.txt")):
        canon_map[norm(p.name)] = strip_page_markers(p.read_text(encoding="utf-8-sig"))

    def find_canonical(pid: str) -> tuple[str, str] | None:
        kw = KEYWORDS[pid][1]
        for name, text in canon_map.items():
            if kw in name:
                return name, norm(text)
        return None

    def find_extracted(pid: str):
        kw = KEYWORDS[pid][0]
        for name, data in extracted.items():
            if kw in name:
                return data
        return None

    results = []
    for r in rows:
        pid = r["product_id"]
        gold_text = r["gold_text"]

        # grounding
        canon = find_canonical(pid)
        if canon is None:
            grounded_ok, canon_name = False, None
        elif r["item_type"] == "免责原文":
            grounded_ok = all(norm(s) in canon[1] for s in sentences(gold_text))
            canon_name = canon[0]
        else:
            grounded_ok = norm(gold_text) in canon[1]
            canon_name = canon[0]

        # extraction
        data = find_extracted(pid)
        if data is None:
            status, extracted_text = "missing_product", None
        elif r["item_type"] == "责任名称":
            names = [norm(item.get("责任名称") or "") for item in data.get("保险责任", [])]
            if norm(gold_text) in names:
                status, extracted_text = "correct", gold_text
            else:
                status = "incorrect"
                extracted_text = " / ".join(item.get("责任名称") or "" for item in data.get("保险责任", []))
        else:  # 免责原文
            exc = data.get("责任免除", {})
            extracted_text = exc.get("原文") or ""
            status = "correct" if norm(extracted_text) == norm(gold_text) else "incorrect"

        results.append({
            "product_id": pid,
            "product_name": r["product_name"],
            "item_type": r["item_type"],
            "item_name": r["item_name"],
            "source_clause": r["source_clause"],
            "status": status,
            "grounded": grounded_ok,
            "canonical_file": canon_name,
        })

    total = len(results)
    correct = sum(1 for x in results if x["status"] == "correct")
    summary = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "gold_verbatim_sha256": gold_sha,
        "total": total,
        "correct": correct,
        "incorrect": sum(1 for x in results if x["status"] == "incorrect"),
        "missing_product": sum(1 for x in results if x["status"] == "missing_product"),
        "grounded": sum(1 for x in results if x["grounded"]),
        "accuracy": round(correct / total, 4) if total else 0,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# 责任名称与免责原文逐字核对报告",
        "",
        f"生成时间：{summary['generated_at']}",
        "",
        "## 汇总",
        "",
        f"- Gold 逐字条目：{total}（责任名称 {sum(1 for x in results if x['item_type']=='责任名称')} 条 + 免责原文 {sum(1 for x in results if x['item_type']=='免责原文')} 条）",
        f"- 逐字一致：{correct} / {total}",
        f"- 不一致：{summary['incorrect']}；缺失产品：{summary['missing_product']}",
        f"- 原文落位核验（gold_text 逐句在 canonical 文本中）：{summary['grounded']} / {total}",
        f"- 逐字准确率：{summary['accuracy']:.2%}",
        "",
        "## 口径说明",
        "",
        "- 逐字比较执行 Unicode NFKC 归一化并去除空白，保留全部文字、数字与释义标记（如“见11.11”“详见释义”）。",
        "- “原文落位核验”按句比对并忽略分页标记 `<<<PAGE N>>>`，用于证明 gold_text 出自条款原文、非人工改写；免责原文被释义脚注打断时仍能逐句核验。",
        "",
        "## 明细",
        "",
        "| 产品 | 类型 | 条目 | 条款号 | 逐字一致 | 原文落位 |",
        "|---|---|---|---|---|---|",
    ]
    for x in results:
        lines.append(
            f"| {x['product_name']} | {x['item_type']} | {x['item_name']} | {x['source_clause']} | "
            f"{x['status']} | {'是' if x['grounded'] else '否'} |"
        )
    lines += ["", "本报告仅用于条款信息整理与课程作业，不构成保险建议、产品推荐或产品排名。", ""]
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
