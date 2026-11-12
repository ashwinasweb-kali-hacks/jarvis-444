import pycdlib, io, os

src_iso = r'C:\Users\ARUMUGAM\Downloads\clipperx.iso'
dst_iso = r'E:\jarvis\JARVIS-OS.iso'
patched_cpio = r'E:\jarvis\jarvis-initramfs.cpio'

# Read source ISO bytes
raw_src = bytearray(open(src_iso, 'rb').read())
print('Source ISO length:', len(raw_src))

src = pycdlib.PyCdlib()
src.open(src_iso)

# Find initramfs extent and length
initramfs_rba = None
initramfs_len = None
for c in src.list_children(iso_path='/boot'):
    name = c.file_identifier().decode('utf-8', 'ignore')
    if 'initramf' in name.lower():
        initramfs_rba = c.extent_location() if callable(getattr(c, 'extent_location', None)) else c.extent_location
        initramfs_len = c.data_length
        print(f'Found {name}: RBA={initramfs_rba}, Length={initramfs_len}')
        break

# Find grub.cfg extent
grub_rba = None
grub_len = None
for c in src.list_children(iso_path='/boot/grub'):
    name = c.file_identifier().decode('utf-8', 'ignore')
    if 'grub.cfg' in name.lower():
        grub_rba = c.extent_location() if callable(getattr(c, 'extent_location', None)) else c.extent_location
        grub_len = c.data_length
        print(f'Found {name}: RBA={grub_rba}, Length={grub_len}')
        break

src.close()

# Replace initramfs in raw_src at sector initramfs_rba * 2048
new_cpio_data = open(patched_cpio, 'rb').read()
assert len(new_cpio_data) == initramfs_len, f'Length mismatch: {len(new_cpio_data)} vs {initramfs_len}'
offset_initramfs = initramfs_rba * 2048
raw_src[offset_initramfs:offset_initramfs + initramfs_len] = new_cpio_data
print('Patched initramfs into ISO binary at offset', offset_initramfs)

# Replace grub.cfg with JARVIS-OS branding (keep length exact by padding)
new_grub = b'''set default=0
set timeout=2

menuentry "JARVIS-OS - Quantum AI Holographic Station" {
    linux /boot/vmlinuz console=tty1 quiet
    initrd /boot/initramfs.cpio
}
'''
if len(new_grub) <= grub_len:
    new_grub = new_grub.ljust(grub_len, b' ')
    offset_grub = grub_rba * 2048
    raw_src[offset_grub:offset_grub + grub_len] = new_grub
    print('Patched grub.cfg into ISO binary at offset', offset_grub)

open(dst_iso, 'wb').write(raw_src)
print('Successfully generated bootable ISO:', dst_iso, f'({len(raw_src)} bytes)')
