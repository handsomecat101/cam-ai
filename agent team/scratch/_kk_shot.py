import ctypes, time
from PIL import ImageGrab
ctypes.windll.shcore.SetProcessDpiAwareness(2)
time.sleep(1.5)
im = ImageGrab.grab(all_screens=True)
im.save(r'H:\AI Project\cam-ai\_kiem_chung\gui_moi.png')
print("SIZE", im.size)
