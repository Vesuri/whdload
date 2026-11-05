"""Compress only named completed gate traces/calibration banks; retain verified bytes."""
from pathlib import Path
import sys,subprocess,hashlib,json,os,shutil
prefix=sys.argv[1];instances=sys.argv[2:];report={'compressed':[],'runtimes':[]}
def digest(stream):
 h=hashlib.sha256()
 while b:=stream.read(1024*1024):h.update(b)
 return h.hexdigest()
for w in ['a','b']:
 for state in ['off','on']:
  p=Path('tmp/prof')/(prefix+'-'+w+'-'+state)
  assert json.loads((p/'trace-check.json').read_text())['passed']
  for f in [p/'trace.bin',*sorted(p.glob('calibration-*.bin'))]:
   if not f.exists():continue
   z=f.with_suffix(f.suffix+'.zst');assert not z.exists()
   with f.open('rb') as src:sha=digest(src)
   subprocess.run(['zstd','-q','-3',str(f),'-o',str(z)],check=True)
   proc=subprocess.Popen(['zstd','-q','-d','-c',str(z)],stdout=subprocess.PIPE)
   restored=digest(proc.stdout);assert proc.wait()==0 and restored==sha
   report['compressed'].append(dict(path=str(f),sha256=sha,original=f.stat().st_size,compressed=z.stat().st_size));f.unlink()
for instance in instances:
 assert instance.startswith('c5-') and '/' not in instance
 p=Path('tmp/run')/(instance or 'default')/'.run';assert p.is_dir();pids=[]
 for f in p.glob('*.pid'):
  pid=int(f.read_text().strip());pids.append(pid)
  try:os.kill(pid,0)
  except ProcessLookupError:pass
  else:raise RuntimeError(f'PID {pid} still live; refusing cleanup')
 size=sum(f.stat().st_size for f in p.rglob('*') if f.is_file() and not f.is_symlink())
 shutil.rmtree(p);report['runtimes'].append(dict(instance=instance,pids=pids,recorded_pids_dead=True,removed_bytes=size))
report['reclaimed_bytes']=sum(x['original']-x['compressed'] for x in report['compressed'])+sum(x['removed_bytes'] for x in report['runtimes'])
Path('tmp/'+prefix+'-cleanup.json').write_text(json.dumps(report,indent=2)+'\n');print(prefix,report['reclaimed_bytes'],flush=True)
