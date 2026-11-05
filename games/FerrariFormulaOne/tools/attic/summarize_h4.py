from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for profile in ['a1200-fast','030-50','040-40','060-50']:
 for scene in ['normal','grid','dense']:
  stem='drive-timing' if profile=='a1200-fast' and scene=='normal' else 'h4-fps'
  paths=[r/f'tmp/step5/c4-q03-{stem}-{profile}-h4-{scene}-{arm}/result.json' for arm in ['control','candidate']]
  if not all(p.exists() for p in paths):continue
  js=[read(p) for p in paths]
  if not all(j.get('status')=='passed' for j in js):continue
  assert js[1]['mean_ms']<=js[0]['mean_ms']+1e-9
  assert js[1]['p95_ms']<=js[0]['p95_ms']+1e-9
  assert all(len(j['interval_fields'])==300 and j['error']==0 for j in js)
  rows.append(dict(profile=profile,scene=scene,arms={arm:dict(path=str(p.relative_to(r)),sha256=sha(p),slave_sha256=j['slave_sha256'],fps=j['fps'],mean_ms=j['mean_ms'],p95_ms=j['p95_ms'],heavy_incomplete=j.get('heavy_incomplete')) for arm,p,j in zip(['control','candidate'],paths,js)}))
print('| Emulator / scene | FPS control → H4 | Mean ms control → H4 | p95 ms control → H4 |')
print('|---|---:|---:|---:|')
for row in rows:
 a,b=row['arms'].values();print(f"| {row['profile']} / {row['scene']} | {a['fps']:.3f} → {b['fps']:.3f} | {a['mean_ms']:.3f} → {b['mean_ms']:.3f} | {a['p95_ms']:.3f} → {b['p95_ms']:.3f} |")
(r/'manifest/render-h4-performance.json').write_text(json.dumps(dict(status='passed' if len(rows)==12 else 'incomplete',comparisons=rows),indent=2)+'\n')
