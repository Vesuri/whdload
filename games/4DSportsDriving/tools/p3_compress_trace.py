import hashlib,json,sys
from pathlib import Path
from compression import zstd as z
p=Path(sys.argv[1]);raw=p/'trace.bin';dst=p/'trace.bin.zst';assert not dst.exists()
h=hashlib.sha256();size=raw.stat().st_size
with raw.open('rb') as src,z.open(dst,'wb',level=3) as writer:
 while b:=src.read(8*1024*1024):h.update(b);writer.write(b)
v=hashlib.sha256();n=0
with z.open(dst,'rb') as rd:
 while b:=rd.read(8*1024*1024):v.update(b);n+=len(b)
assert n==size and h.digest()==v.digest()
r=dict(raw_bytes=size,sha256=h.hexdigest(),compressed_bytes=dst.stat().st_size,verified_decompression_sha256=v.hexdigest())
(p/'trace-storage.json').write_text(json.dumps(r,indent=2)+'\n');raw.unlink();print(r)
