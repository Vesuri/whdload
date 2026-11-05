"""Refresh only completed normal-bundle columns in the sole scoreboard."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from completion_cadence import summarize
phase=sys.argv[1]
p=ROOT/'docs/profiling.md';lines=p.read_text().splitlines();hashes=set()
for machine,prefix in [('a500','| A500,'),('020','| 020,'),('030','| 030/50, 2M chip + 8M fast, MMU |'),('030-nommu','| 030/50, 2M chip + 8M fast, no MMU tooltype |'),('040','| 040/25'),('060','| 060/50')]:
 d=ROOT/f'tmp/prof/completion-{phase}-{machine}-1'
 if not (d/'event.json').exists():
  if phase=='f':raise RuntimeError('Missing final case '+machine)
  continue
 meta=json.loads((d/'event.json').read_text());assert meta['classification']=='accepted'
 entry=json.loads((d/'entry.json').read_text());assert entry['build_mode']=='normal' and entry['mask']==(0 if phase=='f' else 1)
 if phase=='f':
  assert 'CUSTOM2=' not in entry['environment']['WHD_ARGS']
  assert '0x7001' in (d/'default-selection.txt').read_text()
 hashes.add(entry['slave_sha256']);c=summarize((d/'event.log').read_text(),2000);st=meta['timing']['summaries']
 for i,line in enumerate(lines):
  if not line.startswith(prefix) or i>30:continue
  cells=line.split('|')
  if phase=='f' and machine=='a500':cells[1]=' A500, 512K chip + 2M fast (F); A2 stock used 1.5M slow '
  cells[2]=f' {phase.upper()} bundle / A2 stock '
  cells[4]=f' {c["event_free_frame_fps"]:.3f} / {c["window_fps"]:.3f} '
  cells[5]=cells[5].split('→')[0]+f'→ {st["world"]["mean_ms"]:.2f} '
  cells[6]=cells[6].split('→')[0]+'→ '+' / '.join(f'{st[n]["mean_ms"]:.2f}' for n in ('scene','cockpit','publication'))+' '
  cells[7]=cells[7].split('/')[0]+f'/ {c["dashboard_events"]} '
  cells[8]=cells[8].split('/')[0]+f'/ {c["clean_fields"]:.0f} '
  lines[i]='|'.join(cells)
 print(machine,c['event_free_frame_fps'],c['window_fps'],flush=True)
assert len(hashes)<=1,hashes
p.write_text('\n'.join(lines)+'\n');print('normal binary',hashes)
