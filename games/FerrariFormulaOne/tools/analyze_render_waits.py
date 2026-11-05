from pathlib import Path
import json,sys,collections,bisect,statistics
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
p=Path('tmp/dev/tmp/step5/c4-q03-render-profile-a1200-fast-rc2-trace');r=json.loads((p/'result.json').read_text());sy=r['symbols'];host=int(r['host'],16);probe=int(r['probe'],16);wait=host+r['host_symbols']['gfx_WaitBlit'];draw=probe+sy['B8Draw'];end=probe+sy['B8Frames']-2
rows=sorted(json.loads((p/'addresses.json').read_text()),key=lambda x:x['actual']);keys=[x['actual'] for x in rows]
def canon(pc):
 if pc is None:return -1
 i=bisect.bisect_right(keys,pc)-1
 if i>=0 and pc<rows[i]['actual']+rows[i]['size']:return rows[i]['old']+pc-rows[i]['actual']
 return pc
cur=None;complete=[];openwait=None;wrappercaller=None;prev=None;calls=[];costs=collections.Counter();drawidx=-1
for f in barto.load(p/'detail.bin').fields:pass
t=barto.load(p/'detail.bin')
for f in t.fields:
 for pc,c,regs in t.instructions(f):
  irq=(regs[16]>>8)&7;n=canon(pc)
  if pc==draw:cur={'calls':[],'costs':collections.Counter(),'pc_counts':collections.Counter(),'wrapper_costs':[]};drawidx+=1
  if cur is not None:
   if n==0x2a130 and not irq:wrappercaller=canon(prev)
   if pc==wait and not irq:
    assert openwait is None
    openwait={'cycles':0,'busy':False,'cia_reads':0,'caller':hex(wrappercaller) if wrappercaller is not None else 'unknown'}
   if openwait is not None:
    openwait['cycles']+=c
    if wait+0x10<= (pc or -1) <wait+0x28 and not irq:openwait['cia_reads']+=1;openwait['busy']=True
    if pc==wait+0x38:
     cur['calls'].append(openwait);openwait=None
   k='gap' if pc==0x7fffffff else 'irq' if irq else 'wait-helper' if pc is not None and wait<=pc<=wait+0x38 else 'wait-wrapper' if 0x2a130<=n<=0x2a13e else 'other'
   cur['costs'][k]+=c;cur['pc_counts'][n]+=1
   if n==0x2a138:cur['wrapper_costs'].append(c)
  if pc==end and cur is not None:assert openwait is None;complete.append(cur);cur=None
  if not irq and pc not in (None,0x7fffffff):prev=pc
n=len(complete);calls=[c for d in complete for c in d['calls']];costs=sum((d['costs'] for d in complete),collections.Counter());caller=collections.defaultdict(lambda:collections.Counter());ms=lambda c:c/14187.58
for c in calls:caller[c['caller']].update(calls=1,busy=int(c['busy']),cycles=c['cycles'],cia_reads=c['cia_reads'])
out={'draws':n,'wait_calls':len(calls),'calls_per_draw':len(calls)/n,'busy_calls':sum(c['busy'] for c in calls),'idle_calls':sum(not c['busy'] for c in calls),'cia_reads':sum(c['cia_reads'] for c in calls),'inclusive_wait_ms_per_draw':sum(ms(c['cycles']) for c in calls)/n,'busy_wait_ms_per_draw':sum(ms(c['cycles']) for c in calls if c['busy'])/n,'idle_wait_ms_per_draw':sum(ms(c['cycles']) for c in calls if not c['busy'])/n,'exclusive_ms_per_draw':{k:ms(v/n) for k,v in costs.most_common()},'callers':{k:dict(v,ms_per_draw=ms(v['cycles']/n)) for k,v in sorted(caller.items(),key=lambda x:-x[1]['cycles'])},'wrapper_jsr_cycles':{'min':min(c for d in complete for c in d['wrapper_costs']),'median':statistics.median(c for d in complete for c in d['wrapper_costs']),'max':max(c for d in complete for c in d['wrapper_costs'])}}
(p/'wait-analysis.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
