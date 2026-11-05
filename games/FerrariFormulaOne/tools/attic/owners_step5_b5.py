#!/usr/bin/env python3
# Per-car split of complete updates: segments are delimited by visits to the
# native car-loop head $671b6 (cars 7..0) inside the update starting at $65174.
from pathlib import Path
import os,sys,collections,json,re,struct,bisect
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
from step5_profile_stream import fields as active_fields
r=Path(__file__).resolve().parents[1];name=sys.argv[1];p=r/'tmp/step5'/name
lo_h,hi_h=int(sys.argv[2],16),int(sys.argv[3],16)
build=Path(json.loads((p/'result.json').read_text())['slave']).parent
listing=(build/'fine.list').read_text()
syms=sorted((int(a,16),n) for n,a in re.findall(r'^([A-Za-z_][\w.]*)\s+00:([0-9A-F]{8})$',listing,re.M))
addrs=[a for a,_ in syms];symbol={n:a for a,n in syms}
text={}
for a,src in re.findall(r'^00:([0-9A-F]{8}) [0-9A-F]+\s+\d+:\s?(.*)$',listing,re.M):text.setdefault(int(a,16),src.strip())
probe=struct.unpack_from('>I',(p/'end.bin').read_bytes(),0x654e8)[0]-symbol['barrier']
lean='velocity_scratch' in symbol
rec_lo=probe+symbol['velocity_records'];rec_hi=rec_lo if lean else probe+symbol['schedule_records']+3200
def label(pc):return syms[bisect.bisect_right(addrs,pc-probe)-1][1]
RL=re.compile(r'_(record|records_count|before|after|snapshot)$')
def kind(pc,regs):
 if pc is None:return 'irq'
 if lo_h<=pc<hi_h:return 'sr_trap'
 if pc==0x7fffffff:return 'irq'
 if not probe<=pc<rec_lo:return 'native'
 s=text.get(pc-probe,'');l=label(pc)
 if not lean and (RL.search(l) or 'records' in s or '_count' in s):return 'trace'
 m=re.search(r',(?:-?\d+)?\(a([0-7])[^,]*\)$',s) or re.search(r',-?\(a([0-7])\)\+?$',s)
 if m and rec_lo<=regs[8+int(m.group(1))]<rec_hi:return 'trace'
 if s.startswith('move.w sr'):return 'sr_trap'
 if s.startswith('movem.l d0-d7/a0-a6') or s.startswith('move.w (sp)+,ccr'):return 'trampoline'
 if l.startswith('FF1Div') or l.startswith('FF1SquareRoot020') or l=='FF1Squares':return 'native'  # native-equivalent arithmetic
 if l.startswith('FF1'):return 'conv_helper'
 if l.startswith('schedule'):return 'scheduler'
 return 'hook_body'
t=barto.load(p/'detail.bin')
if os.environ.get('EXCLUDE_PACING')=='1':t=active_fields(t,listing,probe)
loops=[];cur=None;seg=None; owners=[]; own=None
for f in t.fields:
 for pc,cost,regs in t.instructions(f):
  if pc==0x65174:
   if cur is not None:loops.append(cur);owners.append(own)
   cur=collections.defaultdict(collections.Counter);own=collections.Counter();seg='pre';k=0
  if cur is None:continue
  if pc==0x671bc:
   car=regs[0]&65535;seg='car%d'%car if car<8 else 'post'
  cur[seg][kind(pc,regs)]+=cost
  if seg=='car0' and kind(pc,regs)=='conv_helper':own[label(pc)]+=cost
loops=loops[int(os.environ.get('DROP_UPDATES','0')):];loops=loops[:int(os.environ.get('MAX_UPDATES',len(loops)))];n=len(loops);agg=collections.defaultdict(collections.Counter)
for l in loops:
 for s,c in l.items():agg[s].update(c)
cats=['native','conv_helper','hook_body','trampoline','trace','sr_trap','scheduler','irq']
print('updates',n);print('%-6s'%'seg'+''.join('%12s'%c for c in cats)+'%10s'%'total')
res={}
for s in ['pre']+['car%d'%i for i in range(7,-1,-1)]+['post']:
 c=agg[s];res[s]={k:round(v/n) for k,v in c.items()}
 print('%-6s'%s+''.join('%12d'%(c[x]/n) for x in cats)+'%10d'%(sum(c.values())/n))
T=collections.Counter()
for c in agg.values():T.update(c)
print('%-6s'%'TOTAL'+''.join('%12d'%(T[x]/n) for x in cats)+'%10d'%(sum(T.values())/n))
json.dump({'updates':n,'segment_totals_exact':{s:sum(c.values())/n for s,c in agg.items()},'segments':res,'segment_categories_exact':{s:{k:v/n for k,v in c.items()} for s,c in agg.items()},'totals':{k:round(v/n) for k,v in T.items()},'per_update_totals':[sum(sum(c.values()) for c in l.values()) for l in loops]},open(p/'percar.json','w'),indent=1)

selected=owners[int(os.environ.get('DROP_UPDATES','0')):][:int(os.environ.get('MAX_UPDATES',len(owners)))];o=collections.Counter()
for c in selected:o.update(c)
print('PLAYER HELPER OWNERS',[(k,v/len(selected)) for k,v in o.most_common()])
