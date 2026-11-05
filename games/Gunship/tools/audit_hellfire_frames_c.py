"""Check captured Hellfire presentation against native draw coordinates/buffer."""
import json,re,struct,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
l=(root/'tmp/build/selector-combat.slave.lst').read_text(encoding='latin1')
sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
for folder in map(Path,sys.argv[1:]):
 rows=json.loads((folder/'frame-projections.json').read_text());verified=[]
 for row in rows:
  f=row['frame'];d=folder/f"frame-{f['frame']:03d}"
  h0=(d/'h0.bin').read_bytes();h6=(d/'h6.bin').read_bytes();a=(d/'arena.bin').read_bytes()
  p=row['projections'][0]['visible'];assert len(p)==1
  actual=list(struct.unpack_from('>hh',h0,0xa448))
  assert actual==[p[0]['x'],p[0]['y']],(f,actual,p)
  table=int.from_bytes(h0[0xba2:0xba6],'big');buffer=int.from_bytes(h6[0x4bb0:0x4bb2],'big')
  assert f['bitmap']==table+40*(buffer^1)
  for off in [sym('RT_CLOCK')+12,sym('RT_HISTORY')+12,sym('RT_COMMANDS')+16,sym('RT_COMMANDS')+20]:
   assert int.from_bytes(a[off:off+4],'big')==0
  verified.append(dict(frame=f['frame'],world=f['world'],logical=f['logical'],completed_field=f['native_field'],xy=actual))
 before=[x for x in verified if x['world']==27][-1];after=[x for x in verified if x['world']==28][0]
 report=dict(run=folder.name,frames=len(verified),native_draw_coordinates_match=True,completed_buffer_verified=True,time_input_loss=0,before=before,after=after,correction=[after['xy'][i]-before['xy'][i] for i in range(2)],completion_field_gap=after['completed_field']-before['completed_field'])
 (folder/'retarget-frame-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
