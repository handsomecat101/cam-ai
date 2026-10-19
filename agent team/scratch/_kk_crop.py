from PIL import Image
im = Image.open(r'_kiem_chung\gui_moi.png')
crop = im.crop((36, 24, 1214, 842)).resize((1178*3//2, 818*3//2), Image.LANCZOS)
crop.save(r'_kiem_chung\gui_crop.png')
print("OK", crop.size)
