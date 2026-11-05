from pathlib import Path
import os, json, shutil, gzip, hashlib, time
root=Path.cwd(); base=root; removed=[]; packed=[]; skipped=[]; saved=0
prof=base/'tmp/prof'
for f in prof.rglob('*'):
 if not f.is_file() or f.is_symlink(): continue
 name=f.name
 if name in ('trace.bin','trace.bin.zst','trace.bin.gz','continuous-check.bin','continuous-check-2.bin') or f.suffix=='.lst':
  n=f.stat().st_size;f.unlink();saved+=n;removed.append(str(f.relative_to(root)))
print('Removed old traces/listings:',round(saved/1e9,2),'GB',flush=True)
for run in (base/'tmp/run').rglob('.run'):
 if not run.is_dir() or run.is_symlink():continue
 if any(part.startswith('play-') for part in run.parts):skipped.append(str(run.relative_to(root)));continue
 alive=False
 for p in run.rglob('*.pid'):
  try:
   pid=int(p.read_text().strip()); os.kill(pid,0);alive=True
  except ProcessLookupError:pass
  except (ValueError,PermissionError):alive=True
 if alive:skipped.append(str(run.relative_to(root)));continue
 # Preserve screenshots, configurations and high scores from disposable runtimes.
 keep=run.parent/'retained-runtime-files'
 for f in run.rglob('*'):
  if not f.is_file() or f.is_symlink():continue
  if f.suffix.lower() in ('.png','.jpg','.fs-uae','.uae') or 'high' in f.name.lower() or 'score' in f.name.lower():
   target=keep/f.relative_to(run);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
 n=sum(f.stat().st_size for f in run.rglob('*') if f.is_file() and not f.is_symlink())
 shutil.rmtree(run);saved+=n;removed.append(str(run.relative_to(root)))
print('After stopped runtimes:',round(saved/1e9,2),'GB',flush=True)
# Retain compact memory fixtures; verify compression before removing originals.
for f in prof.rglob('*.bin'):
 if f.is_symlink() or f.stat().st_size<262144:continue
 data=f.read_bytes(); z=f.with_suffix('.bin.gz')
 if not z.exists():
  with gzip.open(z,'wb',compresslevel=1) as out:out.write(data)
 with gzip.open(z,'rb') as inp:
  assert hashlib.sha256(inp.read()).digest()==hashlib.sha256(data).digest(),str(f)
 saved+=len(data)-z.stat().st_size;f.unlink();packed.append(str(f.relative_to(root)))
 if len(packed)%1000==0:print('Compressed',len(packed),'memory fixtures;',round(saved/1e9,2),'GB reclaimed',flush=True)
report=dict(bytes_reclaimed=saved,removed=removed,compressed=packed,preserved_runtimes=skipped)
(base/'tmp/cleanup-completed-work.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(bytes_reclaimed=saved,removed_count=len(removed),compressed_count=len(packed),preserved_runtimes=skipped)),flush=True)
