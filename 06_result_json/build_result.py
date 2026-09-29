"""Validate individual extraction JSON files and atomically build result.json."""
from __future__ import annotations
import argparse, json, os, sys, tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "05_LLM_Prompt_Schema"))
from llm_extract import validate_result  # noqa: E402


def build(input_dir: Path, output: Path) -> dict:
    results, rejected = [], []
    for path in sorted(input_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig")); errors = validate_result(data)
        except (OSError, json.JSONDecodeError) as exc: errors, data = [str(exc)], None
        (rejected if errors else results).append({"result_file": path.name, "errors": errors} if errors else {"result_file": path.name, "result": data})
    payload = {"schema_version": "1.1", "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"), "document_count": len(results), "rejected_count": len(rejected), "results": results, "rejected": rejected}
    output.parent.mkdir(parents=True, exist_ok=True); handle, temp_name = tempfile.mkstemp(prefix=output.name + ".", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream: json.dump(payload, stream, ensure_ascii=False, indent=2); stream.write("\n")
        os.replace(temp_name, output)
    except Exception:
        Path(temp_name).unlink(missing_ok=True); raise
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--input-dir", type=Path, default=ROOT / "06_result_json" / "extracted"); ap.add_argument("--output", type=Path, default=ROOT / "06_result_json" / "result.json"); args = ap.parse_args(); payload = build(args.input_dir, args.output); print(json.dumps({k: payload[k] for k in ("document_count", "rejected_count")}, ensure_ascii=False)); return 1 if payload["rejected_count"] else 0


if __name__ == "__main__": raise SystemExit(main())
