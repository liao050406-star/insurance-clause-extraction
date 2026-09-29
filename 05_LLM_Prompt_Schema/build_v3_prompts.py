from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "05_LLM_Prompt_Schema" / "增额终身寿险13字段Schema.md").read_text(encoding="utf-8")
TPL = (ROOT / "05_LLM_Prompt_Schema" / "prompts" / "v3_gold_schema.md").read_text(encoding="utf-8")
MAPPING = {
    "fuze_zerui_xianli": "富泽泽瑞一生（献礼版）终身寿险（分红型）",
    "hengan_chuanshi_ruiying_b": "恒安标准传世瑞盈B款终身寿险（分红型）条款",
    "cpic_xinxiangban_2025": "自选-太保鑫相伴（2025）终身寿险",
    "nci_ezengfu_youxiang": "自选-新华人寿《E增福优享版终身寿险（互联网）》",
    "dongfang_zun_4_zhenxiang": "东方嘉富东方尊4.0（臻享版）终身寿险条款",
}


def main() -> None:
    out = ROOT / "05_LLM_Prompt_Schema" / "prompts" / "generated_v3"
    out.mkdir(parents=True, exist_ok=True)
    for pid, stem in MAPPING.items():
        source = ROOT / "04_chunk" / "sections" / f"{stem}.sections.txt"
        text = TPL.replace("{{PRODUCT_ID}}", pid).replace("{{FIELD_SPEC_13}}", SCHEMA)
        text = text.replace("{{SOURCE_FILE}}", source.name).replace("{{CLAUSE_TEXT}}", source.read_text(encoding="utf-8"))
        (out / f"{pid}__v3_prompt.md").write_text(text, encoding="utf-8")
    print(f"wrote {len(MAPPING)} prompts to {out}")


if __name__ == "__main__":
    main()
