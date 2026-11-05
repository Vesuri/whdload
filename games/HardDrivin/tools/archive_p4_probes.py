from pathlib import Path
import hashlib,subprocess
from trace_fingerprints import fingerprint
root=Path('tmp/prof')
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
for name in ['p4-first-a-on', 'p4-first-b-on', 'p4-current-a-on', 'p4-current-b-on', 'p4-fast-a-on', 'p4-fast-b-on', 'p4-lean2-a-on', 'p4-lean2-b-on', 'p4-next-a-on', 'p4-next-b-on', 'p4-check-a-off', 'p4-check-a-on', 'p4-check-b-off', 'p4-check-b-on']:
 p=root/name;trace=p/'trace.bin'
 if not trace.exists():continue
 fingerprint(p);expected=sha(trace);(p/'trace.sha256').write_text(expected+'\n')
 subprocess.run(['zstd','-q','-3',str(trace)],check=True)
 z=p/'trace.bin.zst';subprocess.run(['zstd','-qt',str(z)],check=True)
 h=hashlib.sha256();proc=subprocess.Popen(['zstd','-qdc',str(z)],stdout=subprocess.PIPE)
 for chunk in iter(lambda:proc.stdout.read(8*1024*1024),b''):h.update(chunk)
 assert proc.wait()==0 and h.hexdigest()==expected
 trace.unlink();print('Archived and verified',name,flush=True)
