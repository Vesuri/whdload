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
 for n in range(30):
  g.cont();time.sleep(10 if n==0 else 2);g.stop();d=dump('calibration')
  try:rr={n:lo for lo,hi,n,o in regions(d,base)}
  except (ValueError,KeyError):continue
  if 'gpc-data' in rr and d[rr['gpc']-base+0x39e:rr['gpc']-base+0x3a0]==bytes.fromhex('4ef9'):break
 else:raise RuntimeError('calibration failed')
 h=rr['gpc'];sb=rr['slave'];close();print(name,'calibrated',flush=True)
 g=server.boot();until(h);until(h+0x7094)
 for _ in range(40):until(h+0x39e)
 a4=value('$a4');dump('scene');cmd(f'dump binary memory {out}/chip.bin 0 0x80000');server.handle(g,f'shot {out}/scene.png')
 if os.environ.get('HORIZON_TRACE'):
  until(h+0x8246)
  while word(a4-30580)!=0 or word(a4-20714)!=0x8200:until(h+0x8246)
  dump('trace-before');server.profile_window=True
  server.capture(g,4,str((out/'trace.bin').resolve()))
 samples=[]
 for i in range(64):
  until(h+0x8246)
  while word(a4-30580)!=0:until(h+0x8246)
  heading=word(a4-20714)
  until(h+0x82e8)
  if i==0:memory=dump('horizon')
  bitmap=long(a4+3590);ptrs=list(struct.unpack_from('>5I',memory,bitmap-base+8))
  cmd(f'dump binary memory {out}/pan-{i:02d}.bin 0 0x80000')
  samples.append(dict(index=i,heading=heading,pan=heading//64,planes=ptrs))
  if i%16==15:print(name,len(samples),'pan samples',flush=True)
 (out/'samples.json').write_text(json.dumps(samples,indent=2)+'\n')

finally:
 close()
