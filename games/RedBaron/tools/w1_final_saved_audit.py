"""Audit completed corrected-build captures without contacting any emulator."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from check_disabled import check
from hook_ranges import ranges
from display_ownership import analyse
original=Path('tmp/game/RedBaron/data/sim').read_bytes()
for case in sorted([*Path('tmp/prof').glob('w1-scene-*-*-*'),*Path('tmp/prof').glob('w1-hot-*-*')]):
 if 'twins' in case.name or not (case/'complete.json').exists() or (case/'final-audit.json').exists():continue
 mask=int(case.name.rsplit('-',1)[1]);window=case/'window'
 assert json.loads((case/'entry.json').read_text())['slave_sha256']=='5c0918ccbccb27ad301478873e1aeab8398f057211b2749ce7d16fe949f23475'
 before=json.loads((window/'before.json').read_text());after=json.loads((window/'after.json').read_text())
 banks=[(int(f.stem.split('-')[1],16),f.read_bytes()) for f in window.glob('memory-*.bin')]
 def read(addr,size):
  for lo,b in banks:
   if lo<=addr and addr+size<=lo+len(b):return b[addr-lo:addr-lo+size]
  raise ValueError('Missing bank')
 spans=[x for x in ranges() if not mask&(1<<x[2])]
 if spans:check(original,before['sim'],read,spans)
 buffers=sorted({r['display'] for log in (before,after) for r in log['records']});assert len(buffers)==2,buffers
 result=analyse(window/'trace.bin',before['sim'],buffers)
 (window/'display.json').write_text(json.dumps(result,indent=2)+'\n')
 summary=dict(disabled_ranges_checked=len(spans),observable=result['observable'],writes=result['framebuffer_writes'],conflicts=len(result['active_display_conflicts']),fetched_later=result['conflicts_fetched_later'])
 (case/'final-audit.json').write_text(json.dumps(summary,indent=2)+'\n');print(case,summary,flush=True)
