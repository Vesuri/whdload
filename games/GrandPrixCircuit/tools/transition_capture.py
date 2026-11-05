#!/usr/bin/env python3
"""Read-only observation of an isolated test build: Monza qualifying and race."""
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
 else:raise RuntimeError('calibration did not reach patched program')
 h=rr['gpc'];sb=rr['slave'];close();print(name,'calibrated',flush=True)
 g=server.boot();until(h);until(h+0x7094);a4=value('$a4');dump('qual-start')
 assert word(a4-31430)==6 and word(a4+3846)==0
 print(name,'Monza qualifying started',flush=True)
 until(h+0xe8a);dump('qual-finished');print(name,'qualifying returned',flush=True)
 until(h+0xb74);dump('transition');assert word(a4+3846)==1
 print(name,'native race call reached',flush=True)
 until(h+0x7094);dump('race-start')
 print(name,'race grid', [word(a4+3732+2*i) for i in range(10)],flush=True)
 cmd(f'break *{h+0x772a:#x}');cmd(f'break *{h+0x8e4e:#x}')
 r=cmd(f'''set $sf=0
while $sf < 900
continue
if $pc == {h+0x772a:#x}
set $sf=$sf+1
else
printf "DRAW %d %d %d %d %d\\n", $sf, *(short*){a4-1518:#x}, (short)$d4, (short)$d5, *(short*){a4-29944:#x}
end
end
delete
''')
 rows=[list(map(int,x)) for x in re.findall(r'^DRAW (\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+)$',r,re.M)]
 (out/'draws.json').write_text(json.dumps(rows)+'\n')
 dump('race-end');server.handle(g,f'shot {out}/race-end.png')
 print(name,'draw count',len(rows),'speed',sorted(set(x[4] for x in rows)),flush=True)
except BaseException:
 try:
  g.running=True;g.stop();cmd('delete');server.handle(g,f'shot {out}/failure.png');dump('failure')
 except Exception as e:print('failure capture',repr(e),flush=True)
 raise
finally:
 close()
