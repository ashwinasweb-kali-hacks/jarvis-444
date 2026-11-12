import pycdlib

src_iso = r'C:\Users\ARUMUGAM\Downloads\clipperx.iso'
dst_iso = r'E:\jarvis\JARVIS-OS.iso'
patched_cpio = r'E:\jarvis\jarvis-initramfs.cpio'

raw_src = bytearray(open(src_iso, 'rb').read())

src = pycdlib.PyCdlib()
src.open(src_iso)

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

# 1. Patch initramfs with Tony Stark Workshop wallpapers
new_cpio_data = open(patched_cpio, 'rb').read()
assert len(new_cpio_data) == initramfs_len
offset_initramfs = initramfs_rba * 2048
raw_src[offset_initramfs:offset_initramfs + initramfs_len] = new_cpio_data

# 2. Patch grub.cfg keeping exact console=ttyS0 so DRM card0 initializes without hanging
new_grub = b'set default=0\nset timeout=1\n\nmenuentry "JARVIS-OS - Tony Stark Workshop" {\n    linux /boot/vmlinuz console=ttyS0 loglevel=4 quiet\n    initrd /boot/initramfs.cpio\n}\n'
new_grub = new_grub.ljust(grub_len, b' ')
offset_grub = grub_rba * 2048
raw_src[offset_grub:offset_grub + grub_len] = new_grub

open(dst_iso, 'wb').write(raw_src)
print("Rebuilt JARVIS-OS.iso successfully")
