"""Refresh the sole scoreboard from completed A2 normal-build windows."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from completion_cadence import summarize
cases=[('a500','A500, 512K chip + 1.5M slow'),('020','020, 2M chip + 8M fast'),('030','030/50, 2M chip + 8M fast, MMU'),('030-nommu','030/50, 2M chip + 8M fast, no MMU tooltype'),('040','040/25 NOMMU, AGA, 2M chip + 16M Z3 fast'),('060','060/50 NOMMU, AGA, 2M chip + 16M Z3 fast')]
rows=['| Configuration | Checkpoint | Stock steady / event FPS | Bundle steady / event FPS | World update ms | Scene / cockpit / publication ms | DASH markers stock / bundle | Clean fields stock / bundle | World time / wall time | Dropped world time |','|---|---|---|---|---|---|---|---|---|---|']
for machine,label in cases:
 pair=[]
 for mask in [0,1]:
  suffix='-r4' if machine=='a500' and mask==0 else ''
  d=ROOT/f'tmp/prof/completion-a2-{machine}-{mask}{suffix}'
  if not (d/'event.json').exists():break
  meta=json.loads((d/'event.json').read_text());assert meta['classification']=='accepted'
  assert meta['slave_sha256']=='5256542f87ec1c6d3eca174416560597a60e76e1cc785cd0fbf5e3efff3f0ba8'
  assert meta['realism_sha256']=='659d36ca563ba4622daabb36a71dafaf6060cdcbf89bb12e75426198496d272c'
  cadence=summarize((d/'event.log').read_text(),2000)
  pair.append((meta,cadence))
 if len(pair)!=2:
  rows.append('| '+label+' | A1 configs | '+' | '.join(['Pending']*8)+' |');continue
 def fps(p):return f"{p[1]['event_free_frame_fps']:.3f} / {p[1]['window_fps']:.3f}"
 def stage(p,names):return ' / '.join(f"{p[0]['timing']['summaries'][n]['mean_ms']:.2f}" for n in names)
 a,b=pair
 rows.append('| '+' | '.join([label,'A2',fps(a),fps(b),stage(a,['world'])+' → '+stage(b,['world']),stage(a,['scene','cockpit','publication'])+' → '+stage(b,['scene','cockpit','publication']),f"{a[1]['dashboard_events']} / {b[1]['dashboard_events']}",f"{a[1]['clean_fields']:.0f} / {b[1]['clean_fields']:.0f}",'Pending D','Pending D'])+' |')
p=ROOT/'docs/profiling.md';s=p.read_text();start=s.index('| Configuration |');end=s.index('\n\n',start);p.write_text(s[:start]+'\n'.join(rows)+s[end:])
print('\n'.join(rows))
