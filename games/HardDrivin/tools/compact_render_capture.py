"""Compact completed rendering captures and remove only their dead owned runtime."""
import os,sys,json,hashlib,subprocess,shutil
from pathlib import Path
name,instance=sys.argv[1:];assert name.startswith('s5-') and instance.startswith('s5') and '/' not in name+instance
p=Path('tmp/prof')/name;assert (p/'render-costs.json').exists() or (p/'render-result.json').exists()
def digest(f):
 h=hashlib.sha256()
 while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()
r={'compressed':[]}
for f in [p/'trace.bin',*p.glob('calibration-*.bin')]:
 if not f.exists():continue
 z=f.with_suffix(f.suffix+'.zst');assert not z.exists()
 with f.open('rb') as stream:h=digest(stream)
 subprocess.run(['zstd','-q','-3',str(f),'-o',str(z)],check=True)
 proc=subprocess.Popen(['zstd','-qdc',str(z)],stdout=subprocess.PIPE);got=digest(proc.stdout);assert proc.wait()==0 and got==h
 r['compressed'].append(dict(file=f.name,sha256=h,bytes_saved=f.stat().st_size-z.stat().st_size));f.unlink()
run=Path('tmp/run')/(instance or 'default')/'.run';assert run.is_dir();pids=[]
for f in run.glob('*.pid'):
 pid=int(f.read_text().strip());pids.append(pid)
 try:os.kill(pid,0)
 except ProcessLookupError:pass
 else:raise RuntimeError(f'{pid} still active')
r['runtime']=dict(instance=instance,dead_pids=pids,bytes_removed=sum(f.stat().st_size for f in run.rglob('*') if f.is_file() and not f.is_symlink()));shutil.rmtree(run)
(p/'cleanup.json').write_text(json.dumps(r,indent=2)+'\n');print(name,sum(x['bytes_saved'] for x in r['compressed'])+r['runtime']['bytes_removed'],flush=True)
