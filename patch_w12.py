import capstone

elf = bytearray(open('extracted_w12', 'rb').read())
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)

# Find 0x4035fe: 75 e8 (jne 0x4035e8)
# and 0x403606: 75 e0 (jne 0x4035e8)
offset1 = 0x4035fe - 0x400000
offset2 = 0x403606 - 0x400000

print(f'Bytes at offset1: {elf[offset1:offset1+2].hex()}')
print(f'Bytes at offset2: {elf[offset2:offset2+2].hex()}')

assert elf[offset1:offset1+2] == b'\x75\xe8', "Mismatch offset1"
assert elf[offset2:offset2+2] == b'\x75\xe0', "Mismatch offset2"

# NOP them out
elf[offset1:offset1+2] = b'\x90\x90'
elf[offset2:offset2+2] = b'\x90\x90'

open('patched_w12', 'wb').write(elf)
print('Patched w12-compositor successfully: will accept any DRM display resolution!')
