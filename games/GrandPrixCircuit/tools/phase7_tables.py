#!/usr/bin/env python3
"""Independent Q8 model and retained guest table comparison; reads private inputs."""
import json,re,struct,os,sys
from pathlib import Path
from gpc_report import regions
p=Path(sys.argv[1]);m=json.loads((p/'metadata.json').read_text());os.environ['SLAVE']=str((p/'slave.slave').resolve());raw=(p/'before.bin').read_bytes();base=m['base'];a4=m['data_base']+0x7ffe-base
sb=next(lo for lo,hi,n,o in regions(raw,base) if n=='slave')-base
listing=(p/'slave.slave.lst').read_text(encoding='latin1')
def sym(n):return sb+int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)$',listing,re.M)[1],16)
def words(o,n):return list(struct.unpack_from('>'+str(n)+'h',raw,o))
angles=raw[a4-22184:a4-22184+89]
signed=words(sym('render_angle_values'),177)
assert signed==[-v for v in angles[:0:-1]]+list(angles)
assert angles[0]==0 and all(x<=y for x,y in zip(angles,angles[1:]))
def odd(i):return angles[abs(i)]*(1 if i>=0 else -1)
for q in range(-22528,22529):
 i,f=divmod(q,256);got=signed[i+88]+(signed[i+89]-signed[i+88])*f//256 if f else signed[i+88]
 j,g=divmod(abs(q),256);mag=angles[j]*256+((angles[j+1]-angles[j])*g if g else 0)
 want=(mag if q>=0 else -mag)//256
 assert got==want,(q,got,want)
main=words(sym('render_main_y'),41);mirror=words(sym('render_mirror_y'),21);lengths=words(sym('render_lengths'),40);f=words(sym('render_fraction'),1)[0]
game=(Path(__file__).resolve().parents[1]/'tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit/data/GrandPrixCircuit').read_bytes()
assert list(struct.unpack_from('>41h',game,0xe5bc+32766-31280))==main
assert list(struct.unpack_from('>40h',game,0xe5bc+32766-710))==lengths
assert [(((v-72)&65535)>>1)+9 for v in main[:21]]==mirror
assert raw[a4-840:a4-840+46]==game[0xe5bc+32766-840:0xe5bc+32766-840+46]
def tables(f):
 a=main.copy();b=mirror.copy()
 for i in range(2,40):a[i]+=(main[i-1]-main[i])*f//256
 for i in range(2,20):b[i]-=(mirror[i]-mirror[i+1])*f//256
 c=[x+((lengths[i-1] if i else 0)-x)*f//256 for i,x in enumerate(lengths)]
 return a,b,c
def rowmap(y,lo,hi):
 flags=[];indices=[]
 for row in range(lo,hi+1):
  k=max(i for i in range(1,len(y)) if y[i]>=row)
  flags.append(-int(y[k]==row));indices.append(k)
 return flags,indices
def select(y):return [2*(i-1) for i in range(1,len(y)) if i==len(y)-1 or y[i]!=y[i+1]]+[-1]
for q in range(256):
 a,b,c=tables(q)
 assert a[1]==111 and a[-1]==72 and b[1]==28 and b[-1]==11
 assert all(x>=y for x,y in zip(a[1:],a[2:]))
 assert all(x>=y for x,y in zip(b[1:],b[2:]))
 assert all(0<=x<=1300 for x in c)
 for y,lo,hi in [(a,72,111),(b,11,22)]:
  flags,indices=rowmap(y,lo,hi);assert all(1<=i<len(y) for i in indices)
  assert len(select(y))<=len(y)
 assert select(a)==select(main), 'main distinct-Y list changed'
 assert a[9:]==main[9:] and b[4:]==mirror[4:]
a,b,c=tables(f)
assert words(a4-31280,41)==a
assert words(a4-1104,21)==b
assert words(a4-710,40)==c
for y,lo,hi,fo,io,li in [(a,72,111,3848,3932,'render_main_list'),(b,11,22,3756,3800,'render_mirror_list')]:
 flags,indices=rowmap(y,lo,hi)
 assert words(a4+fo,len(flags))==flags
 assert words(a4+io,len(indices))==indices
 # Native list intentionally chooses an earlier duplicate at the far row;
 # require exact original bytes above, not a newly generated list.
print(json.dumps(dict(capture=p.name,fraction=f,model_fractions=256,signed_angle_vectors=45057,guest_tables='exact',bounds='pass')))
