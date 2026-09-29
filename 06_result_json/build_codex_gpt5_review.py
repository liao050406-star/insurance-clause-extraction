"""Build the current model's Gold-aware development review files.

This is intentionally labelled non-blind.  It is a pipeline/reference check, not
an independent accuracy sample.  Model B and C must be produced without Gold.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "08_gold_csv对比" / "gold.csv"
OUT = ROOT / "06_result_json" / "model_outputs" / "codex_gpt5"


def parse_value(raw: str):
    raw = raw.strip()
    if raw in {"null", "true", "false"} or raw.startswith(("{", "[", '"')):
        return json.loads(raw)
    try:
        return float(raw) if "." in raw else int(raw)
    except ValueError:
        return raw


def main() -> None:
    before = hashlib.sha256(GOLD.read_bytes()).hexdigest()
    rows = list(csv.DictReader(GOLD.open("r", encoding="utf-8-sig", newline="")))
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["product_id"], []).append(row)
    OUT.mkdir(parents=True, exist_ok=True)
    for product_id, items in grouped.items():
        payload = {
            "metadata": {
                "model_id": "codex_gpt5",
                "product_id": product_id,
                "product_name": items[0]["product_name"],
                "evaluation_mode": "gold_aware_development_review",
                "independent_blind_test": False,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "warning": "本结果用于验证数据结构与报告链路，模型已接触Gold，不计入独立盲测准确率。",
            },
            "fields": {
                row["field_name"]: {
                    "value": parse_value(row["gold_value"]),
                    "source_clause": row["source_clause"],
                    "source_text": row["source_text"],
                }
                for row in items
            },
        }
        path = OUT / f"{product_id}__codex_gpt5.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    after = hashlib.sha256(GOLD.read_bytes()).hexdigest()
    if before != after:
        raise RuntimeError("gold.csv changed unexpectedly")
    print(f"wrote {len(grouped)} files; gold_sha256={after}")


if __name__ == "__main__":
    main()
