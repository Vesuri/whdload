from pathlib import Path
from functools import lru_cache
import json,re,struct,sys
root=Path('tmp/c');listing=Path('tmp/build/verify/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
def inputs(folder):
 meta=json.loads((folder/'input-events.json').read_text());epoch=meta['epoch'];records={}
 for path in list(folder.glob('input-*-arena.bin'))+list(folder.glob('world-*/arena.bin')):
  a=path.read_bytes();h=sym('RT_HISTORY');q=sym('RT_COMMANDS')
  assert struct.unpack_from('>II',a,h+8)==(0,0)
  assert struct.unpack_from('>II',a,q+16)==(0,0)
  assert struct.unpack_from('>H',a,sym('RT_SCHEDULER')+22)[0]==0
  for i in range(128):
   x=a[h+20+i*40:h+20+(i+1)*40];field=int.from_bytes(x[:4],'big')-epoch
   if field<=0:continue
   # Fixed-seed verification removes timestamp entropy; retain every control byte.
   record=x[4:32].hex()
   assert field not in records or records[field]==record
   records[field]=record
 return meta['events'],records
folders=[Path(x) for x in sys.argv[1:3]] if len(sys.argv)>2 else [root/f'world-active-{cpu}' for cpu in ['020','060']]
a,b=[inputs(f) for f in folders];assert a[0]==b[0]
common=sorted(a[1].keys()&b[1].keys());different=[k for k in common if a[1][k]!=b[1][k]]
rows=[]
for tick in range(100,103):
 states=[]
 for f in folders:
  d=f/f'world-{tick}';h6=(d/'h6.bin').read_bytes();h4=(d/'h4.bin').read_bytes();p=h6[0x3b88:0x3bde]
  assert int.from_bytes(p[28:30],'big')>0
  states.append(dict(player=p.hex(),rng=h4[0x3cc:0x3d0].hex(),mission=(d/'mission.bin').read_bytes()[:0x94].hex(),alive=(d/'alive.bin').read_bytes().hex()))
 rows.append(dict(world=tick,equal={k:states[0][k]==states[1][k] for k in states[0]},player_differences=[hex(i) for i,(x,y) in enumerate(zip(bytes.fromhex(states[0]['player']),bytes.fromhex(states[1]['player']))) if x!=y]))
result=dict(matched_input_fields=len(common),different_input_fields=different,worlds=rows,scope='Retained control records and selected authoritative state; full object and no-draw comparisons remain open.')
(folders[1]/'active-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
assert not different
assert all(all(row['equal'].values()) for row in rows)
