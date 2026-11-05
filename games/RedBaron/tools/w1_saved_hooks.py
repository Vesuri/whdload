"""Audit disabled hooks from retained event snapshots, without touching the emulator."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from check_disabled import check
from hook_ranges import ranges
p=argparse.ArgumentParser();p.add_argument('entry',type=Path);p.add_argument('--mask',type=int,required=True);a=p.parse_args()
banks=[(int(f.stem.split('-')[1],16),f.read_bytes()) for f in (a.entry/'event').glob('memory-*.bin')]
def read(addr,size):
 for lo,b in banks:
  if lo<=addr and addr+size<=lo+len(b):return b[addr-lo:addr-lo+size]
 raise ValueError('Missing bank')
sim=json.loads((a.entry/'event/before.json').read_text())['sim'];spans=[x for x in ranges() if not a.mask&(1<<x[2])]
if spans:check(Path('tmp/game/RedBaron/data/sim').read_bytes(),sim,read,spans)
result={'mask':a.mask,'disabled_ranges_checked':len(spans),'status':'passed' if spans else 'no disabled ranges','ranges':[{'offset':x[0],'length':x[1]-x[0],'bit':x[2]} for x in spans]}
(a.entry/'off-hooks.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
