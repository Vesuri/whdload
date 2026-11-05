from pathlib import Path
import sys,json,bisect,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());sy=r['symbols'];probe=int(r['probe'],16);rows=sorted(json.loads((p/'addresses.json').read_text()),key=lambda x:x['actual']);keys=[x['actual'] for x in rows]
def canon(pc):
 if pc is None:return -1
 i=bisect.bisect_right(keys,pc)-1
 return rows[i]['old']+pc-rows[i]['actual'] if i>=0 and pc<rows[i]['actual']+rows[i]['size'] else pc
cur=None;draws=[]
for f in (t:=barto.load(p/'detail.bin')).fields:
 for pc,cycles,regs in t.instructions(f):
  if (regs[16]>>8)&7:continue
  if pc==probe+sy['B8Draw']:cur={'planes':[],'colour_blits':0,'cookie_blits':0,'clip_shift':[]}
  if cur is not None:
   n=canon(pc)
   if n==0x32e34:cur['planes'].append(regs[0]&65535);cur['clip_shift'].append([regs[x]&65535 for x in [3,4,5]])
   if n==0x32e68:cur['colour_blits']+=1
   if n==0x32efe:cur['cookie_blits']+=1
  if pc==probe+sy['B8Frames']-2 and cur is not None:draws.append(cur);cur=None
out={'draws':draws,'complete_draws':len(draws),'planes':dict(collections.Counter(x for d in draws for x in d['planes'])),'colour_blits':sum(d['colour_blits'] for d in draws),'cookie_blits':sum(d['cookie_blits'] for d in draws),'clip_shift_cases':sorted(set(tuple(x) for d in draws for x in d['clip_shift']))};(p/'colour-analysis.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k not in ['draws','clip_shift_cases']})
