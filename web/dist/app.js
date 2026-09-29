'use strict';
const state = { group: 'all', query: '' };
let lastTrigger = null;

const groups = {
  coverage: ['insured_age_range', 'waiting_period', 'coverage_type'],
  benefit: ['benefit_before_payment_end', 'benefit_after_payment_end', 'age_benefit_ratio', 'guaranteed_growth_rate', 'effective_sum_assured_definition'],
  rights: ['policy_loan', 'reduction_rule'],
  dividend: ['dividend_guarantee', 'dividend_type', 'dividend_payment_method'],
};
const labels = { insured_age_range: '投保年龄', waiting_period: '等待期', coverage_type: '保险责任', benefit_before_payment_end: '交费期满前给付', benefit_after_payment_end: '交费期满后给付', age_benefit_ratio: '年龄给付比例', guaranteed_growth_rate: '固定递增系数', effective_sum_assured_definition: '有效保险金额', policy_loan: '保单贷款', reduction_rule: '减额规则', dividend_guarantee: '红利是否保证', dividend_type: '红利类型', dividend_payment_method: '红利领取方式' };
const short = { insured_age_range: '年龄边界', waiting_period: '天', coverage_type: '责任名称', benefit_before_payment_end: '计算规则', benefit_after_payment_end: '计算规则', age_benefit_ratio: '分段比例', guaranteed_growth_rate: '小数', effective_sum_assured_definition: '定义', policy_loan: '比例与期限', reduction_rule: '申请与限额', dividend_guarantee: '布尔/不适用', dividend_type: '类型', dividend_payment_method: '方式' };
const keyLabels = { under_18: '未满18周岁', adult_before_payment_end: '成年且交费期满前', adult_after_payment_end: '成年且交费期满后', rule: '运算', part1: '第一部分', part2: '第二部分', condition: '适用条件', max_cash_value_ratio: '现金价值上限', max_term_months: '最长月数', insured_consent_required: '需被保险人同意', after_free_look_period: '犹豫期后', basis: '计算基数' };
const modelName = { codex_gpt5: '模型 A · codex_gpt5', claude_sonnet: '模型 B · claude_sonnet', claude_opus: '模型 C · claude_opus' };

const STATUS = {
  correct: { tag: '✓', label: '一致', cls: 'st-correct' },
  equivalent: { tag: '≈', label: '语义等价', cls: 'st-equivalent' },
  substantive: { tag: '✗', label: '实质分歧', cls: 'st-substantive' },
  missing: { tag: '—', label: '缺失', cls: 'st-missing' },
};

function stringify(v) { return v === null ? 'null' : typeof v === 'object' ? JSON.stringify(v, null, 0) : String(v); }
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
function textOf(t) { return Array.isArray(t) ? t.join('\n') : (t || '该字段没有可引用原文。'); }

function pretty(v, key) {
  if (v === null) return '<span class="null">null</span>';
  if (key === 'guaranteed_growth_rate') {
    const s = (v * 100).toFixed(2).replace(/\.?0+$/, '');
    return `<span class="number">${s}%</span>`;
  }
  if (key === 'waiting_period') return `<span class="number">${v}</span> 天`;
  if (typeof v === 'boolean') return v ? '是' : '否';
  if (Array.isArray(v)) return `<span class="tag-list">${v.map(x => `<i>${escapeHtml(x)}</i>`).join('')}</span>`;
  if (typeof v === 'object') return `<span class="kv-list">${Object.entries(v).map(([k, x]) => `<span><b>${escapeHtml(keyLabels[k] || k)}</b>${escapeHtml(typeof x === 'boolean' ? (x ? '是' : '否') : stringify(x))}</span>`).join('')}</span>`;
  return escapeHtml(stringify(v));
}

function productScore(p) {
  return SITE_DATA.models.map(m => {
    let n = 0;
    SITE_DATA.fields.forEach(f => { if (p.fields[f].models[m.id].status === 'correct') n++; });
    return `${m.letter}${n}`;
  }).join('  ');
}

function matches(f) {
  const q = state.query.trim().toLowerCase();
  if (!q) return true;
  const hay = [f, labels[f], ...SITE_DATA.products.map(p => {
    let s = stringify(p.fields[f].gold.value);
    SITE_DATA.models.forEach(m => { s += stringify(p.fields[f].models[m.id].value); });
    return s;
  })].join(' ').toLowerCase();
  return hay.includes(q);
}

function visibleFields() {
  const allowed = state.group === 'all' ? SITE_DATA.fields : groups[state.group];
  return allowed.filter(matches);
}

function fieldCell(f) {
  return `<th class="field-cell" scope="row" data-f="${f}">${labels[f]}<small>${f} · ${short[f]}</small></th>`;
}
function goldCell(p, f) {
  return `<td class="val-cell gold-col" data-product="${p.id}" data-field="${f}" data-model="gold" role="button" tabindex="0"><span class="val-body">${pretty(p.fields[f].gold.value, f)}</span><span class="cell-status gold-tag">基准</span></td>`;
}
function modelCell(p, f, mid) {
  const m = p.fields[f].models[mid];
  const st = STATUS[m.status];
  return `<td class="val-cell cell-${m.status}" data-product="${p.id}" data-field="${f}" data-model="${mid}" role="button" tabindex="0"><span class="val-body">${pretty(m.value, f)}</span><span class="cell-status ${st.cls}">${st.tag} ${st.label}</span></td>`;
}
function productCell(p, n) {
  return `<th class="product-cell" scope="rowgroup" rowspan="${n}"><span class="p-name">${escapeHtml(p.shortName)}</span><span class="p-sub">${escapeHtml(p.name)}</span><span class="p-score">${productScore(p)}</span></th>`;
}

function render() {
  const head = document.querySelector('#matrix-head');
  head.innerHTML = `<tr><th class="head-product" scope="col">产品</th><th class="head-field" scope="col">字段</th><th class="head-gold" scope="col">Gold 基准</th>${SITE_DATA.models.map(m => `<th scope="col">模型 ${m.letter}<small>${m.blind ? '独立盲测' : '开发复核'}</small></th>`).join('')}</tr>`;

  const fields = visibleFields();
  document.querySelector('#visible-count').textContent = `${fields.length} / 13`;
  const body = document.querySelector('#matrix-body');
  body.innerHTML = fields.length
    ? SITE_DATA.products.map(p => fields.map((f, i) =>
        `<tr>${i === 0 ? productCell(p, fields.length) : ''}${fieldCell(f)}${goldCell(p, f)}${SITE_DATA.models.map(m => modelCell(p, f, m.id)).join('')}</tr>`
      ).join('')).join('')
    : `<tr><td colspan="6"><div class="empty">没有匹配字段。请清除检索词或切换分组。</div></td></tr>`;

  body.querySelectorAll('.val-cell').forEach(td => {
    td.addEventListener('click', () => { lastTrigger = td; showEvidence(td.dataset.product, td.dataset.field, td.dataset.model); });
    td.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); td.click(); } });
  });
}

function setText(sel, txt) { document.querySelector(sel).textContent = txt; }

function showEvidence(pid, f, modelKey) {
  const p = SITE_DATA.products.find(x => x.id === pid);
  const field = p.fields[f];
  const panel = document.querySelector('#evidence-panel');
  setText('#evidence-product', p.shortName);
  setText('#evidence-field', labels[f]);
  const cmp = document.querySelector('#evidence-compare');
  if (modelKey === 'gold') {
    setText('#evidence-view', 'Gold 基准');
    setText('#evidence-value', stringify(field.gold.value));
    setText('#evidence-clause', field.gold.clause || '条款未载明');
    setText('#evidence-text', textOf(field.gold.text));
    cmp.hidden = true;
  } else {
    const m = field.models[modelKey];
    const st = STATUS[m.status];
    setText('#evidence-view', modelName[modelKey]);
    setText('#evidence-value', stringify(m.value));
    setText('#evidence-clause', m.clause || '未提供来源条款号');
    setText('#evidence-text', textOf(m.text));
    cmp.hidden = false;
    const gv = document.querySelector('#evidence-gold-value');
    gv.textContent = stringify(field.gold.value);
    gv.className = 'gold-chip ' + st.cls;
    setText('#evidence-gold-status', st.label);
  }
  panel.hidden = false;
  document.querySelector('.close-evidence').focus();
}
function closeEvidence() { document.querySelector('#evidence-panel').hidden = true; if (lastTrigger?.isConnected) lastTrigger.focus(); }

function renderModelLab() {
  const name = { codex_gpt5: 'codex_gpt5', claude_sonnet: 'claude_sonnet', claude_opus: 'claude_opus' };
  const parts = [];
  SITE_DATA.models.forEach((m, i) => {
    if (i) parts.push('<div class="connector" aria-hidden="true"></div>');
    const role = m.blind ? '独立盲测' : '开发复核 · 非盲测';
    const acc = `严格 ${(m.accuracy * 100).toFixed(2)}% · 实质 ${(m.subst_accuracy * 100).toFixed(2)}%`;
    const note = m.blind ? `${m.correct}/65 严格正确 · ${m.equivalent} 语义等价 · ${m.substantive} 实质分歧` : '65/65 结构链路通过（Gold 副本，无泛化意义）';
    parts.push(`<article class="model ${m.blind ? 'blind' : 'dev'}"><div class="model-index">${m.letter}</div><div class="model-body"><h3>${escapeHtml(name[m.id])}</h3><p class="role">${role}</p><p class="note">${note}</p><strong class="acc">${acc}</strong></div><span class="badge">${m.blind ? '盲测完成' : '非盲测'}</span></article>`);
  });
  document.querySelector('#model-track').innerHTML = parts.join('');
}

function renderSubstantive() {
  const shortName = Object.fromEntries(SITE_DATA.products.map(p => [p.id, p.shortName]));
  const modelOf = { codex_gpt5: '模型 A', claude_sonnet: '模型 B', claude_opus: '模型 C' };
  document.querySelector('#substantive-list').innerHTML = SITE_DATA.substantive.map(s =>
    `<article class="sub-item"><div class="sub-tags"><span>${escapeHtml(shortName[s.product] || s.product)}</span><span>${escapeHtml(labels[s.field] || s.field)}</span><span class="sub-model">${escapeHtml(modelOf[s.model] || s.model)}</span></div><p>${escapeHtml(s.reason)}</p></article>`
  ).join('');
}

/* ---- 顶部：产品 × 对比项目 实质差异表 + 速览报告 ---- */
function renderCompare() {
  const items = SITE_DATA.compare.items;
  const nCol = SITE_DATA.products.length + 1;
  document.querySelector('#compare-head').innerHTML =
    `<tr><th class="cmp-item-head" scope="col">对比项目</th>${SITE_DATA.products.map(p => `<th scope="col"><span class="cmp-name">${escapeHtml(p.shortName)}</span><span class="cmp-full">${escapeHtml(p.name)}</span></th>`).join('')}</tr>`;
  document.querySelector('#compare-body').innerHTML = items.map(it => {
    const badge = it.highlight ? '<span class="diff-badge">实质差异</span>' : '';
    const cells = SITE_DATA.products.map(p => {
      const v = it.cells[p.id] ?? '—';
      const clause = it.clauses[p.id] || '未载明';
      return `<td class="${it.highlight ? 'cmp-diff' : ''}"><span class="cmp-val">${escapeHtml(v)}</span><span class="cmp-clause">${escapeHtml(clause)}</span></td>`;
    }).join('');
    const row = `<tr class="${it.highlight ? 'diff-row' : ''}"><th scope="row"><span class="cmp-label">${escapeHtml(it.label)}</span>${badge}</th>${cells}</tr>`;
    const why = it.highlight ? `<tr class="why-row"><td colspan="${nCol}"><span class="why-mark">差异要点</span>${escapeHtml(it.why)}</td></tr>` : '';
    return row + why;
  }).join('');
}

function renderCompareReport() {
  document.querySelector('#compare-report').innerHTML = SITE_DATA.compare.report.map((r, i) =>
    `<article class="cmp-finding"><div class="mark">${String(i + 1).padStart(2, '0')}</div><div><h3>${escapeHtml(r.title)}</h3><p>${escapeHtml(r.text)}</p></div><button class="cmp-link" data-field="${r.fields.split(' ')[0]}">定位字段</button></article>`
  ).join('');
  document.querySelectorAll('.cmp-link').forEach(b => b.addEventListener('click', () => {
    state.group = 'all'; state.query = '';
    document.querySelector('#field-search').value = '';
    document.querySelector('.filter.active').classList.remove('active');
    document.querySelector('[data-group="all"]').classList.add('active');
    render();
    const row = document.querySelector(`[data-f="${b.dataset.field}"]`)?.closest('tr');
    row?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    row?.classList.add('row-highlight'); setTimeout(() => row?.classList.remove('row-highlight'), 1600);
  }));
}

/* ---- wiring ---- */
document.querySelectorAll('.filter').forEach(b => b.addEventListener('click', () => {
  document.querySelector('.filter.active').classList.remove('active'); b.classList.add('active'); state.group = b.dataset.group; render();
}));
document.querySelector('#field-search').addEventListener('input', e => { state.query = e.target.value; render(); });
document.addEventListener('keydown', e => {
  if (e.key === '/' && document.activeElement.tagName !== 'INPUT') { e.preventDefault(); document.querySelector('#field-search').focus(); }
  if (e.key === 'Escape') closeEvidence();
});
document.querySelector('.close-evidence').addEventListener('click', closeEvidence);
document.querySelector('#reset-btn').addEventListener('click', () => {
  state.group = 'all'; state.query = '';
  document.querySelector('#field-search').value = '';
  document.querySelector('.filter.active').classList.remove('active'); document.querySelector('[data-group="all"]').classList.add('active');
  document.querySelector('#evidence-panel').hidden = true;
  render();
});
document.querySelector('#finding-list').innerHTML = SITE_DATA.findings.map((f, i) =>
  `<article class="finding"><div class="mark">${String(i + 1).padStart(2, '0')}</div><h3>${escapeHtml(f.title)}</h3><p>${escapeHtml(f.text)}</p><button class="finding-link" data-field="${f.fields.split(' ')[0]}">定位 ${escapeHtml(f.fields)}</button></article>`
).join('');
document.querySelectorAll('.finding-link').forEach(b => b.addEventListener('click', () => {
  state.group = 'all'; state.query = '';
  document.querySelector('#field-search').value = '';
  document.querySelector('.filter.active').classList.remove('active'); document.querySelector('[data-group="all"]').classList.add('active');
  render();
  const row = document.querySelector(`[data-f="${b.dataset.field}"]`)?.closest('tr');
  row?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  row?.classList.add('row-highlight'); setTimeout(() => row?.classList.remove('row-highlight'), 1600);
}));

renderCompare();
renderCompareReport();
renderModelLab();
renderSubstantive();
render();
