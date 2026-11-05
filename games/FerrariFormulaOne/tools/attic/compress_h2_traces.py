from pathlib import Path
import gzip,hashlib,json,shutil
r=Path(__file__).resolve().parents[1];out=[]
for p in (r/'tmp/step5').glob('c4-q03-render-profile-a1200-fast-h2*/detail.bin'):
 dest=p.with_suffix('.bin.gz');sha=hashlib.sha256(p.read_bytes()).hexdigest();size=p.stat().st_size
 with p.open('rb') as src,gzip.open(dest,'wb',compresslevel=6) as f:shutil.copyfileobj(src,f)
 h=hashlib.sha256()
 with gzip.open(dest,'rb') as f:
  while chunk:=f.read(1024*1024):h.update(chunk)
 assert h.hexdigest()==sha
 out.append(dict(path=str(dest.relative_to(r)),raw_bytes=size,raw_sha256=sha,compressed_bytes=dest.stat().st_size,compressed_sha256=hashlib.sha256(dest.read_bytes()).hexdigest()));p.unlink()
(r/'manifest/render-h2-traces.json').write_text(json.dumps(out,indent=2)+'\n');print('Verified/compressed',len(out),'traces')
