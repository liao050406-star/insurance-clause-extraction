import io, sys, unicodedata, re, glob, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def norm(s):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', s))

files = {}
for f in glob.glob('03_raw_text/raw_text/*.canonical.txt'):
    base = os.path.basename(f).replace('.canonical.txt', '')
    files[base] = f

checks = {
    '东方嘉富东方尊4.0': ['身故或全残保险金', '因下列情形之一导致被保险人身故或全残的'],
    '太保鑫相伴': ['身故保险金', '特定客运交通工具意外身故保险金', '因下列情形之一导致被保险人身故的'],
    '富泽泽瑞一生': ['身故或全残保险金', '交清增额保险对应的身故或全残保险金', '因下列情形之一导致被保险人身故或全残的'],
    '恒安标准传世瑞盈B款': ['身故保险金', '因下列情形之一导致被保险人身故的'],
    '新华人寿': ['身故或身体全残保险金', '因下列情形之一导致被保险人身故或身体全残的'],
}

for stem, phrases in checks.items():
    matches = [p for k, p in files.items() if stem in k]
    if not matches:
        print('NO FILE for', stem)
        continue
    path = matches[0]
    txt = norm(open(path, encoding='utf-8-sig').read())
    print(stem, '->', os.path.basename(path))
    for p in phrases:
        print('    ', 'OK ' if norm(p) in txt else 'MISS', p)
