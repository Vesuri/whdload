from pathlib import Path
import gzip,hashlib,json,sys
r=Path(__file__).resolve().parents[1];rows=[]
for p in sorted((r/'tmp/step5').glob(sys.argv[1]+'/detail.bin')):
 data=p.read_bytes();raw=hashlib.sha256(data).hexdigest();q=p.with_suffix('.bin.gz')
 with q.open('wb') as f:
  with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0,compresslevel=6) as z:z.write(data)
 assert hashlib.sha256(gzip.decompress(q.read_bytes())).hexdigest()==raw
 rows.append(dict(path=str(q.relative_to(r)),raw_sha256=raw,raw_bytes=len(data),gzip_bytes=q.stat().st_size));p.unlink()
(r/('manifest/'+sys.argv[2]+'.json')).write_text(json.dumps(rows,indent=2)+'\n');print(rows)
