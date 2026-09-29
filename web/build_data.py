import json, csv, sys
from pathlib import Path
from collections import Counter

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "tmp"))
from build_model_comparison import SUBSTANTIVE, norm, parse_value, FIELDS  # noqa: E402

order = ['fuze_zerui_xianli', 'hengan_chuanshi_ruiying_b', 'cpic_xinxiangban_2025',
         'nci_ezengfu_youxiang', 'dongfang_zun_4_zhenxiang']
short = {'fuze_zerui_xianli': '富泽泽瑞', 'hengan_chuanshi_ruiying_b': '恒安瑞盈B',
         'cpic_xinxiangban_2025': '太保鑫相伴', 'nci_ezengfu_youxiang': '新华E增福',
         'dongfang_zun_4_zhenxiang': '东方尊4.0'}
MODEL_IDS = [('codex_gpt5', 'A', False), ('claude_sonnet', 'B', True), ('claude_opus', 'C', True)]

gold_rows = list(csv.DictReader((root / '08_gold_csv对比/gold.csv').open('r', encoding='utf-8-sig', newline='')))
gold = {(r['product_id'], r['field_name']): parse_value(r['gold_value']) for r in gold_rows}
gold_src = {(r['product_id'], r['field_name']): (r['source_clause'], r['source_text']) for r in gold_rows}
product_names = {r['product_id']: r['product_name'] for r in gold_rows}
gold_sha = 'e76ddd93c670b1581d686af81228273319b09b0a7a2f19ff1fa15cab38959942'


def load(model_id):
    d = root / '06_result_json' / 'model_outputs' / model_id
    out = {}
    for p in sorted(d.glob('*.json')):
        data = json.loads(p.read_text(encoding='utf-8'))
        out[data['metadata']['product_id']] = data['fields']
    return out


models = {mid: load(mid) for mid, _, _ in MODEL_IDS}


def status(pid, f, mid):
    p = models[mid].get(pid, {}).get(f)
    if p is None:
        return 'missing'
    got = p.get('value')
    if norm(got) == norm(gold[(pid, f)]):
        return 'correct'
    if (pid, f, mid) in SUBSTANTIVE:
        return 'substantive'
    return 'equivalent'


products = []
for pid in order:
    fields = {}
    for f in FIELDS:
        sc, st = gold_src[(pid, f)]
        mvals = {}
        for mid, _, _ in MODEL_IDS:
            p = models[mid].get(pid, {}).get(f)
            mvals[mid] = {
                'value': p.get('value') if p else None,
                'clause': p.get('source_clause') if p else None,
                'text': p.get('source_text') if p else None,
                'status': status(pid, f, mid),
            }
        fields[f] = {'gold': {'value': gold[(pid, f)], 'clause': sc, 'text': st}, 'models': mvals}
    products.append({'id': pid, 'name': product_names[pid], 'shortName': short[pid], 'fields': fields})

model_summary = []
for mid, letter, blind in MODEL_IDS:
    c = Counter(status(pid, f, mid) for pid in order for f in FIELDS)
    total = len(order) * len(FIELDS)
    correct, equiv, subst, missing = c['correct'], c['equivalent'], c['substantive'], c['missing']
    model_summary.append({
        'id': mid, 'letter': letter, 'blind': blind,
        'correct': correct, 'equivalent': equiv, 'substantive': subst, 'missing': missing,
        'accuracy': correct / total, 'subst_accuracy': (correct + equiv) / total,
    })

findings = [
    {'title': '固定递增系数', 'text': '富泽为1.75%；恒安为1.50%；太保、新华、东方为2.00%。恒安系数属于给付公式固定因子，不等于保证红利或保证收益。', 'fields': 'guaranteed_growth_rate · dividend_guarantee'},
    {'title': '等待期', 'text': '新华180日；恒安、太保90日；富泽、东方为null。null仅表示本字段未确认，不自动等于零等待期。', 'fields': 'waiting_period'},
    {'title': '责任范围', 'text': '富泽、新华、东方包含身故或全残；恒安记录为身故；太保另列特定交通工具意外身故保险金。', 'fields': 'coverage_type'},
    {'title': '分红机制', 'text': '富泽、恒安为分红型且均明确红利不保证；两者红利类型和处理方式不同，其余三款对应字段不适用。', 'fields': 'dividend_guarantee · dividend_type'},
    {'title': '减额规则', 'text': '富泽、东方明确第5个保单周年日后可申请；五款均存在累计减额或最低标准约束。', 'fields': 'reduction_rule'},
    {'title': '保单贷款', 'text': '五款贷款上限均为相应现金价值口径的80%，单次期限不超过6个月，欠款扣除及犹豫期表述存在差别。', 'fields': 'policy_loan'},
]

# ---- curated substantive comparison (top-of-page 产品×对比项目 table + mini report) ----
# 手写整理的“实质差异”速览：把 13 字段压成可横向比较的一行话，并标记哪些属于实质差异。
# 单元格只做忠实压缩、不新增结论；“差异要点”给出谁与谁不同、差在哪。
COMPARE_ITEMS = [
    {'field': 'insured_age_range', 'label': '投保年龄', 'highlight': True,
     'why': '太保按性别分别设定上限（女75/男71周岁）且上限最高；恒安未载明；其余为单一 0–70 或 0–75 周岁区间。',
     'cells': {'fuze_zerui_xianli': '0–70周岁（出生满28日）', 'hengan_chuanshi_ruiying_b': '未载明（null）',
               'cpic_xinxiangban_2025': '女0–75 / 男0–71周岁（满30日）', 'nci_ezengfu_youxiang': '0–70周岁（出生满30日）',
               'dongfang_zun_4_zhenxiang': '0–75周岁（出生满28日）'}},
    {'field': 'waiting_period', 'label': '等待期', 'highlight': True,
     'why': '新华180日为最长；恒安、太保90日；富泽、东方未载明。null 仅表示未确认，不等于零等待期。',
     'cells': {'fuze_zerui_xianli': '未载明（null）', 'hengan_chuanshi_ruiying_b': '90日',
               'cpic_xinxiangban_2025': '90日', 'nci_ezengfu_youxiang': '180日',
               'dongfang_zun_4_zhenxiang': '未载明（null）'}},
    {'field': 'coverage_type', 'label': '保险责任', 'highlight': True,
     'why': '富泽、新华、东方含全残责任；恒安仅列身故；太保另列特定客运交通工具意外身故保险金。',
     'cells': {'fuze_zerui_xianli': '身故或全残', 'hengan_chuanshi_ruiying_b': '身故',
               'cpic_xinxiangban_2025': '身故 + 特定交通工具意外身故', 'nci_ezengfu_youxiang': '身故或身体全残',
               'dongfang_zun_4_zhenxiang': '身故或全残'}},
    {'field': 'benefit_before_payment_end', 'label': '交费期满前给付', 'highlight': True,
     'why': '恒安把红利保险金额拆成独立部分并与主给付求和；其余四款均为「保费/现价」取大结构。',
     'cells': {'fuze_zerui_xianli': '取大：保费（×比例）/现价', 'hengan_chuanshi_ruiying_b': '两项之和：主给付 + 红利现价',
               'cpic_xinxiangban_2025': '取大：保费（×比例）/现价', 'nci_ezengfu_youxiang': '取大：保费（×系数）/现价',
               'dongfang_zun_4_zhenxiang': '取大：保费（×比例）/现价'}},
    {'field': 'benefit_after_payment_end', 'label': '交费期满后给付', 'highlight': True,
     'why': '恒安为「初始保额与红利保额分别按1.015增长后求和」；其余四款在保费、现价、保额三者中取大。',
     'cells': {'fuze_zerui_xianli': '取大：保费×比例 / 现价 / 当年度保额', 'hengan_chuanshi_ruiying_b': '两项之和：初始保额与红利保额分别×1.015增长',
               'cpic_xinxiangban_2025': '取大：保费×比例 / 现价 / 有效保额', 'nci_ezengfu_youxiang': '取大：保费×系数 / 现价 / 基本保额×1.02^(n-1)',
               'dongfang_zun_4_zhenxiang': '取大：有效保额 / 保费×比例 / 现价'}},
    {'field': 'age_benefit_ratio', 'label': '年龄给付比例', 'highlight': True,
     'why': '恒安边界整体后移一岁（18-41/42-61/62+）；富泽、恒安含未满18周岁1.0档，其余三款不含。',
     'cells': {'fuze_zerui_xianli': '0-17→1.0 · 18-40→1.6 · 41-60→1.4 · 61+→1.2',
               'hengan_chuanshi_ruiying_b': '0-17→1.0 · 18-41→1.6 · 42-61→1.4 · 62+→1.2',
               'cpic_xinxiangban_2025': '≤40→1.6 · 41-60→1.4 · 61+→1.2',
               'nci_ezengfu_youxiang': '18-40→1.6 · 41-60→1.4 · 61+→1.2',
               'dongfang_zun_4_zhenxiang': '≤40→1.6 · 41-60→1.4 · 61+→1.2'}},
    {'field': 'guaranteed_growth_rate', 'label': '固定递增系数', 'highlight': True,
     'why': '三种系数并存；恒安1.50%是给付公式中的固定因子，不代表保证红利或保证收益。',
     'cells': {'fuze_zerui_xianli': '1.75%', 'hengan_chuanshi_ruiying_b': '1.50%',
               'cpic_xinxiangban_2025': '2.00%', 'nci_ezengfu_youxiang': '2.00%',
               'dongfang_zun_4_zhenxiang': '2.00%'}},
    {'field': 'effective_sum_assured_definition', 'label': '有效保险金额', 'highlight': True,
     'why': '恒安为「初始保额+累计红利保额」累加定义；新华引用条款公式；其余为固定比例逐年递增。',
     'cells': {'fuze_zerui_xianli': '首年=基本保额，此后×1.0175逐年递增', 'hengan_chuanshi_ruiying_b': '初始保额 + 各年度累计红利保额',
               'cpic_xinxiangban_2025': '生效=基本保额，每满一年×1.02递增', 'nci_ezengfu_youxiang': '依基本保额及第五条，期满后×1.02^(n-1)',
               'dongfang_zun_4_zhenxiang': '首年=基本保额，次年起×1.02'}},
    {'field': 'policy_loan', 'label': '保单贷款', 'highlight': False,
     'why': '五款上限均为现金价值口径80%、单次≤6个月；是否写明「犹豫期后」「扣除欠款后余额」存在措辞差别。',
     'cells': {'fuze_zerui_xianli': '80% · 6个月 · 需同意 · 犹豫期后', 'hengan_chuanshi_ruiying_b': '80% · 6个月 · 需同意 · 扣欠款后余额',
               'cpic_xinxiangban_2025': '80% · 6个月 · 需同意 · 犹豫期后+扣欠款', 'nci_ezengfu_youxiang': '80% · 6个月 · 需同意 · 犹豫期后+扣欠款',
               'dongfang_zun_4_zhenxiang': '80% · 6个月 · 需同意 · 扣欠款后余额'}},
    {'field': 'reduction_rule', 'label': '减额规则', 'highlight': True,
     'why': '富泽、东方须第5个保单周年日后方可申请；恒安按初始/红利保额同比例减少；五款均设年度累计减额或最低保额约束。',
     'cells': {'fuze_zerui_xianli': '第5周年起可减 · 年度减额现价≤累计保费20%', 'hengan_chuanshi_ruiying_b': '初始/红利保额同比例减 · 年度≤20%',
               'cpic_xinxiangban_2025': '年度减基本保额≤20% · 减后保费≥最低', 'nci_ezengfu_youxiang': '年度减基本保额≤20% · 减后保费≥最低',
               'dongfang_zun_4_zhenxiang': '第5周年起可减 · 年度减额现价≤已付保费20%'}},
    {'field': 'dividend_guarantee', 'label': '红利是否保证', 'highlight': True,
     'why': '仅分红型的富泽、恒安载明红利不保证；其余三款为非分红，字段不适用。',
     'cells': {'fuze_zerui_xianli': '否（红利不保证）', 'hengan_chuanshi_ruiying_b': '否（红利不保证）',
               'cpic_xinxiangban_2025': '不适用（null）', 'nci_ezengfu_youxiang': '不适用（null）',
               'dongfang_zun_4_zhenxiang': '不适用（null）'}},
    {'field': 'dividend_type', 'label': '红利类型', 'highlight': True,
     'why': '恒安区分年度红利与终了红利；富泽未单独载明类型；其余三款不适用。',
     'cells': {'fuze_zerui_xianli': '未载明', 'hengan_chuanshi_ruiying_b': '年度红利 · 终了红利',
               'cpic_xinxiangban_2025': '不适用（null）', 'nci_ezengfu_youxiang': '不适用（null）',
               'dongfang_zun_4_zhenxiang': '不适用（null）'}},
    {'field': 'dividend_payment_method', 'label': '红利领取方式', 'highlight': True,
     'why': '富泽提供三种领取方式；恒安按红利类型分别约定；其余三款不适用。',
     'cells': {'fuze_zerui_xianli': '现金领取 · 累积生息 · 购买交清增额', 'hengan_chuanshi_ruiying_b': '年度红利增额计息 · 终了红利现金支付',
               'cpic_xinxiangban_2025': '不适用（null）', 'nci_ezengfu_youxiang': '不适用（null）',
               'dongfang_zun_4_zhenxiang': '不适用（null）'}},
]

# 每个对比项目附条款依据（来自 Gold 的 source_clause），保证结论可追溯。
compare_items = []
for it in COMPARE_ITEMS:
    clauses = {pid: (gold_src.get((pid, it['field']), ('', ''))[0] or '未载明') for pid in order}
    compare_items.append({**it, 'clauses': clauses})

COMPARE_REPORT = [
    {'title': '递增系数三档并存', 'text': '富泽1.75%、恒安1.50%、其余三款2.00%。恒安系数是给付公式固定因子，不等于保证红利或保证收益。', 'fields': 'guaranteed_growth_rate'},
    {'title': '等待期与责任范围分化', 'text': '新华等待期180日最长、恒安与太保90日、富泽与东方未载明；责任范围上太保额外含特定交通工具意外身故，恒安仅身故。', 'fields': 'waiting_period coverage_type'},
    {'title': '给付结构两种范式', 'text': '恒安把红利保险金额拆出、与主给付求和；其余四款在保费、现金价值、保额三者中取大。', 'fields': 'benefit_before_payment_end benefit_after_payment_end'},
    {'title': '分红机制仅两款', 'text': '富泽、恒安为分红型且均明确红利不保证，领取方式与红利类型不同；其余三款对应字段不适用。', 'fields': 'dividend_guarantee dividend_type dividend_payment_method'},
    {'title': '年龄边界与投保年龄差异', 'text': '恒安给付比例边界整体后移一岁；太保按性别分列投保年龄上限；恒安投保年龄未载明。', 'fields': 'age_benefit_ratio insured_age_range'},
    {'title': '减额与贷款规则', 'text': '富泽、东方减额须第5个保单周年日后；保单贷款五款高度一致（80%、6个月），仅措辞细节有别。', 'fields': 'reduction_rule policy_loan'},
]

substantive = [{'product': pid, 'field': f, 'model': mid, 'reason': reason}
               for (pid, f, mid), reason in SUBSTANTIVE.items()]

payload = {'fields': FIELDS, 'products': products, 'models': model_summary,
           'findings': findings, 'substantive': substantive, 'gold_sha': gold_sha,
           'compare': {'items': compare_items, 'report': COMPARE_REPORT}}
(root / 'web/dist/data.js').write_text('const SITE_DATA=' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
print('generated web/dist/data.js with', len(products), 'products ×', len(FIELDS), 'fields × 4 views')
