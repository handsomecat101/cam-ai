import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
p = 'cam_ai_core.py'
s = open(p, 'rb').read().decode('utf-8')
lines = s.split('\n')
print('lines', len(lines))
pat = re.compile(r'^class |^def |^    def |putText|rectangle|polylines|imencode|imencode|cv2\.putText|cv2\.rectangle|draw_|ve_|annotat')
for i, l in enumerate(lines, 1):
    if pat.search(l):
        print(i, l.rstrip()[:170])