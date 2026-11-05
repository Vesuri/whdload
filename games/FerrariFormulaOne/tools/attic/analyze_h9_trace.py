from pathlib import Path
import subprocess,sys,gzip,hashlib,shutil,json
r=Path(__file__).resolve().parents[1];p=Path(sys.argv[1]);raw=p/'detail.bin'
for script in ['analyze_hi25_profile.py','analyze_h8_calls.py','analyze_hi25_blits.py','audit_h7_trace.py']:
 with (p/(script+'.log')).open('w') as f:subprocess.run([sys.executable,str(r/'tools'/script),str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
sha=hashlib.file_digest(raw.open('rb'),'sha256').hexdigest();z=raw.with_suffix('.bin.gz')
with raw.open('rb') as a,gzip.open(z,'wb',compresslevel=6) as b:shutil.copyfileobj(a,b)
with gzip.open(z,'rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==sha
(p/'h9-trace-hash.json').write_text(json.dumps(dict(sha256=sha,raw_bytes=raw.stat().st_size,compressed_bytes=z.stat().st_size),indent=2)+'\n');raw.unlink()
print(json.loads((p/'hi25-analysis.json').read_text())['mean_after_wait_ms'])
