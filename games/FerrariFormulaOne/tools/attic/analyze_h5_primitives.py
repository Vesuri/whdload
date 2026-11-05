from pathlib import Path
import sys,json,bisect,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());sy=r['symbols'];base=int(r['probe'],16);rows=sorted(json.loads((p/'addresses.json').read_text()),key=lambda x:x['actual']);keys=[x['actual'] for x in rows]
def canon(pc):
 if pc is None:return -1
 i=bisect.bisect_right(keys,pc)-1
 return rows[i]['old']+pc-rows[i]['actual'] if i>=0 and pc<rows[i]['actual']+rows[i]['size'] else pc
hist=collections.Counter();lines=[];bitmaps=[];colours=[];draws=[];active=None;cost=0
trace=barto.load(p/'detail.bin');shift=0
for f in trace.fields:
 for pc,c,g in trace.instructions(f):
  n=canon(pc)
  if not (g[16]>>8)&7:
   if n in (0x24ba2,0x24c88):shift=g[0]&65535
   if n==0x24d58:shift=g[2]&65535
   if pc==base+sy['B8Draw']:active=[]
   if n in (0x24c14,0x24db4,0x6ad86,0x6adda,0x32efe,0x32e68,0x6ac12,0x6ac3e) and active is not None:
    if n in (0x24c14,0x24db4):key=('bitmap',g[0]&63,(g[0]&65535)>>6,hex((g[2]&65535) if n==0x24db4 else 0x7ca),shift,hex(g[8]),hex(g[9]));bitmaps.append((n,list(g),cost))
    elif n in (0x6ad86,0x6adda):key=('line',(g[4]&65535)>>6,hex(g[1]&65535),hex(g[6]&65535),g[5]&65535);lines.append((n,list(g),cost))
    elif n in (0x6ac12,0x6ac3e):key=('road_fill',g[0]&63,(g[0]&65535)>>6)
    else:
     size=g[12] if n==0x32e68 else g[0]
     key=('colour-intermediate' if n==0x32e68 else 'colour-cookie',size&63,(size&65535)>>6,g[3]&65535,g[4]&65535,g[5]&65535)
    active.append(key)
   if pc==base+sy['B8Frames']-2 and active is not None:draws.append(active);active=None
  cost+=c
hist.update(x for d in draws for x in d)
out=dict(complete_draws=len(draws),histogram=[dict(key=k,count=v) for k,v in hist.most_common()],lines=lines,bitmaps=bitmaps)
(p/'h5-primitives.json').write_text(json.dumps(out,indent=2)+'\n')
small=collections.Counter()
for k,v in hist.items():small[k[:5] if k[0]=='bitmap' else k]+=v
print('draws',len(draws));print('\n'.join(f'{v}: {k}' for k,v in small.most_common(70)))
