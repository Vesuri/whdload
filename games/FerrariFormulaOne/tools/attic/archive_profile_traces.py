"""Losslessly archive completed profile traces after analysis; retain summaries."""
from pathlib import Path
import gzip, hashlib, json, shutil, sys
r=Path(__file__).resolve().parents[1]
for name in sys.argv[1:]:
 p=r/'tmp/step5'/name
 assert p.resolve().parent==(r/'tmp/step5').resolve()
 assert json.loads((p/'result.json').read_text())['status']=='complete'
 assert json.loads((p/'audit.json').read_text())['status']=='passed'
 rows=[]
 for filename in ('detail.bin','detail-raw.bin'):
  src=p/filename; dst=p/(filename+'.gz')
  if not src.exists():
   assert dst.exists()
   continue
  digest=hashlib.sha256()
  with src.open('rb') as f:
   while chunk:=f.read(4194304):digest.update(chunk)
  if not dst.exists():
   with src.open('rb') as f,gzip.open(dst,'wb',compresslevel=1) as out:shutil.copyfileobj(f,out)
  verify=hashlib.sha256()
  with gzip.open(dst,'rb') as f:
   while chunk:=f.read(4194304):verify.update(chunk)
  assert digest.digest()==verify.digest(),str(src)
  rows.append(dict(original=filename,archive=dst.name,sha256=digest.hexdigest(),original_bytes=src.stat().st_size,compressed_bytes=dst.stat().st_size))
  src.unlink()
 if rows:(p/'trace-archives.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('Verified archives:',name,flush=True)
