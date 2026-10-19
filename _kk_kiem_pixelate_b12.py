import cv2
import numpy as np

BASE = 'H:/AI Project/cam-ai/_kk_out/pc_audit/'


def first_frame(path):
    cap = cv2.VideoCapture(path)
    ok, f = cap.read()
    cap.release()
    return f if ok else None


a = first_frame(BASE + 'B8_min_face_40/ket_qua_ket_qua.mp4')
b = first_frame(BASE + 'B12_pixelate_vung/ket_qua_ket_qua.mp4')
print('kich thuoc A =', None if a is None else a.shape)
print('kich thuoc B =', None if b is None else b.shape)
if a is None or b is None:
    raise SystemExit('khong doc duoc video')

d = np.abs(a.astype(int) - b.astype(int)).sum(axis=2)
ys, xs = np.nonzero(d > 30)
print('so pixel khac nhieu >30 =', len(xs))
if len(xs):
    print('vung khac nhieu: x %d - %d | y %d - %d' % (xs.min(), xs.max(), ys.min(), ys.max()))
    print('trie do rong cao: x %.1f%% | y %.1f%%' % (100 * xs.max() / a.shape[1], 100 * ys.max() / a.shape[0]))
    # so vung khac nhieu co phai la 1 vung lien mach (pixelate) hay rai rac
    mask = (d > 30).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    print('so vung lien mach =', n - 1)
    for i in range(1, min(n, 6)):
        x, y, w, h, area = stats[i]
        print('  vung %d: x=%d y=%d w=%d h=%d area=%d' % (i, x, y, w, h, area))

print('--- vung.txt ---')
print(open('H:/AI Project/cam-ai/vung.txt', encoding='utf-8').read()[:400])
