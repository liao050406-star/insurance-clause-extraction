"""Build LLM extraction prompts and validate manually returned extraction JSON.

This module intentionally does not require an API key. The course permits using a web or
desktop LLM manually, while code remains responsible for preparing context and validating
the returned JSON. The prompt, model response, and validated output therefore remain
separate artifacts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PRODUCT_FIELDS = {
    # 文本字段同样必须允许 null：条款未载明时不能为了通过类型校验而补写。
    "保险公司": (str, type(None)),
    "产品名称": (str, type(None)),
    "保险期间": (str, type(None)),
    "投保年龄": (str, type(None)),
    "等待期天数": (int, type(None)),
    "犹豫期天数": (int, type(None)),
    "宽限期天数": (int, type(None)),
    "保额递增比例": (int, float, type(None)),
    "递增起始保单年度": (int, type(None)),
    "红利领取方式": (str, type(None)),
    "保单贷款比例": (int, float, type(None)),
    "减保起始保单年度": (int, type(None)),
    "减保年度上限比例": (int, float, type(None)),
}

RESPONSIBILITY_FIELDS = {
    "责任名称": str,
    "责任类型": str,
    "必选或可选": str,
    "给付基准": str,
    "给付方式": (str, type(None)),
    "已交保费给付比例上限": (int, float, type(None)),
    "单次给付限额": (int, float, type(None)),
    "保障终止年龄": (int, type(None)),
    "行使条件": (str, type(None)),
    "是否受责任免除约束": (str, type(None)),
    "赔付说明": str,
    "出处": str,
}

EXCLUSION_FIELDS = {
    "适用范围": str,
    "免责条数": int,
    "原文": str,
    "出处": str,
    "值得关注的条目": str,
}

REQUIRED_TOP_LEVEL = {"产品信息", "保险责任", "责任免除", "其他免责提示"}
ALLOWED_PAYMENT_METHODS = {"取较大者", "定额给付", None}
ALLOWED_REQUIREDNESS = {"必选", "可选"}
ALLOWED_EXCLUSION_VALUES = {"是", "否", None}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def relevant_sections(payload: dict[str, Any]) -> list[dict[str, Any]]:
    categories = {
        "front_matter",
        "contract",
        "eligibility",
        "coverage_and_benefits",
        "exclusions",
        "dividends",
        "premiums",
        "policy_rights",
        "definitions",
    }
    return [section for section in payload["sections"] if section["category"] in categories]


def render_clause_context(sections: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for section in sections:
        article = section.get("article_no") or "正文前置信息"
        blocks.append(
            f"### {article} {section['title']}（PDF第{section['page_start']}-"
            f"{section['page_end']}页）\n{section['text']}"
        )
    return "\n\n".join(blocks)


def build_prompt(
    sections_path: Path,
    template_path: Path,
    structure_path: Path,
    sample_path: Path,
    output_dir: Path,
    force: bool,
) -> Path:
    section_payload = json.loads(read_text(sections_path))
    template = read_text(template_path)
    replacements = {
        "{{FIELD_SPEC}}": read_text(structure_path),
        "{{OUTPUT_SAMPLE}}": read_text(sample_path),
        "{{SOURCE_FILE}}": str(section_payload.get("source_file", sections_path.name)),
        "{{CLAUSE_TEXT}}": render_clause_context(relevant_sections(section_payload)),
    }
    prompt = template
    for marker, value in replacements.items():
        prompt = prompt.replace(marker, value)
    unresolved = re.findall(r"\{\{[A-Z_]+\}\}", prompt)
    if unresolved:
        raise ValueError(f"提示词仍有未替换占位符: {sorted(set(unresolved))}")

    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = sections_path.name.removesuffix(".sections.json")
    output_path = output_dir / f"{base_name}.prompt.md"
    if output_path.exists() and not force:
        raise FileExistsError(f"提示词已存在，请使用 --force 覆盖: {output_path}")
    output_path.write_text(prompt.rstrip() + "\n", encoding="utf-8")
    return output_path


def strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else stripped


def check_exact_fields(
    obj: dict[str, Any], expected: dict[str, Any], location: str, errors: list[str]
) -> None:
    missing = set(expected) - set(obj)
    extra = set(obj) - set(expected)
    if missing:
        errors.append(f"{location} 缺少字段: {sorted(missing)}")
    if extra:
        errors.append(f"{location} 存在额外字段: {sorted(extra)}")
    for field, expected_type in expected.items():
        if field in obj and not isinstance(obj[field], expected_type):
            errors.append(
                f"{location}.{field} 类型错误: {type(obj[field]).__name__}"
            )


def validate_result(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["顶层必须是 JSON 对象"]

    missing = REQUIRED_TOP_LEVEL - set(data)
    extra = set(data) - REQUIRED_TOP_LEVEL
    if missing:
        errors.append(f"顶层缺少字段: {sorted(missing)}")
    if extra:
        errors.append(f"顶层存在额外字段: {sorted(extra)}")

    product = data.get("产品信息")
    if isinstance(product, dict):
        check_exact_fields(product, PRODUCT_FIELDS, "产品信息", errors)
        for field in ("保额递增比例", "保单贷款比例", "减保年度上限比例"):
            value = product.get(field)
            if value is not None and value < 0:
                errors.append(f"产品信息.{field} 不能为负数")
    else:
        errors.append("产品信息必须是对象")

    responsibilities = data.get("保险责任")
    if isinstance(responsibilities, list) and responsibilities:
        for index, item in enumerate(responsibilities):
            location = f"保险责任[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{location} 必须是对象")
                continue
            check_exact_fields(item, RESPONSIBILITY_FIELDS, location, errors)
            if item.get("必选或可选") not in ALLOWED_REQUIREDNESS:
                errors.append(f"{location}.必选或可选 枚举值错误")
            if item.get("给付方式") not in ALLOWED_PAYMENT_METHODS:
                errors.append(f"{location}.给付方式 枚举值错误")
            if item.get("是否受责任免除约束") not in ALLOWED_EXCLUSION_VALUES:
                errors.append(f"{location}.是否受责任免除约束 枚举值错误")
    else:
        errors.append("保险责任必须是非空数组")

    exclusions = data.get("责任免除")
    if isinstance(exclusions, dict):
        check_exact_fields(exclusions, EXCLUSION_FIELDS, "责任免除", errors)
    else:
        errors.append("责任免除必须是对象")

    if data.get("其他免责提示") is not None and not isinstance(data.get("其他免责提示"), str):
        errors.append("其他免责提示必须是字符串或 null")
    return errors


def validate_and_save(response_path: Path, output_dir: Path, force: bool) -> tuple[Path, list[str]]:
    raw = strip_markdown_fence(read_text(response_path))
    data = json.loads(raw)
    errors = validate_result(data)
    if errors:
        return Path(), errors

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{response_path.stem}.json"
    if output_path.exists() and not force:
        raise FileExistsError(f"输出已存在，请使用 --force 覆盖: {output_path}")
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path, []


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成字段抽取提示词或校验 LLM 返回的 JSON。")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="从章节 JSON 生成完整抽取提示词")
    build.add_argument("sections_json", nargs="+", type=Path)
    build.add_argument("--template", type=Path, default=Path("05_LLM_Prompt_Schema/prompts/v1_initial.md"))
    build.add_argument(
        "--structure",
        type=Path,
        default=Path("05_LLM_Prompt_Schema/增额终身寿险Schema.md"),
    )
    build.add_argument(
        "--sample",
        type=Path,
        default=Path("05_LLM_Prompt_Schema/样例_中英鑫悦未来5号至臻版.json"),
    )
    build.add_argument("--output-dir", type=Path, default=Path("05_LLM_Prompt_Schema/prompts/generated"))
    build.add_argument("--force", action="store_true")

    validate = subparsers.add_parser("validate", help="校验并保存 LLM 返回的 JSON")
    validate.add_argument("response_json", nargs="+", type=Path)
    validate.add_argument("--output-dir", type=Path, default=Path("06_result_json/extracted"))
    validate.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    failures = 0
    if args.command == "build":
        for path in args.sections_json:
            try:
                output = build_prompt(
                    path,
                    args.template,
                    args.structure,
                    args.sample,
                    args.output_dir,
                    args.force,
                )
                print(output.resolve())
            except Exception as exc:
                failures += 1
                print(f"[ERROR] {path}: {exc}", file=sys.stderr)
    else:
        for path in args.response_json:
            try:
                output, errors = validate_and_save(path, args.output_dir, args.force)
                if errors:
                    failures += 1
                    print(f"[INVALID] {path}", file=sys.stderr)
                    for error in errors:
                        print(f"  - {error}", file=sys.stderr)
                else:
                    print(output.resolve())
            except Exception as exc:
                failures += 1
                print(f"[ERROR] {path}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
