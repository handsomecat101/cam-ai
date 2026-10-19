from PIL import Image
im = Image.open(r"H:\AI Project\cam-ai\_kiem_chung\gui_v2.png")
# vung chu trang thai ben canh thanh tien trinh
hop = im.crop((1140, 838, 1250, 864)).resize((110*6, 26*6), Image.LANCZOS)
hop.save(r"H:\AI Project\cam-ai\_kiem_chung\_zoom_trang_thai.png")
print("OK", hop.size)
