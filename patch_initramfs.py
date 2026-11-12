from PIL import Image
import struct

im = Image.open(r'C:\Users\ARUMUGAM\Downloads\workshop-reference.png').convert('RGBA')
if im.size != (1280, 720):
    im = im.resize((1280, 720), Image.Resampling.LANCZOS)

magic = b'W21W'
hdr = magic + struct.pack('<II', 1280, 720)
pixels = im.tobytes()
raw_wallpaper = hdr + pixels

cpio = bytearray(open(r'E:\jarvis\clipperx-initramfs.cpio', 'rb').read())
for target in [b'share/wallpapers/aurora.raw', b'share/wallpapers/bloom.raw', b'share/wallpapers/dune.raw']:
    idx = cpio.find(target)
    if idx != -1:
        h = cpio[idx-110:idx]
        namesize = int(h[94:102], 16)
        filesize = int(h[54:62], 16)
        start = (idx - 110) + 110 + namesize + ((4 - ((110 + namesize) % 4)) % 4)
        cpio[start:start+filesize] = raw_wallpaper
        print('Replaced', target.decode())

open(r'E:\jarvis\jarvis-initramfs.cpio', 'wb').write(cpio)
print('Wrote E:\jarvis\jarvis-initramfs.cpio successfully')
