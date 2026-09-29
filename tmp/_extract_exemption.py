import io, sys, re, glob, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def norm(s):
    return re.sub(r'\s+', '', s)

files = {}
for f in glob.glob('03_raw_text/raw_text/*.canonical.txt'):
    base = os.path.basename(f).replace('.canonical.txt', '')
    files[base] = f

# lead-in phrases (verbatim, minus trailing colon variance)
leads = {
    '东方嘉富东方尊4.0': '因下列情形之一导致被保险人身故或全残的',
    '太保鑫相伴': '因下列情形之一导致被保险人身故的',
    '富泽泽瑞一生': '因下列情形之一导致被保险人身故或全残的',
    '恒安标准传世瑞盈B款': '因下列情形之一导致被保险人身故的',
    '新华人寿': '因下列情形之一导致被保险人身故或身体全残的',
}

for stem, lead in leads.items():
    matches = [p for k, p in files.items() if stem in k]
    path = matches[0]
    txt = open(path, encoding='utf-8-sig').read()
    # find lead-in, normalize whitespace for locating
    idx = norm(txt).find(norm(lead))
    if idx < 0:
        print('NOT FOUND', stem)
        continue
    # extract from the lead-in to ~600 chars after (or to next 条款 heading)
    seg = txt[idx: idx + 900]
    print('=' * 70)
    print(stem)
    print('-' * 70)
    print(seg)
