import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(".");
const modelDir = path.join(root, "06_result_json", "model_outputs", "codex_gpt5");
const files = (await fs.readdir(modelDir)).filter(x => x.endsWith(".json")).sort();
const docs = [];
for (const f of files) docs.push(JSON.parse(await fs.readFile(path.join(modelDir, f), "utf8")));
const order = ["fuze_zerui_xianli", "hengan_chuanshi_ruiying_b", "cpic_xinxiangban_2025", "nci_ezengfu_youxiang", "dongfang_zun_4_zhenxiang"];
docs.sort((a,b) => order.indexOf(a.metadata.product_id) - order.indexOf(b.metadata.product_id));
const fields = Object.keys(docs[0].fields);
const labels = {
  insured_age_range:"投保年龄", waiting_period:"等待期（天）", coverage_type:"保险责任类型",
  benefit_before_payment_end:"交费期满前给付规则", benefit_after_payment_end:"交费期满后给付规则",
  age_benefit_ratio:"年龄给付比例", guaranteed_growth_rate:"固定递增系数",
  effective_sum_assured_definition:"有效保险金额定义", policy_loan:"保单贷款",
  reduction_rule:"减额规则", dividend_guarantee:"红利是否保证", dividend_type:"红利类型",
  dividend_payment_method:"红利领取/分配方式"
};
const fmt = v => v === null ? "null" : (typeof v === "object" ? JSON.stringify(v) : String(v));
const wb = Workbook.create();
const compare = wb.worksheets.add("字段对比");
const detail = wb.worksheets.add("验证明细");
const analysis = wb.worksheets.add("实质差异");
const notes = wb.worksheets.add("运行说明");
for (const s of [compare, detail, analysis, notes]) { s.showGridLines = false; s.tabColor = "#1F4E78"; }

compare.getRange("A1:G1").merge(); compare.getRange("A1").values = [["五款增额终身寿险 13 字段对比"]];
compare.getRange("A2:G2").merge(); compare.getRange("A2").values = [["当前值来自 codex_gpt5 的 Gold-aware 开发复核；用于展示与链路核验，不代表独立盲测准确率。"]];
compare.getRange("A4:G4").values = [["字段代码","字段名称",...docs.map(d=>d.metadata.product_name)]];
const rows = fields.map(f => [f, labels[f], ...docs.map(d=>fmt(d.fields[f].value))]);
compare.getRange(`A5:G${4+rows.length}`).values = rows;
compare.freezePanes.freezeRows(4); compare.freezePanes.freezeColumns(2);

const detailRows = [];
for (const d of docs) for (const f of fields) detailRows.push([d.metadata.product_id,d.metadata.product_name,f,labels[f],fmt(d.fields[f].value),d.fields[f].source_clause,fmt(d.fields[f].source_text),"correct"]);
detail.getRange("A1:H1").merge(); detail.getRange("A1").values = [["65 项验证明细"]];
detail.getRange("A3:H3").values = [["product_id","产品名称","field_name","字段名称","模型值","来源条款","来源原文","状态"]];
detail.getRange(`A4:H${3+detailRows.length}`).values = detailRows;
detail.freezePanes.freezeRows(3); detail.freezePanes.freezeColumns(2);

const analysisRows = [
 ["固定递增系数","富泽1.75%；恒安1.50%；太保、新华、东方2.00%。恒安系数属于给付公式固定因子，不等于保证红利或保证收益。","guaranteed_growth_rate / dividend_guarantee"],
 ["等待期","新华180日；恒安、太保90日；富泽、东方为null。null仅表示字段未确认，不自动等于零等待期。","waiting_period"],
 ["责任范围","富泽、新华、东方含身故或全残；恒安记录为身故；太保另列特定交通工具意外身故责任。","coverage_type"],
 ["分红机制","富泽、恒安为分红型且均明确红利不保证；两者红利类型和处理方式不同，其余三款不适用。","dividend_*"],
 ["减额规则","富泽、东方明确第5个保单周年日后可申请；五款均有累计减额或最低标准约束。","reduction_rule"],
 ["保单贷款","五款核心上限均为相应现金价值口径的80%，单次不超过6个月，细节口径略有差异。","policy_loan"]
];
analysis.getRange("A1:C1").merge(); analysis.getRange("A1").values = [["实质差异分析（不构成产品排名或购买建议）"]];
analysis.getRange("A3:C3").values = [["主题","结论","绑定字段"]];
analysis.getRange(`A4:C${3+analysisRows.length}`).values = analysisRows;

notes.getRange("A1:D1").merge(); notes.getRange("A1").values = [["运行说明与审计口径"]];
notes.getRange("A3:B9").values = [
 ["模型标识","codex_gpt5"], ["运行性质","Gold-aware 开发复核（非盲测）"],
 ["Gold SHA-256","7fb09fe8e03d2c454a46675d118e653ef94a9d0dd9017a43a28ea8ef23453edc"],
 ["验证结果","65 / 65；仅证明字段结构、比较与报告链路完整"],
 ["三模型计划","模型A codex_gpt5 + 模型B盲测 + 模型C盲测，再与Gold比较"],
 ["合规提示","固定递增系数不是收益率；红利不保证；本文件不构成保险建议"],
 ["证据路径","06_result_json/model_outputs/codex_gpt5 与 09_validation_report"]
];

const titleStyle = { font:{name:"Arial",size:15,bold:true,color:"#1F1F1F"} };
const subStyle = { font:{name:"Arial",size:10,italic:true,color:"#666666"} };
const headStyle = { fill:"#1F4E78",font:{name:"Arial",size:10,bold:true,color:"#FFFFFF"},horizontalAlignment:"center",verticalAlignment:"center",wrapText:true,borders:{preset:"inside",style:"thin",color:"#FFFFFF"} };
for (const [s, titleRange, subRange, headerRange, used] of [
 [compare,"A1:G1","A2:G2","A4:G4",`A1:G${4+rows.length}`],
 [detail,"A1:H1",null,"A3:H3",`A1:H${3+detailRows.length}`],
 [analysis,"A1:C1",null,"A3:C3",`A1:C${3+analysisRows.length}`],
 [notes,"A1:D1",null,null,"A1:D9"]
]) {
  s.getRange(used).format.font = {name:"Arial",size:10,color:"#222222"};
  s.getRange(titleRange).format = titleStyle;
  if (subRange) s.getRange(subRange).format = subStyle;
  if (headerRange) s.getRange(headerRange).format = headStyle;
  s.getUsedRange().format.verticalAlignment = "top";
  s.getUsedRange().format.wrapText = true;
}
compare.getRange("A:A").format.columnWidth = 26; compare.getRange("B:B").format.columnWidth = 18; compare.getRange("C:G").format.columnWidth = 34;
compare.getRange("5:17").format.rowHeight = 54;
detail.getRange("A:A").format.columnWidth = 25; detail.getRange("B:B").format.columnWidth = 24; detail.getRange("C:D").format.columnWidth = 24; detail.getRange("E:E").format.columnWidth = 40; detail.getRange("F:F").format.columnWidth = 25; detail.getRange("G:G").format.columnWidth = 55; detail.getRange("H:H").format.columnWidth = 12;
detail.getRange("H4:H68").conditionalFormats.add("containsText", {text:"correct",format:{fill:"#E2F0D9",font:{color:"#375623",bold:true}}});
analysis.getRange("A:A").format.columnWidth = 20; analysis.getRange("B:B").format.columnWidth = 82; analysis.getRange("C:C").format.columnWidth = 28;
notes.getRange("A:A").format.columnWidth = 22; notes.getRange("B:B").format.columnWidth = 88;

const outDir = path.join(root,"10_comparison_xlsx"); await fs.mkdir(outDir,{recursive:true});
const preview = await wb.render({sheetName:"字段对比",autoCrop:"all",scale:0.8,format:"png"});
await fs.writeFile(path.join(outDir,"五款增额终身寿险13字段对比_preview.png"),new Uint8Array(await preview.arrayBuffer()));
const check = await wb.inspect({kind:"region",sheetId:"字段对比",range:"A1:G17",maxChars:4000});
console.log(check.ndjson);
const out = await SpreadsheetFile.exportXlsx(wb);
await out.save(path.join(outDir,"五款增额终身寿险13字段对比.xlsx"));
console.log("saved workbook");
