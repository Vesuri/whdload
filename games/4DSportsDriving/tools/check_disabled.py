#!/usr/bin/env python3
"""Compare declared optimization hook ranges against pristine executable bytes."""
import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--timing-only',action='store_true');p.add_argument('--render-only',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parents[1]
meta=json.loads((a.capture/'anchor.json').read_text()); mem=(a.capture/'memory.bin').read_bytes()
original=(root/'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes()
base=meta.get('memory_base',0x200000); count=0
for source in (root/'src').glob('*.s'):
 for kind,off,n in re.findall(r'(PERF|TIMING)_RANGE h0:([0-9a-fA-F]+) (\d+)',source.read_text()):
  if a.timing_only and kind!='TIMING':continue
  if a.render_only and kind!='PERF':continue
  off=int(off,16); n=int(n); at=meta['game_base']-base+off
  assert mem[at:at+n]==original[0x28+off:0x28+off+n],f'Changed disabled hook at {off:05x}'
  count+=1
assert count,'No declared ranges found'
print(f'{count} disabled optimization ranges match the original')
