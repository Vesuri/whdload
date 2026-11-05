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

gfx=u(execbase+84+6*12)
for n,offset in [('OwnBlitter',-456),('DisownBlitter',-462),('QBlit',-276),('QBSBlit',-294)]:
 a=gfx+offset;target=u(a+2);print("\nVECTOR",n,hex(target))
 for i in c.disasm(m[target:target+100],target):print(hex(i.address),i.mnemonic,i.op_str)
