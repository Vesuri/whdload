"""Analyze completed retained cases only; no emulator interaction."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from display_ownership import analyse
for case in sorted(Path('tmp/prof').glob('w1-controlled-*-*')):
 if not (case/'complete.json').exists():continue
 for window in [case/'event',*sorted(p for p in case.glob('steady-*') if p.is_dir())]:
  out=window/'display.json'
  if out.exists():continue
  before=json.loads((window/'before.json').read_text());after=json.loads((window/'after.json').read_text())
  buffers=sorted({r['display'] for log in (before,after) for r in log['records']});assert len(buffers)==2,buffers
  result=analyse(window/'trace.bin',before['sim'],buffers);out.write_text(json.dumps(result,indent=2)+'\n')
  print(window,dict(observable=result['observable'],writes=result['framebuffer_writes'],conflicts=len(result['active_display_conflicts']),fetched_later=result['conflicts_fetched_later']),flush=True)
