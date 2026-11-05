from pathlib import Path
import hashlib,subprocess
from trace_fingerprints import fingerprint
root=Path('tmp/prof')
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
for name in ['p2-probe', 'p2-recip', 'p2-defer', 'p2-fast', 'p2-final-a-off', 'p2-final-a-on', 'p2-shared', 'p2-shared-b', 'p2-shared-a-off', 'p2-shared-b-off', 'p2-swap']:
 p=root/name;trace=p/'trace.bin'
 if not trace.exists():continue
 fingerprint(p);expected=sha(trace);(p/'trace.sha256').write_text(expected+'\n')
 subprocess.run(['zstd','-q','-3',str(trace)],check=True)
 z=p/'trace.bin.zst';subprocess.run(['zstd','-qt',str(z)],check=True)
 h=hashlib.sha256();proc=subprocess.Popen(['zstd','-qdc',str(z)],stdout=subprocess.PIPE)
 for chunk in iter(lambda:proc.stdout.read(8*1024*1024),b''):h.update(chunk)
 assert proc.wait()==0 and h.hexdigest()==expected
 trace.unlink();print('Archived and verified',name,flush=True)
