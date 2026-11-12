iso = bytearray(open('JARVIS-OS.iso', 'rb').read())
offset = 1227 * 2048
grub_len = 168
new_grub = b'set default=0\nset timeout=1\n\nmenuentry "JARVIS-OS" {\n    linux /boot/vmlinuz console=ttyS0 loglevel=7 debug earlyprintk=serial\n    initrd /boot/initramfs.cpio\n}\n'
new_grub = new_grub.ljust(grub_len, b' ')
iso[offset:offset+grub_len] = new_grub
open('JARVIS-OS.iso', 'wb').write(iso)
print('Patched debug grub.cfg, len:', len(new_grub))
