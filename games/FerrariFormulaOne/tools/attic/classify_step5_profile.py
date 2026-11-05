#!/usr/bin/env python3
# Split probe-region cycles into trace recording, CCR-trap instructions,
# trampoline register save/restore, and remaining (arithmetic/ownership) work.
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
coarse='C1Head' in symbol
probe=int(json.loads((p/'result.json').read_text())['probe'],16) if coarse else struct.unpack_from('>I',(p/'end.bin').read_bytes(),0x654e8)[0]-symbol['barrier']
lean=coarse or 'velocity_scratch' in symbol
rec_lo=probe+symbol['public_bindings'] if coarse else probe+symbol['velocity_records'];rec_hi=rec_lo if lean else probe+symbol['schedule_records']+3200
def label(pc):return syms[bisect.bisect_right(addrs,pc-probe)-1][1]
RECORD_LABEL=re.compile(r'_(record|records_count|before|after|snapshot)$')
def kind(pc,regs):
 s=text.get(pc-probe,'');l=label(pc)
 if not lean and (RECORD_LABEL.search(l) or 'records' in s or '_count' in s):return 'trace'
 m=re.search(r',(?:-?\d+)?\(a([0-7])[^,]*\)$',s) or re.search(r',-?\(a([0-7])\)\+?$',s)
 if m and rec_lo<=regs[8+int(m.group(1))]<rec_hi:return 'trace'
 if s.startswith('move.w sr'):return 'sr-save instruction'
 if s.startswith('movem.l d0-d7/a0-a6') or s.startswith('move.w (sp)+,ccr'):return 'trampoline save/restore'
 if l.startswith('FF1'):return 'module helper'
 return 'hook body'
t=barto.load(p/'detail.bin')
if os.environ.get('EXCLUDE_PACING')=='1':t=active_fields(t,listing,probe)
started=False;loops=[];tot=collections.Counter();bylabel=collections.defaultdict(collections.Counter)
for f in t.fields:
 for pc,cost,regs in t.instructions(f):
  if pc==0x65174:
   if started:loops.append((tot,bylabel))
   started=True;tot=collections.Counter();bylabel=collections.defaultdict(collections.Counter)
  if not started:continue
  if pc is None:tot['IRQ/gap']+=cost;continue
  if probe<=pc<rec_lo:k=kind(pc,regs);tot[k]+=cost;bylabel[label(pc)][k]+=cost
  elif lo_h<=pc<hi_h:tot['WHDLoad SR emulation']+=cost
  elif pc==0x7fffffff:tot['IRQ/gap']+=cost
  else:tot['native/other']+=cost
loops=loops[int(os.environ.get('DROP_UPDATES','0')):];loops=loops[:int(os.environ.get('MAX_UPDATES',len(loops)))];n=len(loops)
tot=collections.Counter();bylabel=collections.defaultdict(collections.Counter)
for t,l in loops:
 tot.update(t)
 for k,c in l.items():bylabel[k].update(c)
print('updates',n)
for k,v in tot.most_common():print('%9.0f %s'%(v/n,k))
out={k:{kk:round(vv/n) for kk,vv in c.items()} for k,c in sorted(bylabel.items(),key=lambda x:-sum(x[1].values()))}
json.dump({'totals':{k:v/n for k,v in tot.items()},'labels':out,'per_update_totals':[sum(t.values()) for t,l in loops]},open(p/'classified.json','w'),indent=1)
for k,c in list(out.items())[:45]:print('%7d %-28s %s'%(sum(c.values()),k,c))
