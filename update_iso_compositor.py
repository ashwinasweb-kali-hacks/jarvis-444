import struct

cpio = bytearray(open('jarvis-initramfs.cpio', 'rb').read())
target = b'bin/w12-compositor'
idx = cpio.find(target)
assert idx != -1

h = cpio[idx-110:idx]
namesize = int(h[94:102], 16)
filesize = int(h[54:62], 16)
start = (idx - 110) + 110 + namesize + ((4 - ((110 + namesize) % 4)) % 4)

new_data = open('patched_w12', 'rb').read()
assert len(new_data) == filesize, f'Size mismatch {len(new_data)} vs {filesize}'
cpio[start:start+filesize] = new_data
open('jarvis-initramfs.cpio', 'wb').write(cpio)
print('Updated jarvis-initramfs.cpio with patched w12-compositor')

# Now patch into JARVIS-OS.iso
import pycdlib
src_iso = r'C:\Users\ARUMUGAM\Downloads\clipperx.iso'
dst_iso = r'E:\jarvis\JARVIS-OS.iso'

raw_src = bytearray(open(src_iso, 'rb').read())
src = pycdlib.PyCdlib()
src.open(src_iso)

initramfs_rba = None
initramfs_len = None
for c in src.list_children(iso_path='/boot'):
    name = c.file_identifier().decode('utf-8', 'ignore')
    if 'initramf' in name.lower():
        initramfs_rba = c.extent_location() if callable(getattr(c, 'extent_location', None)) else c.extent_location
        initramfs_len = c.data_length
        break

for c in src.list_children(iso_path='/boot/grub'):
    name = c.file_identifier().decode('utf-8', 'ignore')
    if 'grub.cfg' in name.lower():
        grub_rba = c.extent_location() if callable(getattr(c, 'extent_location', None)) else c.extent_location
        grub_len = c.data_length
        break
src.close()

assert len(cpio) == initramfs_len
offset_initramfs = initramfs_rba * 2048
raw_src[offset_initramfs:offset_initramfs + initramfs_len] = cpio

# Keep original console=ttyS0 loglevel=4 quiet
new_grub = b'set default=0\nset timeout=1\n\nmenuentry "JARVIS-OS - Quantum AI Holographic Station" {\n    linux /boot/vmlinuz console=ttyS0 loglevel=4 quiet\n    initrd /boot/initramfs.cpio\n}\n'
new_grub = new_grub.ljust(grub_len, b' ')
offset_grub = grub_rba * 2048
raw_src[offset_grub:offset_grub + grub_len] = new_grub

open(dst_iso, 'wb').write(raw_src)
print('Successfully rebuilt JARVIS-OS.iso with patched compositor!')
