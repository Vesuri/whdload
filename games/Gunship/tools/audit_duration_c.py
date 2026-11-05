"""Live duration captures plus execution of their native clock conversion."""
from unicorn_b import *
from pathlib import Path
import os,json,sys
listing=Path(os.environ['LISTING']).read_text(encoding='latin1')
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+'$',listing,re.M)[1],16)
c=CPU();reports=[]
for name in sys.argv[1:]:
 path=Path(name);timing=json.loads((path/'actual-rate.json').read_text());rows=[];events=[]
 assert [t['world'] for t in timing['rows']]==list(range(20,201))
 epoch=json.loads((path/'input-events.json').read_text())['epoch']
 for t in timing['rows']:
  w=t['world'];folder=path/f'world-{w}';a=(folder/'arena.bin').read_bytes()
  h=struct.unpack_from('>9I',a,sym('RT_HUNKS'))
  code=(folder/'h0.bin').read_bytes();h6=(folder/'h6.bin').read_bytes();player=h6[0x3b88:0x3b88+86]
  tick=int.from_bytes(player[12:14],'big');assert tick==w
  prefix=bytes.fromhex('70003039')+struct.pack('>I',h[6]+0x3b94)+bytes.fromhex('72034eba')
  hits=[i for i in range(0,len(code)-20,2) if code[i:i+len(prefix)]==prefix]
  assert len(hits)==2
  minute,second=hits;assert second-minute==0x2a
  assert code[minute+14:minute+18]==bytes.fromhex('723c4eba')
  c.put(h[0],code);c.put(h[6],h6)
  c.rw(8,0x8f000);c.call(h[0]+minute,h[0]+minute+20);minutes=c.rr(9)
  c.rw(8,0x8f000);c.call(h[0]+second,h[0]+second+0x34);seconds=c.rr(10)
  assert (minutes,seconds)==(tick//180,tick//3%60)
  assert player[57]==40 and player[66]==28 and player[14:16]==bytes(2)
  reserves=list(struct.unpack_from('>HH',player,4))
  assert min(reserves)>120
  logical,fields,ticks,dropped,rebases=struct.unpack_from('>5I',a,sym('RT_CLOCK'))
  assert fields==logical-epoch==(w*t['rate']+2)//3 and ticks==w and dropped==0 and rebases==1
  assert struct.unpack_from('>II',a,sym('RT_HISTORY')+8)==(0,0)
  assert int.from_bytes(a[sym('RT_SCHEDULER')+22:sym('RT_SCHEDULER')+24],'big')==0
  row=dict(world=w,native_clock=[minutes,seconds],reserves=reserves)
  if rows:
   delta=[x-y for x,y in zip(rows[-1]['reserves'],reserves)]
   assert delta==([40,120] if w%16==0 else [0,0])
   if w%16==0:events.append(w)
  rows.append(row)
 assert events==list(range(32,193,16))
 report=dict(captures=len(rows),reserve_transitions=len(rows)-1,depletion_worlds=events,
             native_clock_at_rollover=[r for r in rows if r['world'] in (179,180,181)],
             actual_elapsed_seconds=timing['native_fields']/t['rate'],rate_hz=timing['observed_world_rate'],
             no_active_history_loss_or_discard=True,no_clock_discard_or_extra_rebase=True,
             scope='Fixed-collective live world captures; saved native clock-conversion code executed in Unicorn, not clock UI pixels.')
 (path/'duration-audit.json').write_text(json.dumps(report,indent=2)+'\n');reports.append(dict(run=path.name,**report))
print(json.dumps(reports,indent=2));c.close()
