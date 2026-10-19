import cv2
import numpy as np

BASE = 'H:/AI Project/cam-ai/_kk_out/pc_audit/'
ZONE = (0.2, 0.15, 0.8, 0.95)  # theo vung.txt


def frame_at(path, idx):
    cap = cv2.VideoCapture(path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, f = cap.read()
    cap.release()
    return f if ok else None


for idx in (60,):
    a = frame_at(BASE + 'B8_min_face_40/ket_qua_ket_qua.mp4', idx)
    b = frame_at(BASE + 'B12_pixelate_vung/ket_qua_ket_qua.mp4', idx)
    h, w = a.shape[:2]
    x1, y1, x2, y2 = int(ZONE[0] * w), int(ZONE[1] * h), int(ZONE[2] * w), int(ZONE[3] * h)
    ca = a[y1:y2, x1:x2]
    cb = b[y1:y2, x1:x2]
    out = 'H:/AI Project/cam-ai/_kk_out/pc_audit/B12_pixelate_vung/so_sanh_vung_%d.png' % idx
    cv2.imwrite(out, np.hstack([ca, cb]))
    print('frame', idx, 'crop', ca.shape, '->', out)
    # do mat do pixel hoa: so pixel trung nhau theo hang
    g = cv2.cvtColor(cb, cv2.COLOR_BGR2GRAY)
    tang = np.abs(np.diff(g.astype(int), axis=1))
    print('  B12 trong vung: tb |dhac hang| = %.2f (pixel hoa -> cao)' % tang.mean())
    g2 = cv2.cvtColor(ca, cv2.COLOR_BGR2GRAY)
    tang2 = np.abs(np.diff(g2.astype(int), axis=1))
    print('  B8  trong vung: tb |dhac hang| = %.2f' % tang2.mean())
    print('  so pixel giong nhau trong vung: %d / %d' % (
        int((np.abs(ca.astype(int) - cb.astype(int)).sum(axis=2) < 10).sum()), ca.shape[0] * ca.shape[1]))
