import sys,re,json,collections,bisect,gzip,os
sys.path.insert(0,os.path.expanduser('~/.local/share/amiga/pylib'))
from amigaxdev import barto
from pathlib import Path
p=Path(sys.argv[1]);res=json.loads((p/'result.json').read_text());probe=int(res['probe'],16)
fl=(Path(res['slave']).parent/'fine.list').read_text()
fs=sorted((int(a,16),n) for n,a in re.findall(r'^([A-Za-z_][\w.]*)\s+00:([0-9A-F]{8})$',fl,re.M));fa=[a for a,_ in fs];sym={n:a for a,n in fs}
dc=int(re.search(r'^00:([0-9A-F]{8}) 6\w+\s+\d+:\s+bsr\.w B8Draw',fl,re.M)[1],16)
D=probe+sym['B8Draw'];A=probe+dc+4
tmp='tmp/ff1_trace.bin';os.system(f'gunzip -c {p}/detail.bin.gz > {tmp}')
t=barto.load(tmp);ind=False;c=collections.Counter();pcs=collections.Counter();nd=0;spans=[];cur=0
def cat(pc):
 if pc is None:return 'stopped'
 if pc==0x7fffffff:return 'gap'
 if probe<=pc<probe+0x10000:return 'probe:'+fs[bisect.bisect_right(fa,pc-probe)-1][1]
 if pc<0x80000:return 'native %05x'%(pc>>8<<8)
 return 'other %x'%(pc>>8<<8)
for f in t.fields:
 for pc,cost,r in t.instructions(f):
  if pc==D and not ind:ind=True;nd+=1;cur=0
  elif pc==A and ind:ind=False;spans.append(cur)
  if ind:c[cat(pc)]+=cost;cur+=cost;pcs[pc]+=cost
os.remove(tmp)
n=len(spans) or 1
print(p.name,'draws',nd,'complete',len(spans),'mean %.1f ms'%(sum(spans)/n/7093.79))
for k,v in c.most_common(30):print('%6.2f ms/draw %s'%(v/nd/7093.79,k))
print('top pcs');[print(' %s %.2f'%(hex(k) if k else k,v/nd/7093.79)) for k,v in pcs.most_common(25)]
