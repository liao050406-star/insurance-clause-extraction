"""Extract page-aware raw and cleaned text from insurance clause PDFs.

The extractor deliberately keeps two representations:

* raw_text: close to pdfplumber's output, for later quotation verification;
* clean_text: conservative whitespace/header cleanup, for section splitting and LLM input;
* canonical_text: deterministic page-aware text used only for source spans and hashing.

No OCR is performed. A page with very little extractable text is reported as a warning so
that scanned PDFs are not silently treated as successfully extracted documents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Iterable


PAGE_NUMBER_PATTERNS = (
    re.compile(r"^第\s*\d+\s*页\s*[，,]\s*共\s*\d+\s*页$"),
    re.compile(r"^第\s*\d+\s*页$"),
    # Appended base clauses sometimes use a footer such as
    # “个人保险基本条款第三版第2页”.  It is layout metadata rather than body text.
    re.compile(r"^.{1,40}第\s*\d+\s*页$"),
    re.compile(r"^[-—–]?\s*\d+\s*[-—–]?$"),
    re.compile(r"^\d+\s*/\s*\d+$"),
)
MIN_TEXT_CHARS_PER_PAGE = 40
SUPPORTED_ENGINES = ("auto", "pdfplumber", "pypdf")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def text_quality(text: str) -> dict[str, float | int]:
    """Return deterministic diagnostics used to detect weak PDF text layers."""
    compact = re.sub(r"\s+", "", text)
    visible = len(compact)
    cjk = len(re.findall(r"[\u3400-\u9fff]", compact))
    replacement = compact.count("\ufffd")
    controls = sum(1 for char in compact if unicodedata.category(char) == "Cc")
    useful = sum(1 for char in compact if char.isalnum() or "\u3400" <= char <= "\u9fff")
    return {
        "visible_chars": visible,
        "cjk_chars": cjk,
        "replacement_chars": replacement,
        "control_chars": controls,
        "useful_char_ratio": round(useful / visible, 4) if visible else 0.0,
    }


def prefer_fallback(primary: str, fallback: str) -> bool:
    """Use a fallback only when it is materially better than the primary output."""
    first = text_quality(primary)
    second = text_quality(fallback)
    if second["replacement_chars"] > first["replacement_chars"]:
        return False
    if second["control_chars"] > first["control_chars"]:
        return False
    first_chars = int(first["visible_chars"])
    second_chars = int(second["visible_chars"])
    if first_chars < MIN_TEXT_CHARS_PER_PAGE <= second_chars:
        return True
    return second_chars >= max(first_chars + 40, math.ceil(first_chars * 1.2))


def normalize_raw_text(text: str | None) -> str:
    """Apply only lossless-ish cleanup to extracted text."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def normalize_clean_line(line: str) -> str:
    """Normalize a line for reading while retaining wording and punctuation."""
    line = unicodedata.normalize("NFKC", line)
    line = line.replace("\u00a0", " ").replace("\u3000", " ")
    line = re.sub(r"[\t ]+", " ", line).strip()

    # PDF text layers sometimes insert spaces between every Chinese character.
    previous = None
    while previous != line:
        previous = line
        line = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", line)
    return line


def canonical_margin_line(line: str) -> str:
    line = normalize_clean_line(line)
    line = re.sub(r"\d+", "#", line)
    return line


def is_page_number(line: str) -> bool:
    normalized = normalize_clean_line(line)
    return any(pattern.fullmatch(normalized) for pattern in PAGE_NUMBER_PATTERNS)


def nonempty_line_indexes(lines: list[str]) -> list[int]:
    return [index for index, line in enumerate(lines) if normalize_clean_line(line)]


def find_repeating_margin_lines(raw_pages: list[str]) -> set[str]:
    """Find short lines repeated near page tops/bottoms, usually headers and footers."""
    counts: Counter[str] = Counter()
    for text in raw_pages:
        lines = text.splitlines()
        indexes = nonempty_line_indexes(lines)
        margin_indexes = set(indexes[:4] + indexes[-4:])
        seen_on_page: set[str] = set()
        for index in margin_indexes:
            candidate = canonical_margin_line(lines[index])
            if candidate and len(candidate) <= 100:
                seen_on_page.add(candidate)
        counts.update(seen_on_page)

    threshold = max(2, math.ceil(len(raw_pages) * 0.5))
    return {line for line, count in counts.items() if count >= threshold}


def clean_page_text(raw_text: str, repeating_margin_lines: set[str]) -> str:
    lines = raw_text.splitlines()
    nonempty_indexes = nonempty_line_indexes(lines)
    margin_indexes = set(nonempty_indexes[:4] + nonempty_indexes[-4:])
    cleaned: list[str] = []

    for index, raw_line in enumerate(lines):
        line = normalize_clean_line(raw_line)
        if not line:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        if is_page_number(line):
            continue
        if index in margin_indexes and canonical_margin_line(line) in repeating_margin_lines:
            continue
        cleaned.append(line)

    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return "\n".join(cleaned)


def render_text_file(pages: Iterable[dict[str, object]], key: str) -> str:
    blocks: list[str] = []
    for page in pages:
        blocks.append(f"===== PAGE {page['page_number']} =====\n{page[key]}")
    return "\n\n".join(blocks).rstrip() + "\n"


def canonical_page_text(clean_text: str) -> str:
    """Create a stable citation view without changing any non-whitespace character.

    PDF line wrapping is layout, not wording.  Joining non-empty physical lines with one
    ASCII space makes a sentence contiguous while retaining footnote numbers and punctuation.
    """
    return " ".join(line.strip() for line in clean_text.splitlines() if line.strip())


def build_canonical_text(pages: Iterable[dict[str, object]]) -> tuple[str, list[dict[str, int]]]:
    parts: list[str] = []
    page_spans: list[dict[str, int]] = []
    offset = 0
    for page in pages:
        if parts:
            parts.append("\n")
            offset += 1
        marker = f"<<<PAGE {page['page_number']}>>>\n"
        parts.append(marker)
        offset += len(marker)
        start = offset
        value = str(page["canonical_text"])
        parts.append(value)
        offset += len(value)
        page_spans.append({"page_number": int(page["page_number"]), "char_start": start, "char_end": offset})
    return "".join(parts) + "\n", page_spans


def atomic_write_text(path: Path, content: str) -> None:
    """Avoid leaving truncated outputs if a run is interrupted."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, newline="\n"
    ) as stream:
        stream.write(content)
        temporary = Path(stream.name)
    temporary.replace(path)


def output_paths(pdf_path: Path, output_dir: Path) -> dict[str, Path]:
    stem = pdf_path.stem
    return {
        "json": output_dir / f"{stem}.pages.json",
        "raw": output_dir / f"{stem}.raw.txt",
        "clean": output_dir / f"{stem}.clean.txt",
        "canonical": output_dir / f"{stem}.canonical.txt",
        "canonical_map": output_dir / f"{stem}.canonical.map.json",
        "quality": output_dir / f"{stem}.quality.json",
    }


def extract_with_pdfplumber(pdf_path: Path) -> tuple[list[str], list[dict[str, float]]]:
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - environment-dependent message
        raise RuntimeError("缺少 pdfplumber，请先运行 pip install -r requirements.txt") from exc

    texts: list[str] = []
    sizes: list[dict[str, float]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            texts.append(
                normalize_raw_text(page.extract_text(x_tolerance=2, y_tolerance=3, layout=False))
            )
            sizes.append({"width": float(page.width), "height": float(page.height)})
    return texts, sizes


def extract_with_pypdf(pdf_path: Path) -> tuple[list[str], list[dict[str, float]]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - environment-dependent message
        raise RuntimeError("缺少 pypdf，请先运行 pip install -r requirements.txt") from exc

    reader = PdfReader(pdf_path)
    texts: list[str] = []
    sizes: list[dict[str, float]] = []
    for page in reader.pages:
        texts.append(normalize_raw_text(page.extract_text(extraction_mode="layout")))
        sizes.append(
            {
                "width": float(page.mediabox.width),
                "height": float(page.mediabox.height),
            }
        )
    return texts, sizes


def extract_pages(
    pdf_path: Path, engine: str
) -> tuple[list[str], list[dict[str, float]], list[str]]:
    if engine == "pdfplumber":
        texts, sizes = extract_with_pdfplumber(pdf_path)
        return texts, sizes, ["pdfplumber"] * len(texts)
    if engine == "pypdf":
        texts, sizes = extract_with_pypdf(pdf_path)
        return texts, sizes, ["pypdf"] * len(texts)

    primary, sizes = extract_with_pdfplumber(pdf_path)
    selected = list(primary)
    selected_engines = ["pdfplumber"] * len(primary)
    weak_indexes = [
        index
        for index, text in enumerate(primary)
        if int(text_quality(text)["visible_chars"]) < MIN_TEXT_CHARS_PER_PAGE
    ]
    if weak_indexes:
        fallback, fallback_sizes = extract_with_pypdf(pdf_path)
        if len(fallback) != len(primary):
            raise RuntimeError("pdfplumber 与 pypdf 识别的页数不一致")
        for index in weak_indexes:
            if prefer_fallback(primary[index], fallback[index]):
                selected[index] = fallback[index]
                selected_engines[index] = "pypdf"
                sizes[index] = fallback_sizes[index]
    return selected, sizes, selected_engines


def extraction_status(warnings: list[dict[str, object]], page_count: int) -> str:
    weak_pages = sum(1 for item in warnings if item["code"] == "LOW_TEXT_DENSITY")
    if page_count and weak_pages / page_count >= 0.3:
        return "ocr_required"
    if warnings:
        return "needs_review"
    return "ok"


def extract_pdf(
    pdf_path: Path,
    output_dir: Path,
    force: bool = False,
    engine: str = "auto",
) -> dict[str, object]:

    pdf_path = pdf_path.resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF 不存在: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"输入不是 PDF: {pdf_path}")
    if engine not in SUPPORTED_ENGINES:
        raise ValueError(f"不支持的提取引擎: {engine}")

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = output_paths(pdf_path, output_dir)
    existing = [path for path in paths.values() if path.exists()]
    if existing and not force:
        joined = "、".join(str(path) for path in existing)
        raise FileExistsError(f"输出已存在，请使用 --force 覆盖: {joined}")

    raw_pages, page_sizes, page_engines = extract_pages(pdf_path, engine)

    repeating = find_repeating_margin_lines(raw_pages)
    pages: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    for index, raw_text in enumerate(raw_pages):
        clean_text = clean_page_text(raw_text, repeating)
        page_number = index + 1
        quality = text_quality(raw_text)
        if int(quality["visible_chars"]) < MIN_TEXT_CHARS_PER_PAGE:
            warnings.append(
                {
                    "page_number": page_number,
                    "code": "LOW_TEXT_DENSITY",
                    "message": "本页可提取文字过少，可能是扫描页或空白页。",
                }
            )
        pages.append(
            {
                "page_number": page_number,
                "width": page_sizes[index]["width"],
                "height": page_sizes[index]["height"],
                "extractor": page_engines[index],
                "raw_char_count": len(raw_text),
                "clean_char_count": len(clean_text),
                "quality": quality,
                "raw_text": raw_text,
                "clean_text": clean_text,
                "canonical_text": canonical_page_text(clean_text),
            }
        )

    canonical_text, canonical_page_spans = build_canonical_text(pages)
    canonical_sha256 = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()
    payload: dict[str, object] = {
        "schema_version": "1.1",
        "source_file": pdf_path.name,
        "source_path": str(pdf_path),
        "source_sha256": sha256_file(pdf_path),
        "page_count": len(pages),
        "extractor_mode": engine,
        "extractors_used": sorted(set(page_engines)),
        "removed_repeating_margin_lines": sorted(repeating),
        "canonical_text_sha256": canonical_sha256,
        "canonical_char_count": len(canonical_text),
        "canonical_page_spans": canonical_page_spans,
        "warnings": warnings,
        "pages": pages,
    }

    status = extraction_status(warnings, len(pages))
    payload["status"] = status
    quality_report = {
        "source_file": pdf_path.name,
        "source_sha256": payload["source_sha256"],
        "status": status,
        "page_count": len(pages),
        "total_raw_chars": sum(int(page["raw_char_count"]) for page in pages),
        "total_clean_chars": sum(int(page["clean_char_count"]) for page in pages),
        "low_text_pages": [
            warning["page_number"]
            for warning in warnings
            if warning["code"] == "LOW_TEXT_DENSITY"
        ],
        "extractor_counts": dict(Counter(page_engines)),
        "removed_repeating_margin_lines": sorted(repeating),
        "warnings": warnings,
    }

    atomic_write_text(
        paths["json"], json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    )
    atomic_write_text(paths["raw"], render_text_file(pages, "raw_text"))
    atomic_write_text(paths["clean"], render_text_file(pages, "clean_text"))
    atomic_write_text(paths["canonical"], canonical_text)
    atomic_write_text(paths["canonical_map"], json.dumps({
        "source_file": pdf_path.name,
        "source_sha256": payload["source_sha256"],
        "canonical_text_sha256": canonical_sha256,
        "char_offset_rule": "0-based, char_end exclusive",
        "pages": canonical_page_spans,
    }, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(
        paths["quality"], json.dumps(quality_report, ensure_ascii=False, indent=2) + "\n"
    )
    return {
        "source": str(pdf_path),
        "page_count": len(pages),
        "status": status,
        "extractor_counts": quality_report["extractor_counts"],
        "warnings": warnings,
        "outputs": {name: str(path.resolve()) for name, path in paths.items()},
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="逐页提取保险条款 PDF，输出原始文本、清洗文本和页面 JSON。"
    )
    parser.add_argument("pdf", nargs="+", type=Path, help="一个或多个 PDF 文件")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("03_raw_text/raw_text"),
        help="输出目录，默认 03_raw_text/raw_text",
    )
    parser.add_argument("--force", action="store_true", help="覆盖已有输出")
    parser.add_argument(
        "--engine",
        choices=SUPPORTED_ENGINES,
        default="auto",
        help="文本提取引擎；auto 会在低文本页尝试 pypdf 回退",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    failures = 0
    for pdf_path in args.pdf:
        try:
            result = extract_pdf(
                pdf_path, args.output_dir, force=args.force, engine=args.engine
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as exc:  # CLI should continue with remaining files
            failures += 1
            print(f"[ERROR] {pdf_path}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
