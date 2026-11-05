"""Calibrate live hunk placement, reboot with an armed anchor, retain configuration."""
import os,time,subprocess,sys,json,struct,hashlib
from pathlib import Path
from capture_demo import ROOT,SOCK,RUN,command,sha
from machine_profiles import environment,banks
from game_image import hunks
class Session:
 def __init__(self,out,profile,slave,offset,custom4=0):
  self.out=out;self.rel=out.relative_to(ROOT);self.env=environment(profile,slave,custom4);self.profile=profile;self.offset=offset;self.proc=None;self.log=None
 def close(self):
  if not self.proc:return
  try:
   command('quit',timeout=10)
   self.proc.wait(timeout=10)
  except (OSError,RuntimeError,subprocess.TimeoutExpired):
   # Only this harness's recorded PIDs, checked by the shared process helper.
   subprocess.run(['/bin/bash','-c', '. "$1"; . "$FSUAE_COMMON"; fsuae_kill_recorded "$2" gdb; fsuae_kill_recorded "$3" fs-uae', 'cleanup',str(ROOT/'tools/env.sh'),str(RUN/'gdb.pid'),str(RUN/'fsuae.pid')],check=False)
   if self.proc.poll() is None:self.proc.terminate()
   self.proc.wait(timeout=10)
  finally:self.log.close();self.proc=None
 def start(self,anchor=None,tag='run'):
  if SOCK.exists():
   try:command('quit')
   except (ConnectionError,FileNotFoundError):pass
  e=dict(self.env)
  if anchor is not None:e['BOOT_BREAK']=hex(anchor)
  self.log=(self.out/(tag+'-server.log')).open('w');self.proc=subprocess.Popen([sys.executable,str(ROOT/'tools/harddrivin.py'),'serve'],env=e,stdout=self.log,stderr=subprocess.STDOUT)
  deadline=time.monotonic()+int(e['SERVE_WAIT'])
  while 'serving on' not in (self.out/(tag+'-server.log')).read_text():
   assert self.proc.poll() is None,'server exited'
   if time.monotonic()>deadline:raise TimeoutError('Anchor/server timeout; inspect '+str(self.out))
   time.sleep(.25)
 def dump_banks(self,tag):
  result=[]
  for name,base,size in banks(self.env):
   path=self.out/(tag+'-'+name+'.bin');command(f'gdb dump binary memory {path.relative_to(ROOT)} {base:#x} {base+size:#x}')
   result.append((base,path.read_bytes()))
  return result
 def locate(self,images):
  def read(addr,size):
   for base,b in images:
    if base<=addr and addr+size<=base+len(b):return b[addr-base:addr-base+size]
   raise ValueError(hex(addr))
  hits=[]
  for bank,b in images:
   pos=0
   while (pos:=b.find(bytes.fromhex('00011a4e'),pos))>=0:
    if pos>=4 and pos%2==0:
     ptr=struct.unpack_from('>I',b,pos-4)[0]
     try:
      if read(ptr+6,10)==bytes.fromhex('48e700c06104508f4e75'):hits.append((bank+pos-4,ptr))
     except ValueError:pass
    pos+=2
  assert len(hits)==1,hits
  pub,code=hits[0];a4=struct.unpack('>I',read(code+0x11a76,4))[0];data=a4-0x7ffe
  # LoadSeg links precede each hunk body. The second link locates the 4-byte BSS.
  tail=struct.unpack('>I',read(data-4,4))[0]*4+4
  hs=hunks();regions=[dict(name=n,base=b,size=h['size']) for n,b,h in zip(['code','data','bss'],[code,data,tail],hs)]
  assert tail>4 and read(code,2)==b'\x4e\xf9'
  return dict(code_base=code,data_base=data,a4=a4,published=pub,regions=regions,profile=self.profile)
 def boot(self):
  # No persistent address cache: calibration belongs to the exact retained slave/profile.
  self.start(tag='calibration')
  layout=None
  for _ in range(20):
   command('wait 1');command('stop')
   images=self.dump_banks('calibration')
   try:layout=self.locate(images);break
   except (AssertionError,ValueError):continue
  assert layout,'live game not found'
  self.close();self.start(layout['code_base']+self.offset)
  regs=command('gdb info registers pc a4');expected=layout['code_base']+self.offset
  assert re_register(regs,'pc')==expected
  actual=self.locate(self.dump_banks('anchor'));assert actual==layout,'layout changed after calibration reboot'
  assert re_register(regs,'a4')==layout['a4']
  self.layout=layout;(self.out/'anchor.txt').write_text(regs)
  cfg=RUN/'fsuae/Cache/Logs/debug.uae'
  if cfg.exists():(self.out/'emulator.uae').write_bytes(cfg.read_bytes())
  self.metadata=dict(layout=layout,anchor_offset=hex(self.offset),slave_sha256=sha(self.env['SLAVE']),emulator_sha256=sha(self.env['FSUAE']),game_sha256=sha(__import__('game_image').GAME),configuration={k:self.env[k] for k in ['AMIGA_MODEL','CPU','CHIP_KB','FAST_KB','SLOW_KB','MOTHERBOARD_KB','EXTRA_ARGS','WHD_ARGS','SWAP_ONLY','SERVE_WAIT']})
  (self.out/'metadata.json').write_text(json.dumps(self.metadata,indent=2)+'\n')
  for r in layout['regions']:command(f"gdb dump binary memory {self.rel}/game-{r['name']}.bin {r['base']:#x} {r['base']+r['size']:#x}")
  return layout

def re_register(text,name):
 import re
 return int(re.search(r'^'+name+r'\s+0x([0-9a-f]+)',text,re.M).group(1),16)
