"""List double constants the MSP code pushes (MOVI addr,A8 then two MOVE *A8+,*A14+).
Usage: msp_consts.py DIS SEC00 SEC01   -> value, address, use count, first users."""
import os,re,struct,sys,collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tidbl import from_bytes_le
dis=[l.rstrip('\n') for l in open(sys.argv[1])]
img={0x700000:open(sys.argv[2],'rb').read(),0x778e80:open(sys.argv[3],'rb').read()}
def dbl(a):
    for base,b in img.items():
        off=(a-base)//8
        if 0<=off<=len(b)-8 and (a-base)%16==0: return from_bytes_le(b[off:off+8])
uses=collections.defaultdict(list)
for i,l in enumerate(dis):
    m=re.match(r'([0-9A-F]{8}): .*MOVI\s+([0-9A-F]+)h,A8$',l)
    if m and i+2<len(dis) and '*A8+,*A14+,1' in dis[i+1] and '*A8+,*A14+,1' in dis[i+2]:
        uses[int(m.group(2),16)].append(int(m.group(1),16))
rows=[]
for a,u in uses.items():
    v=dbl(a)
    rows.append((a,v,u))
rows.sort(key=lambda r:r[0])
for a,v,u in rows:
    print('%08X %-22s n=%-3d %s'%(a,repr(v),len(u),' '.join('%X'%x for x in u[:6])))
