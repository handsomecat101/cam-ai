import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
p = 'gui.py'
b = open(p, 'rb').read()
print('bytes', len(b), 'CR', b.count(b'\r'), 'BOM', b[:3] == b'\xef\xbb\xbf')
s = b.decode('utf-8')
lines = s.split('\n')
print('lines', len(lines))
pat = re.compile(r'\bafter\(|after_cancel|overrideredirect|transparentcolor|update_idletasks|\.update\(|shadow|Configure|<Button|<Bind|geometry|wm_attributes|\btitle\(|grid_remove|grid\(|place\(|pack\(')
for i, l in enumerate(lines, 1):
    if pat.search(l):
        print(i, l.rstrip()[:170])