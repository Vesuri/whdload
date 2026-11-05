#!/usr/bin/env python3
"""Read-only normal-build title/race and native attract-exit checks, not FPS runs."""
import os,re,time,json,struct,shutil,hashlib
from pathlib import Path
from gpc import server,ROOT
from gpc_report import regions
# Match the requested A1200 profile when no explicit ROM override was supplied.
if os.environ.get('AMIGA_MODEL')=='A1200' and 'KICKSTART' not in os.environ:
 os.environ['KICKSTART']=str(Path.home()/'.local/share/amiga/Kickstarts/kick40068.A1200')
root=Path(ROOT);name=os.environ['CELL'];out=Path(os.environ.get('OUT_ROOT','tmp/phase5'))/('normal-'+name);out.mkdir(parents=True,exist_ok=True)
slave=Path(os.environ['SLAVE']);shutil.copyfile(slave,out/'slave.slave');shutil.copyfile(slave.with_suffix('.lst'),out/'slave.slave.lst')
base=0x200000 if int(os.environ.get('FAST_KB','0')) else 0xc00000
size=int(os.environ.get('FAST_KB','0') or 0)*1024 if base==0x200000 else 1536*1024
if base==0x200000:
 base+=size-1536*1024;size=1536*1024
log=[]
def cmd(s):
 r=g.cmd(s,timeout=240);log.append(s+'\n'+r);(out/'debugger.txt').write_text('\n'.join(log));assert 'Error' not in r and 'Cannot access' not in r,r;return r
def value(s):
 r=cmd('p/x '+s);return int(re.search(r'=\s*(0x[0-9a-f]+|\d+)',r).group(1),0)
def word(a):return value(f'*(unsigned short*){a:#x}')
def long(a):return value(f'*(unsigned int*){a:#x}')
def dump(n):
 cmd(f'dump binary memory {out}/{n}.bin {base:#x} {base+size:#x}');return (out/(n+'.bin')).read_bytes()
def until(a):
 cmd('delete');cmd(f'break *{a:#x}');cmd('continue');assert value('$pc')==a;cmd('delete')
def close():
 if server.g is not None:server.handle(g,'quit');server.g=None;server.lldb=None
listing=(Path(slave.with_suffix('.lst'))).read_text(encoding='latin1')
def symbol(name):
 lines=listing.splitlines()
 for i,line in enumerate(lines):
  if re.search(r'\b'+name+r':',line):
   for l in lines[i:]:
    m=re.match(r'00:([0-9A-F]+) ',l)
    if m:return int(m[1],16)
 raise ValueError(name)
result={'slave_sha256':hashlib.sha256(slave.read_bytes()).hexdigest(),'custom2':int(os.environ['CUSTOM2_VALUE'])}
try:
 g=server.boot()
 runtime=Path('tmp/run/default/.run/dh1/WHDLoad').read_bytes()
 result['whdload_sha256']=hashlib.sha256(runtime).hexdigest()
 result['whdload_version']=re.search(rb'\$VER:[^\0\r\n]+',runtime)[0].decode('latin1')
 for n in range(30):
  g.cont();time.sleep(10 if n==0 else 2);g.stop();d=dump('calibration')
  try:rr={n:lo for lo,hi,n,o in regions(d,base)}
  except (ValueError,KeyError):continue
  if 'gpc-data' in rr and d[rr['gpc']-base+0x39e:rr['gpc']-base+0x3a0]==bytes.fromhex('4ef9'):break
 else:raise RuntimeError('calibration did not reach patched program')
 h=rr['gpc'];sb=rr['slave'];close();print(name,'calibrated',flush=True)
 g=server.boot();until(h);d=dump('entry');rr2={n:lo for lo,hi,n,o in regions(d,base)};assert rr==rr2
 until(h+0x4d94);server.handle(g,f'shot {out}/title.png');dump('intro');print(name,'title',flush=True)
 if os.environ.get('INTRO_TRACE'):
  from amigaxdev import barto
  requested=int(os.environ['INTRO_TRACE']);remaining=requested;parts=[]
  server.profile_window=True
  while remaining:
   count=min(100,remaining);target=out/f'intro-trace-{len(parts):02d}.bin'
   server.capture(g,count,str(target.resolve()))
   trace=barto.load(target);actual=len(trace.fields);del trace
   assert actual==count,(actual,count)
   parts.append(dict(file=target.name,fields=actual));remaining-=actual
   print(name,'captured',requested-remaining,'fields',flush=True)
  (out/'audio-capture.json').write_text(json.dumps(dict(requested_fields=requested,parts=parts),indent=2)+'\n')
  dump('intro-after')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(name,'INTRO_CAPTURE_COMPLETE',flush=True)

except BaseException:
 try:
  g.running=True;g.stop();cmd('delete');server.handle(g,f'shot {out}/failure.png')
  (out/'failure-registers.txt').write_text(cmd('info all-registers'))
  dump('failure')
 except Exception as e:print('failure capture:',repr(e),flush=True)
 raise
finally:
 for candidate in (Path('tmp/run/default/.run/fsuae/Cache/Logs/debug.uae'),Path('tmp/run/default/.run/fsuae/Cache/Logs/fs-uae.log.txt')):
  if candidate.exists():
   if candidate.name=='debug.uae':shutil.copyfile(candidate,out/candidate.name)
   else:(out/'mmu-log.txt').write_text('\n'.join(l for l in candidate.read_text(errors='replace').splitlines() if any(t in l for t in ('CPU=','MMU:','JIT compiler')))+'\n')
 close()
