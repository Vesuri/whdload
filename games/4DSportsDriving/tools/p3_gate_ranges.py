"""Read-only capture proof that every P3-only hook remains native when gated off."""
import json,re,sys
from pathlib import Path
p=Path(sys.argv[1]);gate=json.loads((p/'gate-check.json').read_text());syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(p/'slave.lst').read_text(encoding='latin1'),re.M)};m=json.loads((p/'anchor.json').read_text());b=(p/'memory.bin').read_bytes();original=Path('tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes();rows=[]
for src in Path('src').glob('raster*.s'):
 for off,n in re.findall(r'PERF_RANGE h0:([0-9a-fA-F]+) (\d+) bit=1',src.read_text()):
  off=int(off,16);n=int(n);at=m['game_base']-m['memory_base']+off
  expected=original[0x28+off:0x28+off+n];path='native'
  if off==0x347b0 and gate['custom2']&1 and int(gate['attnflags'],16)&2 and not int(gate['attnflags'],16)&4:
   expected=bytes.fromhex('4eb9')+(m['slave_base']+syms['perf_cpu_rect']).to_bytes(4,'big')+bytes.fromhex('4e71')*17;path='existing P2 rectangle hook'
  assert b[at:at+n]==expected,hex(off)
  rows.append(dict(offset=hex(off),bytes=n,path=path))
assert rows
(p/'gate-disabled-ranges.json').write_text(json.dumps(dict(passed=True,ranges=rows),indent=2)+'\n');print(len(rows),'P3 ranges retain native or the explicitly verified existing P2 rectangle path')
