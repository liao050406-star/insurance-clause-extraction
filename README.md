# 增额终身寿险条款信息抽取

本项目完成 PDF 文本提取、章节切分、13字段提示词生成、模型结果校验、Gold 对比验证和五产品字段对比。当前五款产品均已进入65行 Gold：富泽泽瑞一生、恒安标准传世瑞盈B款、太保鑫相伴（2025）、新华E增福优享版和东方嘉富东方尊4.0。

## 环境

- Python 3.11 及以上
- Python 包：`pdfplumber`、`pypdf`、`pydantic`、`openpyxl`

命令均在项目根目录执行。Windows 终端若未注册 `python`，请使用实际 Python 可执行文件替换命令中的 `python`。

## 目录

- `01_PDF`：原始条款 PDF
- `03_raw_text/raw_text`：原始文本、清洗文本、canonical 文本、页级数据及质量报告
- `04_chunk/sections`：章节切分结果
- `05_LLM_Prompt_Schema`：历史Schema、正式13字段Schema、V3提示词和生成器
- `06_result_json`：模型返回、正式抽取结果、Gold 校验扩展字段和汇总结果
- `07_Pydantic校验`：Gold 对比校验程序及 JSON 结果
- `08_gold_csv对比/gold.csv`：人工确认的只读验收集
- `09_validation_report`：验证报告
- `10_comparison_xlsx`：五款产品字段对比表与实质差异分析
- `11_model_comparison`：三模型输出模板、外部模型盲测提示词、四方对比报告（`three_model_comparison.md`）与实质复核（`substantive_review.md`）

## 闭环运行

### 1. PDF 转文本

```powershell
python 02_PDF解析_PyMuPDF_pdfplumber/extract_pdf.py "01_PDF/条款文件.pdf" --output-dir 03_raw_text/raw_text --engine auto --force
```

程序输出 `raw.txt`、`clean.txt`、`canonical.txt`、`canonical.map.json`、`pages.json` 和 `quality.json`。引用校验以 canonical 文本及字符区间为准。

### 2. 章节切分

```powershell
python 04_chunk/split_sections.py "03_raw_text/raw_text/条款文件.pages.json" --output-dir 04_chunk/sections --force
```

### 3. 生成抽取提示词

```powershell
python 05_LLM_Prompt_Schema/llm_extract.py build "04_chunk/sections/条款文件.sections.json" --template 05_LLM_Prompt_Schema/prompts/v2_final.md --output-dir 05_LLM_Prompt_Schema/prompts/generated_final --force
```

最终版完整 Prompt 输出到 `05_LLM_Prompt_Schema/prompts/generated_final`。将模型返回的纯 JSON 保存到 `06_result_json/llm_responses`。本项目不使用 RAG；模型输入由最终版模板、字段定义、输出样例和相关条款正文组成。初版模板保留在 `prompts/v1_initial.md`，用于展示 Prompt 迭代过程。

### 4. 校验单份抽取结果

```powershell
python 05_LLM_Prompt_Schema/llm_extract.py validate "06_result_json/llm_responses/模型结果.json" --output-dir 06_result_json/extracted --force
```

校验器检查顶层结构、字段完整性、数据类型和枚举。条款未载明的字段必须为 `null`，不得推测。

### 5. 汇总通过结构校验的结果

当前五款结构校验结果位于 `06_result_json/extracted`：

```powershell
python 06_result_json/build_result.py --input-dir 06_result_json/extracted --output 06_result_json/result.json
```

预期输出：`document_count = 5`，`rejected_count = 0`。结构校验通过只表示 JSON 形状、字段和类型合法，不等同于字段事实已通过 Gold 验证。

### 6. 生成13字段V3盲测输入并验证

```powershell
python 05_LLM_Prompt_Schema/build_v3_prompts.py
python 07_Pydantic校验/validate_model_outputs.py --model-id codex_gpt5
```

新 Gold 包含五款产品、每款13字段，共65行。验证器只读 Gold，并在运行前后核对 SHA-256。`codex_gpt5` 文件是用于验证结构和报告链路的 Gold-aware 开发复核，不是独立盲测；模型B、C必须使用 `generated_v3` 输入独立运行。

### 7. 生成字段对比表

```powershell
python tmp/build_five_comparison.py
```

输出：`10_comparison_xlsx/五款增额终身寿险13字段对比.xlsx`。工作簿包含五款字段对比、Gold验证明细和差异分析，字段值可回溯到条款号及原文摘录。

## 当前验收结果

- 五款产品结构校验：5 个通过，0 个拒绝
- 新 Gold：65行，SHA-256 为 `e76ddd93c670b1581d686af81228273319b09b0a7a2f19ff1fa15cab38959942`
- 13字段结构链路验证：65/65，无错误、无缺失
- 上述100%仅代表 Gold-aware 开发复核链路，不作为独立模型准确率
- 模型B、C已按冻结V3提示词完成独立盲测：B=`claude_sonnet`、C=`claude_opus`；四方对比报告见 `11_model_comparison/three_model_comparison.md`
- 盲测严格准确率：`claude_sonnet` 52.31%（34/65）、`claude_opus` 58.46%（38/65）；`codex_gpt5` 的 100% 为 Gold 副本，不纳入盲测口径

本项目及输出仅用于条款信息整理与课程作业，不构成保险建议、产品推荐或产品排名。
