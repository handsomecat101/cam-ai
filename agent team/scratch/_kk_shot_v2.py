"""Chup man hinh GUI CamAI v2 (v2 co hang video mau + nut doi ngon ngu).

Chay SAU khi da mo GUI that:
    .venv\\Scripts\\python.exe _kk_shot_v2.py
"""

import ctypes
import sys
import time

from PIL import ImageGrab

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                       # noqa: BLE001
    pass

ctypes.windll.shcore.SetProcessDpiAwareness(2)
time.sleep(2.0)
im = ImageGrab.grab(all_screens=True)
duong_dan = r"H:\AI Project\cam-ai\_kiem_chung\gui_v2.png"
im.save(duong_dan)
print("SIZE", im.size)
print("DA LUU", duong_dan)