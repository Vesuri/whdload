from pathlib import Path
import struct
from capstone import *
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5/hi25-profile-040-40-grid'
m=bytearray((p/'start.bin').read_bytes());m+=bytes(0x200000-len(m))+(p/'start-fast.bin').read_bytes()
c=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_020)
u=lambda a:struct.unpack_from('>I',m,a)[0]
execbase=u(4);print('exec',hex(execbase))
for n in range(16):
 a=execbase+84+n*12;print('int',n,[hex(u(a+i)) for i in (0,4,8)])
# Find custom INTENA immediate operations in relocated kick memory.
for a in range(0x800000,len(m)-8,2):
 if m[a:a+4]==bytes.fromhex('33fc8040') or m[a:a+4]==bytes.fromhex('317c8040') or m[a:a+4]==bytes.fromhex('337c8040'):
  print('\nENABLER',hex(a))
  for i in c.disasm(m[a-20:a+40],a-20):print(hex(i.address),i.mnemonic,i.op_str)
a=u(execbase+84+6*12+4);print('\nBLIT handler',hex(a))
for i in c.disasm(m[a:a+180],a):print(hex(i.address),i.mnemonic,i.op_str)
