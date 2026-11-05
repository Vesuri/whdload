"""Audit shared hunk and pointed-record reads across completed same-world frames."""
from pathlib import Path
import json,collections,struct,re
root=Path(__file__).resolve().parents[1];reference=root/'tmp/c/homing-selection-pal-060/world-27'
reference_pointer=struct.unpack_from('>I',(reference/'h6.bin').read_bytes(),0x45e2)[0]
reads=json.loads((root/'tmp/c/homing-forecast-player-reads-candidates-only.json').read_text())['reports'];needed=collections.defaultdict(set)
for row in reads:
 for part in row['shared_read_ranges']:
  start=int(part['offset'],16);source=part['source']
  if source=='external':source='object-records';start-=reference_pointer;assert 0<=start and start+part['length']<=256
  needed[source].update(range(start,start+part['length']))
listing=(root/'tmp/build/selector-combat.slave.lst').read_text(encoding='latin1')
sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',listing,re.M)[1],16)
reports=[]
for name in ('forecast-dependencies-pal-020','forecast-dependencies-pal-060'):
 folder=root/'tmp/c'/name;frames=json.loads((folder/'frames.json').read_text());pairs=[]
 for frame in frames:
  a=(folder/f"frame-{frame['frame']:03d}"/'arena.bin').read_bytes()
  for structure,off,width in [('RT_CLOCK',12,4),('RT_CLOCK',26,2),('RT_HISTORY',8,4),('RT_HISTORY',12,4),('RT_COMMANDS',16,4),('RT_COMMANDS',20,4),('RT_SCHEDULER',22,2)]:assert int.from_bytes(a[sym(structure)+off:sym(structure)+off+width],'big')==0,(structure,off,frame)
  assert int.from_bytes(a[sym('RT_CLOCK')+16:sym('RT_CLOCK')+20],'big')==1
  assert int.from_bytes(a[sym('RT_CAPTURE_OWNER'):sym('RT_CAPTURE_OWNER')+2],'big')==1
 for before,after in zip(frames,frames[1:]):
  if before['world']!=after['world']:continue
  first=folder/f"frame-{before['frame']:03d}";second=folder/f"frame-{after['frame']:03d}";changes=[]
  assert json.loads((first/'object-records-address.json').read_text())==json.loads((second/'object-records-address.json').read_text())
  for source,offsets in needed.items():
   a=(first/(source+'.bin')).read_bytes();b=(second/(source+'.bin')).read_bytes()
   changes.extend(dict(source=source,offset=hex(off),before=a[off],after=b[off]) for off in sorted(offsets) if a[off]!=b[off])
  a=(first/'object-records.bin').read_bytes();b=(second/'object-records.bin').read_bytes()
  pairs.append(dict(world=before['world'],before=before['frame'],after=after['frame'],changes=changes,whole_record_changes=[hex(i) for i,(x,y) in enumerate(zip(a,b)) if x!=y]))
 reports.append(dict(time_input_loss=0,unexpected_rebases=0,run=name,frames=len(frames),pairs=pairs,observed_bytes=sum(map(len,needed.values())),external_offsets=[hex(i) for i in sorted(needed['object-records'])]))
report=dict(reports=reports);(root/'tmp/c/forecast-external-dependency-audit.json').write_text(json.dumps(report,indent=2)+'\n')
for r in reports:print(dict(run=r['run'],frames=r['frames'],pairs=len(r['pairs']),observed_bytes=r['observed_bytes'],changed_pairs=sum(bool(p['changes']) for p in r['pairs']),whole_record_changed_pairs=sum(bool(p['whole_record_changes']) for p in r['pairs'])))
