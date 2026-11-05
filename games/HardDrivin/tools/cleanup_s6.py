from pathlib import Path
import os,json,gzip,hashlib,shutil
root=Path('.');saved=0;compressed=0;removed=[];live=[]
for p in (root/'tmp/prof').glob('s6*'):
 if not p.is_dir():continue
 # Keep the active score test and its reload inputs available uncompressed.
 if p.name.startswith('s6-flow') or p.name=='s6-score-reload':continue
 if not any((p/f).exists() for f in ['render-result.json','disabled.json','results.json']):continue
 for f in p.glob('*.bin'):
  z=f.with_suffix(f.suffix+'.gz');data=f.read_bytes()
  if not z.exists():
   with gzip.open(z,'wb',compresslevel=1) as out:out.write(data)
  with gzip.open(z,'rb') as inp:assert hashlib.sha256(inp.read()).digest()==hashlib.sha256(data).digest()
  saved+=len(data)-z.stat().st_size;compressed+=1;f.unlink()
for instance in (root/'tmp/run').glob('s6*'):
 run=instance/'.run'
 if not run.is_dir() or run.is_symlink():continue
 alive=False
 for pidfile in run.glob('*.pid'):
  try:os.kill(int(pidfile.read_text().strip()),0)
  except ProcessLookupError:pass
  else:alive=True
 if alive:live.append(instance.name);continue
 saved+=sum(f.stat().st_size for f in run.rglob('*') if f.is_file() and not f.is_symlink());shutil.rmtree(run);removed.append(instance.name)
r=dict(bytes_saved=saved,compressed_files=compressed,removed_dead_runtimes=removed,preserved_live=live)
(root/'tmp/s6-cleanup.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
