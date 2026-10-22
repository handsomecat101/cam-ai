import ast
import os

ROOT = r"H:\AI Project\cam-ai"
FILES = [
    "cam_ai_core.py",
    "nhan_dien_nhanh.py",
    "_kk_kiem_toc_do.py",
    "_kk_kiem_bit_exact.py",
    "_kk_core_goc.py",
]
BOM = bytes([0xEF, 0xBB, 0xBF])
CR = bytes([13])
for f in FILES:
    p = os.path.join(ROOT, f)
    b = open(p, "rb").read()
    try:
        ast.parse(b.decode("utf-8"))
        ok = "ast OK"
    except Exception as e:
        ok = "AST LOI " + str(e)
    print(f"{f:24s} BOM={str(b[:3] == BOM):5s} CR={b.count(CR):<4d} {ok}")
