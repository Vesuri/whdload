from pathlib import Path
import sys,json,collections,bisect,struct
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
from capstone import *
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());sy=r['symbols'];probe=int(r['probe'],16);host=int(r['host'],16);mem=(p/'start.bin').read_bytes()+(p/'start-fast.bin').read_bytes();md=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_020);md.detail=True
rows=sorted(json.loads((p/'addresses.json').read_text()),key=lambda x:x['actual']);keys=[x['actual'] for x in rows]
def canon(pc):
 i=bisect.bisect_right(keys,pc)-1
 if i>=0 and pc<rows[i]['actual']+rows[i]['size']:return rows[i]['old']+pc-rows[i]['actual']
 return pc
D=probe+sy['B8Draw'];E=probe+sy['B8Frames'];calls={}
for i in md.disasm(mem[D:E],D):
 if i.mnemonic in ('jsr','bsr.w','bsr.l','bsr.b'):
  target=i.op_str
  if target.endswith('.l') and target.startswith('$'):target=hex(canon(int(target[1:-2],16)))
  calls[i.address]=(i.address+i.size,target)
active=False;cur=[];allcalls=[];op=None;colour=collections.Counter();cols=[];cost=0
for f in barto.load(p/'detail.bin').fields:pass
t=barto.load(p/'detail.bin')
for f in t.fields:
 for pc,c,regs in t.instructions(f):
  irq=(regs[16]>>8)&7
  if pc==D:active=True;cur=[];colour=collections.Counter()
  if active:
   if canon(pc or 0)==0x32e34 and not irq:colour[regs[0]&65535]+=1
   if op and pc==op['return'] and not irq:op['cycles']=cost-op['start'];cur.append(op);op=None
   if pc in calls and not irq:
    assert op is None
    ret,target=calls[pc];op={'site':hex(pc-probe),'target':target,'return':ret,'start':cost}
  cost+=c
  if pc==E-2 and active:assert op is None;allcalls.append(cur);cols.append(colour);active=False
agg=collections.defaultdict(lambda:[0,0])
for cs in allcalls:
 for c in cs:agg[c['target']][0]+=1;agg[c['target']][1]+=c['cycles']
n=len(allcalls);out={'complete_draws':n,'top_level_calls':{k:{'calls':v[0],'ms_per_draw':v[1]/n/14187.58} for k,v in sorted(agg.items(),key=lambda x:-x[1][1])},'colour_minterm_indices':dict(sum(cols,collections.Counter()))}
(p/'call-analysis.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
