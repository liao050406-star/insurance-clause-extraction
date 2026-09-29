import io, sys, re, glob, os, unicodedata
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def norm(s):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', s))

import csv
rows = list(csv.DictReader(io.open('08_gold_csv对比/gold_verbatim.csv', encoding='utf-8-sig')))

# only 免责原文 rows
for r in rows:
    if r['item_type'] != '免责原文':
        continue
    pid, name, gold = r['product_id'], r['product_name'], r['gold_text']
    # find canonical
    canon = None
    for f in glob.glob('03_raw_text/raw_text/*.canonical.txt'):
        base = os.path.basename(f).replace('.canonical.txt', '')
        if pid == 'fuze_zerui_xianli' and '富泽' in base: canon = f
        if pid == 'hengan_chuanshi_ruiying_b' and '恒安' in base: canon = f
        if pid == 'cpic_xinxiangban_2025' and '太保' in base: canon = f
        if pid == 'nci_ezengfu_youxiang' and '新华' in base: canon = f
        if pid == 'dongfang_zun_4_zhenxiang' and '东方' in base: canon = f
    if not canon:
        print(pid, 'NO CANON'); continue
    ct = norm(open(canon, encoding='utf-8-sig').read())
    gt = norm(gold)
    print('='*60)
    print(pid, '| gold_norm len', len(gt), '| in canon:', gt in ct)
    if gt not in ct:
        # find longest common prefix
        i = 0
        while i < min(len(gt), len(ct)) and gt[i] == ct[i]:
            i += 1
        # but the mismatch may be at a later offset; find first index where gt is not a substring
        # simple: try to find longest prefix of gt that IS in ct
        lo, hi = 0, len(gt)
        # binary search longest prefix present
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if gt[:mid] in ct:
                lo = mid
            else:
                hi = mid - 1
        print('longest prefix present:', lo, '/', len(gt))
        print('gold   next:', repr(gt[lo:lo+40]))
        # find where that prefix ends in ct
        j = ct.find(gt[:lo])
        print('canon  next:', repr(ct[j+lo:j+lo+40]))
