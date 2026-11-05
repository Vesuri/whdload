from pathlib import Path
import gzip,hashlib,shutil,json
r=Path(__file__).resolve().parents[1];rows=[]
for p in (r/'tmp/step5').glob('*h11-*'):
 if not (p/'result.json').exists() or json.loads((p/'result.json').read_text()).get('status') not in ('passed','captured'):continue
 for f in p.glob('*.bin'):
  if f.stat().st_size<262144 or f.name=='records.bin':continue
  z=f.with_suffix('.bin.gz');h=hashlib.file_digest(f.open('rb'),'sha256').hexdigest()
  with f.open('rb') as a,gzip.open(z,'wb',compresslevel=1) as b:shutil.copyfileobj(a,b)
  with gzip.open(z,'rb') as a:assert hashlib.file_digest(a,'sha256').hexdigest()==h
  rows.append(dict(path=str(f.relative_to(r)),sha256=h,raw=f.stat().st_size,compressed=z.stat().st_size));f.unlink()
p=r/'manifest/render-h11-capture-archive.json';old=json.loads(p.read_text()) if p.exists() else [];p.write_text(json.dumps(old+rows,indent=2)+'\n');print('Archived',len(rows),'files; saved',sum(x['raw']-x['compressed'] for x in rows))
