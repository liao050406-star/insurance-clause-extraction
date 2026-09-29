"""Structure-first, source-grounded chunking for Chinese insurance clauses.

Stage 1 recovers numbered policy sections. Stage 2 splits only oversized sections
at sentence/newline boundaries. Every result keeps exact offsets into one canonical
text, making later LLM quotations mechanically verifiable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator


TITLE_HINTS = sorted({
    "意外身故或意外全残豁免保险费", "身故保险金或全残保险金",
    "基本保险金额和年度有效保险金额", "基本保险金额和有效保险金额",
    "本公司合同解除权的限制", "我们合同解除权的限制", "您解除合同的手续及风险",
    "第二投保人申请变更投保人的要求", "撤销已指定的第二投保人",
    "指定第二投保人的方式", "指定第二投保人", "减少基本保险金额",
    "未成年人身故保险金限制", "未成年人身故保险金", "明确说明与如实告知",
    "合同效力的中止及恢复", "效力中止与恢复", "保单红利的确定",
    "保单红利的分配", "保单红利的领取", "保险费自动垫交", "保险事故通知",
    "保险金申请", "保险金给付", "宣告死亡处理", "年龄性别错误的处理",
    "年龄错误的处理", "其他需要关注的事项", "其他责任免除", "其他免责条款",
    "合同成立与生效", "合同内容变更", "联系方式变更", "保险费的支付",
    "基本保险金额", "有效保险金额", "保险金额", "保险期间", "保险责任", "责任免除", "投保范围", "合同构成",
    "合同终止", "犹豫期", "等待期", "保单贷款", "现金价值", "减额交清",
    "减保", "宽限期", "效力中止", "效力恢复", "受益人", "诉讼时效",
    "未还款项", "争议处理", "全残释义", "保单年度", "保单周年日",
    "保险费约定支付日", "周岁", "有效身份证件", "意外伤害", "全残",
    "已交保险费", "交费期满日", "毒品", "酒后驾驶", "无合法有效驾驶证驾驶",
    "无合法有效行驶证", "机动车", "战争", "军事冲突", "暴乱", "医疗机构",
    "鉴定机构", "利息", "释义",
}, key=len, reverse=True)

ARTICLE_RE = re.compile(r"^\s*(?P<number>\d+(?:\.\d+)+)\s*[.．、]?\s*(?P<rest>.*)$")
TOP_RE = re.compile(r"^\s*(?P<number>\d+)\s*[.．]\s*(?P<rest>.*)$")
CN_RE = re.compile(r"^\s*第(?P<number>[一二三四五六七八九十百千万零〇两\d]+)(?P<kind>条|章|节|部分)\s*(?P<rest>[^。；;]{0,40})\s*$")
REVERSED_ARTICLE_RE = re.compile(r"^\s*(?P<title>[^\d。；;]{2,24})\s+(?P<number>\d+(?:\.\d+)+)\s+(?P<rest>.+)$")
TOC_RE = re.compile(r"(?P<number>\d+(?:\.\d+)+)\s+(?P<title>.+?)(?=(?:\s{2,}|\s)(?:\d+(?:\.\d+)+|\d+\.)\s+|$)")
SENTENCE_RE = re.compile(r"[^。！？!?；;\n]*(?:[。！？!?；;]+|\n+|$)")


@dataclass(frozen=True)
class SourceLine:
    page: int
    text: str
    start: int
    end: int


@dataclass
class Builder:
    article_no: str | None
    title: str
    heading_type: str
    category: str
    lines: list[SourceLine] = field(default_factory=list)

    def result(self, index: int, source: str) -> dict[str, object]:
        start, end = self.lines[0].start, self.lines[-1].end
        text = source[start:end]
        return {
            "section_id": f"section_{index:03d}", "article_no": self.article_no,
            "title": self.title, "heading_type": self.heading_type,
            "category": self.category, "page_start": min(x.page for x in self.lines),
            "page_end": max(x.page for x in self.lines), "char_start": start,
            "char_end": end, "text": text, "line_count": len(self.lines),
            "char_count": len(text),
        }


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text).strip("：:。；;，,、")


def hinted_title(rest: str) -> str | None:
    value = compact(rest)
    # Prefer a complete known title.  Prefix recovery is only a fallback for
    # headings split by a narrow title column.
    for title in TITLE_HINTS:
        if value.startswith(title):
            return title
    for title in TITLE_HINTS:
        # A narrow first column may cut the title after only a few characters and
        # immediately continue with body text. Six leading CJK characters are enough
        # for the domain-specific hints used here; longest hints are checked first.
        prefix_len = min(6, len(title))
        if prefix_len >= 4 and value.startswith(title[:prefix_len]):
            return title
    return None


def fallback_title(rest: str) -> str:
    value = re.split(r"[：:。；;，,（(]|\s{2,}", rest.strip(), maxsplit=1)[0]
    return value[:32] or "未命名条款"


def category(title: str) -> str:
    groups = [
        ("exclusions", ("免除", "免责")), ("dividends", ("红利",)),
        ("eligibility", ("投保范围", "犹豫期")), ("premiums", ("保险费的支付", "宽限期")),
        ("policy_rights", ("现金价值", "贷款", "减保", "减额交清", "自动垫交", "效力", "第二投保人")),
        ("coverage_and_benefits", ("保险责任", "等待期", "保险期间", "保险金额")),
        ("claims", ("受益人", "保险事故通知", "保险金申请", "保险金给付", "宣告死亡", "诉讼时效")),
        ("definitions", ("释义", "周岁", "意外伤害", "全残", "已交保险费")),
        ("contract", ("合同构成", "合同成立", "合同终止")),
    ]
    return next((name for name, words in groups if any(w in title for w in words)), "other")


def find_body_start_page(pages: list[dict[str, object]]) -> int:
    for page in pages:
        # Insurers use both “在本条款中” and “在本保险条款中”.  This marker is
        # substantially more reliable than numbered lines on multi-column TOCs,
        # where entries such as “1.1 合同构成” otherwise look like body headings.
        if re.search(r"在本(?:保险\s*)?条款中", str(page.get("clean_text", ""))):
            return int(page["page_number"])
    for page in pages:
        text = str(page.get("clean_text", ""))
        numbered = [x for x in text.splitlines() if ARTICLE_RE.match(x.strip())]
        body_like = any(len(x) >= 35 or "本合同" in x for x in numbered)
        if numbered and (body_like or (len(numbered) <= 4 and len(text) >= 250)):
            return int(page["page_number"])
    return 1


def toc_titles(pages: list[dict[str, object]], body_page: int) -> dict[str, str]:
    result: dict[str, str] = {}
    for page in pages:
        if int(page["page_number"]) >= body_page:
            break
        for line in str(page.get("clean_text", "")).splitlines():
            for match in TOC_RE.finditer(line):
                title = compact(match.group("title"))
                if 1 <= len(title) <= 32:
                    result.setdefault(match.group("number"), title)
    return result


def canonicalize(pages: list[dict[str, object]], body_page: int) -> tuple[str, list[SourceLine]]:
    parts: list[str] = []
    lines: list[SourceLine] = []
    offset = 0
    for page in pages:
        page_no = int(page["page_number"])
        if page_no < body_page:
            continue
        for raw in str(page.get("clean_text", "")).splitlines():
            line = raw.strip()
            if not line:
                continue
            if parts:
                parts.append("\n")
                offset += 1
            start = offset
            parts.append(line)
            offset += len(line)
            lines.append(SourceLine(page_no, line, start, offset))
    return "".join(parts), lines


def detect_heading(line: str, titles: dict[str, str]) -> tuple[str | None, str, str] | None:
    match = ARTICLE_RE.match(line)
    if match:
        no, rest = match.group("number"), match.group("rest")
        return no, hinted_title(rest) or titles.get(no) or fallback_title(rest), "article"
    match = CN_RE.match(line)
    if match:
        label = f"第{match.group('number')}{match.group('kind')}"
        return label, compact(match.group("rest")) or label, match.group("kind")
    # Some two-column policies extract headings as "保险责任 1.2 正文...".
    match = REVERSED_ARTICLE_RE.match(line)
    if match:
        no = match.group("number")
        title = hinted_title(match.group("title")) or titles.get(no)
        if title:
            return no, title, "article"
    # Plain "1." items are common inside benefit formulae and exclusion lists. They
    # are intentionally not promoted to sections without an explicit 第X章/部分 form.
    return None


def split_into_sections(pages: list[dict[str, object]]) -> tuple[int, str, list[dict[str, object]]]:
    body_page = find_body_start_page(pages)
    titles = toc_titles(pages, body_page)
    source, lines = canonicalize(pages, body_page)
    builders: list[Builder] = []
    current: Builder | None = None
    for line in lines:
        heading = detect_heading(line.text, titles)
        if heading:
            no, title, kind = heading
            current = Builder(no, title, kind, category(title))
            builders.append(current)
        elif current is None:
            current = Builder(None, "正文前置信息", "front_matter", "front_matter")
            builders.append(current)
        current.lines.append(line)
    return body_page, source, [b.result(i, source) for i, b in enumerate(builders, 1)]


def sentence_spans(text: str) -> list[tuple[int, int]]:
    spans = [m.span() for m in SENTENCE_RE.finditer(text) if m.end() > m.start() and m.group().strip()]
    return spans or ([(0, len(text))] if text else [])


def hard_split(text: str, start: int, end: int, limit: int) -> Iterator[tuple[int, int]]:
    cursor = start
    while end - cursor > limit:
        edge = cursor + limit
        newline = text.rfind("\n", cursor + 1, edge + 1)
        cut = newline + 1 if newline > cursor else edge
        yield cursor, cut
        cursor = cut
    if cursor < end:
        yield cursor, end


def bounded_spans(text: str, limit: int) -> list[tuple[int, int]]:
    units: list[tuple[int, int]] = []
    for start, end in sentence_spans(text):
        units.extend([(start, end)] if end - start <= limit else hard_split(text, start, end, limit))
    result: list[tuple[int, int]] = []
    current: tuple[int, int] | None = None
    for start, end in units:
        if current is None:
            current = (start, end)
        elif end - current[0] <= limit:
            current = (current[0], end)
        else:
            result.append(current)
            current = (start, end)
    if current:
        result.append(current)
    return result


def chunk_section(section: dict[str, object], max_chars: int, overlap: int) -> list[dict[str, object]]:
    text = str(section["text"])
    chunks: list[dict[str, object]] = []
    previous_end = 0
    base = int(section["char_start"])
    for index, (start, end) in enumerate(bounded_spans(text, max_chars), 1):
        if index > 1 and overlap:
            proposed = max(previous_end - overlap, 0)
            newline = text.find("\n", proposed, start)
            start = newline + 1 if newline >= 0 else proposed
            start = max(start, end - max_chars)
        value = text[start:end]
        chunks.append({
            "section_id": section["section_id"], "chunk_index": index,
            "article_no": section["article_no"], "title": section["title"],
            "category": section["category"], "page_start": section["page_start"],
            "page_end": section["page_end"], "char_start": base + start,
            "char_end": base + end, "text": value, "char_count": len(value),
        })
        previous_end = end
    return chunks


def build_chunks(sections: Iterable[dict[str, object]], max_chars: int, overlap: int) -> list[dict[str, object]]:
    result = [chunk for section in sections for chunk in chunk_section(section, max_chars, overlap)]
    for index, chunk in enumerate(result, 1):
        chunk["chunk_id"] = f"chunk_{index:03d}"
    return result


def validate_grounding(source: str, sections: list[dict[str, object]], chunks: list[dict[str, object]]) -> dict[str, object]:
    failures = []
    for item in [*sections, *chunks]:
        start, end = int(item["char_start"]), int(item["char_end"])
        if source[start:end] != item["text"]:
            failures.append(str(item.get("chunk_id") or item.get("section_id")))
    return {"status": "ok" if not failures else "failed", "total_items": len(sections) + len(chunks), "ungrounded_ids": failures}


def render_sections(sections: list[dict[str, object]]) -> str:
    return "\n\n".join(
        f"===== {s['section_id']} | {s['article_no'] or 'NO_ARTICLE'} | {s['title']} | pages {s['page_start']}-{s['page_end']} | chars {s['char_start']}-{s['char_end']} =====\n{s['text']}"
        for s in sections
    ).rstrip() + "\n"


def split_file(input_path: Path, output_dir: Path, max_chars: int, overlap: int, force: bool) -> dict[str, object]:
    payload = json.loads(input_path.resolve().read_text(encoding="utf-8"))
    pages = payload.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError(f"输入缺少非空 pages 数组: {input_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    name = input_path.name.removesuffix(".pages.json")
    json_path, text_path = output_dir / f"{name}.sections.json", output_dir / f"{name}.sections.txt"
    if not force and (json_path.exists() or text_path.exists()):
        raise FileExistsError(f"切分结果已存在，请使用 --force 覆盖: {name}")
    body_page, source, sections = split_into_sections(pages)
    article_sections = [s for s in sections if s["article_no"] is not None]
    split_warnings: list[dict[str, object]] = []
    if len(article_sections) < 3 and len(source) >= 2000:
        split_warnings.append({
            "code": "LOW_SECTION_COUNT",
            "message": "正文较长但识别到的条款不足3条；后续抽取应回退到完整canonical文本并人工复核。",
            "article_section_count": len(article_sections),
        })
    chunks = build_chunks(sections, max_chars, overlap)
    validation = validate_grounding(source, sections, chunks)
    if validation["status"] != "ok":
        raise RuntimeError(f"source grounding 校验失败: {validation['ungrounded_ids']}")
    output = {
        "schema_version": "2.0", "source_file": payload.get("source_file"),
        "source_sha256": payload.get("source_sha256"), "body_start_page": body_page,
        "canonical_text_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "canonical_char_count": len(source), "section_count": len(sections),
        "chunk_count": len(chunks), "max_chunk_chars": max_chars,
        "chunk_overlap_chars": overlap, "validation": validation,
        "warnings": split_warnings,
        "sections": sections, "chunks": chunks,
    }
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    text_path.write_text(render_sections(sections), encoding="utf-8")
    return {"input": str(input_path), "body_start_page": body_page, "section_count": len(sections), "chunk_count": len(chunks), "validation": validation, "outputs": {"json": str(json_path.resolve()), "text": str(text_path.resolve())}}


def main() -> int:
    parser = argparse.ArgumentParser(description="按保险条款层级切分并保留精确原文字符区间。")
    parser.add_argument("pages_json", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("04_chunk/sections"))
    parser.add_argument("--max-chars", type=int, default=6000)
    parser.add_argument("--overlap-chars", type=int, default=200)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.max_chars < 500 or not 0 <= args.overlap_chars < args.max_chars:
        print("[ERROR] max-chars >= 500，且 0 <= overlap-chars < max-chars", file=sys.stderr)
        return 2
    failures = 0
    for path in args.pages_json:
        try:
            print(json.dumps(split_file(path, args.output_dir, args.max_chars, args.overlap_chars, args.force), ensure_ascii=False, indent=2))
        except Exception as exc:
            failures += 1
            print(f"[ERROR] {path}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
