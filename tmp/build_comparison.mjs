import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = process.cwd();
const inputPath = `${root}/07_Pydantic校验/validation/validation_results.json`;
const outputPath = `${root}/10_comparison_xlsx/三款增额终身寿险字段对比.xlsx`;
const previewDir = `${root}/tmp/comparison_previews`;
const payload = JSON.parse(await fs.readFile(inputPath, "utf8"));

const fieldMeta = [
  ["insured_age_range", "投保年龄范围", "周岁"],
  ["benefit_age_band_coverage", "给付年龄分段覆盖", ""],
  ["hesitation_period_days", "犹豫期", "天"],
  ["insurance_period", "保险期间", ""],
  ["waiting_period_days", "等待期", "天"],
  ["coverage_scope", "保障范围", ""],
  ["fixed_insured_amount_annual_growth_rate", "固定保额年增长率", "比例"],
  ["insurance_amount_growth_mechanism", "保险金额增长机制", ""],
  ["is_participating", "是否分红", ""],
  ["grace_period_days", "宽限期", "天"],
  ["policy_loan_max_ratio", "保单贷款最高比例", "比例"],
  ["policy_loan_max_term_months", "保单贷款最长期限", "月"],
];
const products = [...new Set(payload.results.map((x) => x.product_name))];
const byKey = new Map(payload.results.map((x) => [`${x.product_name}\u0000${x.field_name}`, x]));
const sourceLabel = (item) => {
  const parts = (item.source_details || [])
    .filter((x) => x.source_clause)
    .map((x) => `第${x.source_clause}条${x.source_page ? `（PDF第${x.source_page}页）` : ""}`);
  return [...new Set(parts)].join("；") || "条款未载明";
};
const displayValue = (value, field) => {
  if (value === null || value === undefined) return "null";
  if (typeof value === "boolean") return value ? "是" : "否";
  if (field === "fixed_insured_amount_annual_growth_rate" || field === "policy_loan_max_ratio") {
    return value;
  }
  return value;
};

const workbook = Workbook.create();
const compare = workbook.worksheets.add("字段对比");
const detail = workbook.worksheets.add("校验明细");
const font = "Arial";
const navy = "#1F4E78";
const pale = "#DCE6F1";
const light = "#F5F7FA";
const border = "#D9E1E8";

compare.showGridLines = false;
compare.getRange("A1:H1").merge();
compare.getRange("A1").values = [["三款增额终身寿险字段对比"]];
compare.getRange("A1").format.font = { name: font, size: 16, bold: true, color: "#1F1F1F" };
compare.getRange("A2:H2").merge();
compare.getRange("A2").values = [["数值来自抽取结果；条款出处已通过 Gold 原文、哈希及字符区间校验。null 表示条款未载明或不适用。"]];
compare.getRange("A2").format.font = { name: font, size: 10, italic: true, color: "#666666" };

const compareHeader = ["字段", "单位"];
for (const product of products) compareHeader.push(product, "条款出处");
const compareRows = [compareHeader];
for (const [field, label, unit] of fieldMeta) {
  const row = [label, unit];
  for (const product of products) {
    const item = byKey.get(`${product}\u0000${field}`);
    row.push(displayValue(item?.predicted_value, field), sourceLabel(item || {}));
  }
  compareRows.push(row);
}
compare.getRange(`A4:H${3 + compareRows.length}`).values = compareRows;
compare.getRange("A4:H4").format = {
  fill: navy,
  font: { name: font, size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#FFFFFF" },
};
compare.getRange("A5:H16").format.font = { name: font, size: 10, color: "#222222" };
compare.getRange("A5:H16").format.verticalAlignment = "top";
compare.getRange("A5:H16").format.wrapText = true;
compare.getRange("A5:H16").format.borders = { preset: "inside", style: "thin", color: border };
for (let row = 5; row <= 16; row += 2) compare.getRange(`A${row}:H${row}`).format.fill = light;
compare.getRange("A5:A16").format.font = { name: font, size: 10, bold: true, color: "#1F1F1F" };
compare.getRange("B5:B16").format.horizontalAlignment = "center";
compare.getRange("C11:C11").format.numberFormat = "0.00%";
compare.getRange("E11:E11").format.numberFormat = "0.00%";
compare.getRange("G11:G11").format.numberFormat = "0.00%";
compare.getRange("C15:C15").format.numberFormat = "0%";
compare.getRange("E15:E15").format.numberFormat = "0%";
compare.getRange("G15:G15").format.numberFormat = "0%";
compare.getRange("A4:A16").format.columnWidth = 24;
compare.getRange("B4:B16").format.columnWidth = 10;
compare.getRange("C4:C16").format.columnWidth = 28;
compare.getRange("D4:D16").format.columnWidth = 21;
compare.getRange("E4:E16").format.columnWidth = 28;
compare.getRange("F4:F16").format.columnWidth = 21;
compare.getRange("G4:G16").format.columnWidth = 28;
compare.getRange("H4:H16").format.columnWidth = 21;
compare.getRange("A1:H2").format.rowHeight = 24;
compare.getRange("A4:H4").format.rowHeight = 42;
compare.getRange("A5:H16").format.autofitRows();
compare.freezePanes.freezeRows(4);
compare.freezePanes.freezeColumns(2);

detail.showGridLines = false;
detail.getRange("A1:I1").merge();
detail.getRange("A1").values = [["字段级校验与条款追溯"]];
detail.getRange("A1").format.font = { name: font, size: 16, bold: true, color: "#1F1F1F" };
detail.getRange("A2:I2").merge();
detail.getRange("A2").values = [[`共 ${payload.summary.gold_fields} 个字段；正确 ${payload.summary.correct}；准确率 ${(payload.summary.accuracy * 100).toFixed(2)}%。`]];
detail.getRange("A2").format.font = { name: font, size: 10, italic: true, color: "#666666" };
const detailRows = [["产品", "字段代码", "字段名称", "预测值", "校验结果", "条款号", "PDF页码", "原文摘录", "原文匹配"]];
const labelByField = new Map(fieldMeta.map(([code, label]) => [code, label]));
for (const item of payload.results) {
  const sources = (item.source_details || []).filter((x) => x.source_clause);
  detailRows.push([
    item.product_name,
    item.field_name,
    labelByField.get(item.field_name) || item.field_name,
    displayValue(item.predicted_value, item.field_name),
    item.result,
    sources.map((x) => x.source_clause).join("；") || "",
    sources.map((x) => x.source_page ?? "").join("；"),
    sources.map((x) => x.source_text || "").join("\n") || "条款未载明",
    item.source_result,
  ]);
}
detail.getRange(`A4:I${3 + detailRows.length}`).values = detailRows;
detail.getRange("A4:I4").format = {
  fill: navy,
  font: { name: font, size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#FFFFFF" },
};
detail.getRange("A5:I40").format.font = { name: font, size: 10, color: "#222222" };
detail.getRange("A5:I40").format.verticalAlignment = "top";
detail.getRange("A5:I40").format.wrapText = true;
detail.getRange("A5:I40").format.borders = { preset: "inside", style: "thin", color: border };
detail.getRange("E5:E40").format.fill = "#E2F0D9";
detail.getRange("A4:A40").format.columnWidth = 30;
detail.getRange("B4:B40").format.columnWidth = 35;
detail.getRange("C4:C40").format.columnWidth = 22;
detail.getRange("D4:D40").format.columnWidth = 25;
detail.getRange("E4:E40").format.columnWidth = 13;
detail.getRange("F4:F40").format.columnWidth = 13;
detail.getRange("G4:G40").format.columnWidth = 11;
detail.getRange("H4:H40").format.columnWidth = 72;
detail.getRange("I4:I40").format.columnWidth = 19;
detail.getRange("A4:I4").format.rowHeight = 30;
detail.getRange("A5:I40").format.autofitRows();
detail.freezePanes.freezeRows(4);
detail.freezePanes.freezeColumns(3);

await fs.mkdir(`${root}/10_comparison_xlsx`, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });
const comparisonPreview = await workbook.render({ sheetName: "字段对比", range: "A1:H16", scale: 1, format: "png" });
await fs.writeFile(`${previewDir}/字段对比.png`, new Uint8Array(await comparisonPreview.arrayBuffer()));
const detailPreview = await workbook.render({ sheetName: "校验明细", range: "A1:I16", scale: 1, format: "png" });
await fs.writeFile(`${previewDir}/校验明细.png`, new Uint8Array(await detailPreview.arrayBuffer()));

const checkCompare = await workbook.inspect({ kind: "table", range: "字段对比!A1:H16", include: "values,formulas", tableMaxRows: 20, tableMaxCols: 10 });
console.log(checkCompare.ndjson);
const checkErrors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 100 }, summary: "final formula error scan" });
console.log(checkErrors.ndjson);
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({ outputPath, sheets: ["字段对比", "校验明细"], rows: payload.summary.gold_fields }));
