#!/usr/bin/env python3
"""Read-only normal-build title/race and native attract-exit checks, not FPS runs."""
import os,re,time,json,struct,shutil,hashlib
from pathlib import Path
from gpc import server,ROOT
from gpc_report import regions
root=Path(ROOT);name=os.environ['CELL'];out=Path('tmp/phase6')/('normal-'+name);out.mkdir(parents=True,exist_ok=True)
slave=Path(os.environ['SLAVE']);shutil.copyfile(slave,out/'slave.slave');shutil.copyfile(slave.with_suffix('.lst'),out/'slave.slave.lst')
base=0x200000 if int(os.environ.get('FAST_KB','0')) else 0xc00000
size=int(os.environ.get('FAST_KB','0') or 0)*1024 if base==0x200000 else 1536*1024
log=[]
def cmd(s):
 r=g.cmd(s,timeout=240);log.append(s+'\n'+r);(out/'debugger.txt').write_text('\n'.join(log));assert not any(x in r for x in ('Error','Cannot access','Invalid hex digit')),r;return r
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
 g=server.boot();cmd('set remote memory-read-packet-size 1024')
 for n in range(30):
  g.cont();time.sleep(1);g.stop();d=dump('calibration')
  try:rr={n:lo for lo,hi,n,o in regions(d,base)}
  except (ValueError,KeyError):continue
  if 'gpc-data' in rr and d[rr['gpc']-base+0x39e:rr['gpc']-base+0x3a0]==bytes.fromhex('4ef9'):break
 else:raise RuntimeError('calibration did not reach patched program')
 h=rr['gpc'];sb=rr['slave'];close();print(name,'calibrated',flush=True)
 g=server.boot();cmd('set remote memory-read-packet-size 1024');until(h);d=dump('entry');rr2={n:lo for lo,hi,n,o in regions(d,base)};assert rr==rr2
 (out/'metadata.json').write_text(json.dumps({'base':base,'code_base':h,'data_base':rr['gpc-data'],'slave_sha256':result['slave_sha256'],'normal_build':True,'options':{k:os.environ.get(k) for k in ['CPU','AMIGA_MODEL','CHIP_KB','FAST_KB','SLOW_KB','WHD_ARGS','EXTRA_ARGS']}},indent=2)+'\n')
 until(h+0x4d94);server.handle(g,f'shot {out}/title.png');print(name,'title',flush=True)
 until(h+0x7094)
 for n in range(40):until(h+0x39e)
 server.handle(g,f'shot {out}/race.png');d=dump('race');shutil.copyfile(out/'race.bin',out/'before.bin')
 # Exercise the native attract-race exit without debugger writes or fake input.
 until(h+0x75c8);a4=value('$a4');pending=sb+symbol('render_swap_pending');epoch=sb+symbol('render_swap_epoch')
 before={'pending':word(pending),'epoch':long(epoch),'native_field':long(a4-31790)}
 until(h+0x75ce)
 assert word(pending)==0
 after={'pending':word(pending),'native_field':long(a4-31790)}
 if before['pending']:assert after['native_field']!=before['epoch']
 result['native_race_exit']={'before':before,'after':after}
 result['pause_and_program_return']='static review only; debugger write probes rejected because writes are ignored'
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(name,'PASS',json.dumps(result),flush=True)

finally:close()
