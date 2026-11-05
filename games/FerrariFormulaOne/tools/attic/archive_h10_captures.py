from pathlib import Path
import json,gzip,hashlib,shutil
r=Path(__file__).resolve().parents[1];index=r/'manifest/render-h10-capture-archive.json';rows=json.loads(index.read_text()) if index.exists() else {};saved=0
for p in (r/'tmp/step5').glob('*h10*'):
 q=p/'result.json'
 if not q.exists() or json.loads(q.read_text()).get('status') not in ['passed','captured']:continue
 for f in p.glob('*.bin'):
  if f.name in ['records.bin','detail.bin'] or f.stat().st_size<1000000:continue
  digest=hashlib.file_digest(f.open('rb'),'sha256').hexdigest();z=f.with_suffix('.bin.gz')
  with f.open('rb') as a,gzip.open(z,'wb',compresslevel=6) as b:shutil.copyfileobj(a,b)
  with gzip.open(z,'rb') as a:assert hashlib.file_digest(a,'sha256').hexdigest()==digest
  rows[str(f.relative_to(r))]={'archive':str(z.relative_to(r)),'sha256':digest,'raw_bytes':f.stat().st_size,'compressed_bytes':z.stat().st_size};saved+=f.stat().st_size-z.stat().st_size;f.unlink()
index.write_text(json.dumps(rows,indent=2)+'\n');print('Verified compressed captures; saved',saved,'bytes')
