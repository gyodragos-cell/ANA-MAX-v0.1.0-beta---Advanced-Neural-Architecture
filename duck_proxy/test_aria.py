import re
with open('dom.html', 'r', encoding='utf-8') as f:
    html = f.read()
    labels = list(set(re.findall(r'aria-label="([^"]*)"', html)))
    for lbl in labels:
        print(lbl.encode('ascii', 'ignore').decode())
