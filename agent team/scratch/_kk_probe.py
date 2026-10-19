import customtkinter as ctk
import gui
from gui import CamAIGui
ctk.set_appearance_mode("dark"); ctk.set_default_color_theme("dark-blue")
app = CamAIGui(); app.update()
def quet(w, path):
    chu = getattr(w, "_chu_vi", None)
    if chu is not None and chu not in gui.DICH_VI_EN and not any(chu.startswith(k) for k in gui._KHOA_DICH_TIEU):
        print("THIEU:", repr(chu), "|", type(w).__name__, "|", path, "|", w.winfo_class())
    for i, c in enumerate(w.winfo_children()):
        quet(c, path + "/" + type(c).__name__ + str(i))
quet(app, "root")
app.destroy()
