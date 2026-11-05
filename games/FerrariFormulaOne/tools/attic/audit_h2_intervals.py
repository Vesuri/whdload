from pathlib import Path
import json,statistics,math
r=Path(__file__).resolve().parents[1]
for p in (r/'tmp/step5').glob('c4-q03-h2-fps-*-h2-*'):
 if not (p/'result.json').exists():continue
 j=json.loads((p/'result.json').read_text())
 if j.get('status')!='passed':continue
 ints=[];files=sorted(p.glob('census-*.jsonl'),key=lambda q:int(q.stem.split('-')[1]))
 for f in files:
  rows=[json.loads(x) for x in f.read_text().splitlines()[1:]];ch=[x['field'] for prev,x in zip(rows,rows[1:]) if prev['planes']!=x['planes']];ints.extend(b-a for a,b in zip(ch,ch[1:]))
 assert len(ints)>=300,p
 ints=ints[:300]
 if ints!=j['interval_fields']:j['rejected_cross_window_fps']=j['fps']
 j.update(interval_fields=ints,fps_fields=sum(ints),fps=300/(sum(ints)*71051/3546895),mean_ms=statistics.mean(ints)*71051/3546895*1000,p95_ms=sorted(ints)[284]*71051/3546895*1000,census_windows=len(files),measurement='300 complete displayed-buffer intervals within census windows; every window edge excluded. Combined window.jsonl is storage only, never evidence of continuous timing across windows.')
 (p/'result.json').write_text(json.dumps(j,indent=2)+'\n');print(p.name,j['fps'],j['p95_ms'],len(files))
