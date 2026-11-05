"""Local pristine SPS 0126 executable: hunk contents, allocations and relocations."""
import struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GAME=ROOT/'tmp/game/HardDrivin_v3.0_0126/HardDrivin/data/HardDrivin'
def hunks():
 b=GAME.read_bytes();i=0
 def word():
  nonlocal i
  v=struct.unpack_from('>I',b,i)[0];i+=4;return v
 assert word()==1011 and word()==0
 count,first,last=word(),word(),word();assert first==0 and count==last+1
 sizes=[(word()&0x3fffffff)*4 for _ in range(count)];out=[]
 for size in sizes:
  kind=word();assert kind in [1001,1002,1003]
  n=word()*4;data=b[i:i+n] if kind!=1003 else b''
  if kind!=1003:i+=n
  relocs=[]
  while (t:=word())!=1010:
   assert t==1004
   while (n:=word()):
    dest=word();relocs.extend((word(),dest) for _ in range(n))
  out.append(dict(size=size,data=data.ljust(size,b'\0'),relocs=relocs))
 assert i==len(b)
 return out
