"""Extract endpoint screenshots already present in completed scene traces."""
from pathlib import Path
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
for case in sorted(Path('tmp/prof').glob('w1-scene-*-*-*')):
 if 'twins' in case.name or not (case/'complete.json').exists() or any((case/'window').glob('last.*')):continue
 t=barto.load(case/'window/trace.bin')
 for name,f in [('first',t.fields[0]),('last',t.fields[-1])]:
  ext='png' if f.shot.startswith(b'\x89PNG') else 'jpg' if f.shot.startswith(b'\xff\xd8') else None
  assert ext,(case,f.shot_kind)
  (case/'window'/f'{name}.{ext}').write_bytes(f.shot)
 print(case,flush=True)
