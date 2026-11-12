import pycdlib, io, os

src_iso_path = r'C:\Users\ARUMUGAM\Downloads\clipperx.iso'
staging = r'E:\jarvis\iso_build_stage'
initramfs_path = r'E:\jarvis\jarvis-initramfs.cpio'

os.makedirs(staging, exist_ok=True)
src = pycdlib.PyCdlib()
src.open(src_iso_path)

def extract_all(iso_path, local_path):
    os.makedirs(local_path, exist_ok=True)
    for c in src.list_children(iso_path=iso_path):
        name = c.file_identifier().decode('utf-8', 'ignore')
        if name in ('.', '..'): continue
        sub_iso = f'{iso_path}/{name}'.replace('//', '/')
        clean_name = name.split(';')[0]
        sub_local = os.path.join(local_path, clean_name)
        if c.is_dir():
            extract_all(sub_iso, sub_local)
        else:
            buf = io.BytesIO()
            src.get_file_from_iso_fp(buf, iso_path=sub_iso)
            open(sub_local, 'wb').write(buf.getvalue())

print('Extracting source ISO tree...')
extract_all('/', staging)
src.close()

boot_dir = os.path.join(staging, 'boot')
open(os.path.join(boot_dir, 'initramfs.cpio'), 'wb').write(open(initramfs_path, 'rb').read())

grub_cfg = """set default=0
set timeout=3

set color_normal=cyan/black
set color_highlight=black/cyan

menuentry "JARVIS-OS -- Tony Stark Workshop Desktop" {
    linux /boot/vmlinuz console=tty1 quiet
    initrd /boot/initramfs.cpio
}

menuentry "JARVIS-OS -- Terminal Recovery Mode" {
    linux /boot/vmlinuz console=tty1 single
    initrd /boot/initramfs.cpio
}
"""
open(os.path.join(staging, 'boot', 'grub', 'grub.cfg'), 'w', encoding='utf-8').write(grub_cfg)
print('Staging tree ready for ISO build.')
