import re

s = open('H:/AI Project/cam-ai/app.py', encoding='utf-8').read()
fl = sorted(set(re.findall(r'"(--[a-z0-9\-]+)"', s)))
print('SO CO:', len(fl))
for f in fl:
    print(f)
