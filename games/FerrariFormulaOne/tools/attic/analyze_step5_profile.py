#!/usr/bin/env python3
# Attribute every traced cycle of complete 20 ms elapsed-diagnostic updates to
# native routine groups or to the nearest diagnostic/module label.
from pathlib import Path
import os,sys,collections,json,re,struct,bisect
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
from step5_profile_stream import fields as active_fields
r=Path(__file__).resolve().parents[1];name=sys.argv[1];p=r/'tmp/step5'/name
build=Path(json.loads((p/'result.json').read_text())['slave']).parent
listing=(build/'fine.list').read_text()
syms=sorted((int(a,16),n) for n,a in re.findall(r'^([A-Za-z_][\w.]*)\s+00:([0-9A-F]{8})$',listing,re.M))
addrs=[a for a,_ in syms];symbol={n:a for a,n in syms}
memory=(p/'end.bin').read_bytes();coarse='C1Head' in symbol
probe=int(json.loads((p/'result.json').read_text())['probe'],16) if coarse else struct.unpack_from('>I',memory,0x654e8)[0]-symbol['barrier']
end_probe=probe+symbol['public_bindings'] if coarse else probe+symbol['velocity_records']
native=[(0x67120,0x68730,'car body'),(0x68730,0x69bac,'AI/contact helpers'),(0x6cd00,0x6d4cc,'engine force helpers'),(0x6d4cc,0x6dc38,'drag/RPM/gear'),(0x6dc38,0x6e2f6,'velocity/slip/tyre response'),(0x6e2f6,0x6ea3e,'engine curves'),(0x6ea3e,0x6ec94,'wear'),(0x6ec94,0x6ef20,'failure helpers'),(0x29500,0x29542,'software multiply'),(0x24fe0,0x25020,'sin/cos'),(0x65174,0x67120,'race main loop'),(0x6bbfc,0x6c900,'retained presentation/boost'),(0x64a68,0x65174,'race overlay low')]
def owner(pc):
 if pc is None:return 'stopped'
 if pc==0x7fffffff:return 'IRQ/gap'
 if probe<=pc<end_probe:return 'probe:'+syms[bisect.bisect_right(addrs,pc-probe)-1][1]
 if 0xf80000<=pc:return 'ROM'
 for a,b,n in native:
  if a<=pc<b:return 'native:'+n
 return 'native:other %05x'%(pc>>8<<8)
trace=barto.load(p/'detail.bin')
if os.environ.get('EXCLUDE_PACING')=='1':trace=active_fields(trace,listing,probe)
started=False;cur=collections.Counter();loops=[];pcs=collections.Counter();nat_pcs=collections.Counter()
for field in trace.fields:
 for pc,cost,regs in trace.instructions(field):
  task=regs[15]>>12 in (0x18,0x1f) or True
  if pc==0x65174:
   if started:loops.append(cur)
   started=True;cur=collections.Counter()
  if not started:continue
  o=owner(pc);cur[o]+=cost
  if pc is not None and pc!=0x7fffffff:
   pcs[pc]+=cost
   if o.startswith('native:'):nat_pcs[pc]+=cost
loops=loops[int(os.environ.get('DROP_UPDATES','0')):];loops=loops[:int(os.environ.get('MAX_UPDATES',len(loops)))];n=len(loops);tot=collections.Counter()
for l in loops:tot.update(l)
clock=7093790 if coarse and 'a500' in name else 14187580
mean=sum(tot.values())/n
def ms(c):return c/clock*1000
out={'trace':name,'probe_base':hex(probe),'complete_updates':n,'mean_cycles':mean,'mean_ms_at_14.19MHz':ms(mean),'per_update_cycles':[sum(l.values()) for l in loops],'owners_mean_cycles':{k:round(v/n) for k,v in tot.most_common()},'top_pcs':[{'pc':hex(k),'owner':owner(k),'cycles_per_update':round(v/n)} for k,v in pcs.most_common(80)]}
(p/'profile.json').write_text(json.dumps(out,indent=2)+'\n')
print(n,'updates; mean',round(mean),'cycles =',round(ms(mean),2),'ms')
for k,v in tot.most_common(60):print('%9d %5.1f%% %s'%(v/n,100*v/n/mean,k))
