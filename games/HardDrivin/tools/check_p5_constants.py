"""Exhaustive unsigned interval cache and contact coefficient validation."""
from pathlib import Path
import json,os,random,re,struct,subprocess
exec(Path('tools/check_native_engine_model.py').read_text().split('results=[]')[0])
r=Path('src');t=(r/'HardDrivinTime.s').read_text();d=(r/'HardDrivinDecay.s').read_text();c=(r/'HardDrivinContact.s').read_text()
b=t[t.index('FC_THROTTLE equ'):t.index('\n_time_pause:')];b=b[:b.rfind('\tENDC')]
c=c[c.index('_contact_response:'):c.index('; D0.L signed Q16')]
stem=Path('tmp/p5-compact-constants');stem.with_suffix('.s').write_text(' org $400100\nVERIFY_TIME_MOTION equ 1\n'+b+d+c+'\n_time_scalar_fields: dc.w 8\n')
subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-L',str(stem.with_suffix('.lst')),'-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
sy={n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+A:([0-9A-F]+)',stem.with_suffix('.lst').read_text(),re.M)};write(0x400100,stem.with_suffix('.bin').read_bytes());stop=0x490000;sp=0x4ffff0
rate_table=[0,18519,18192,17872,17560,17256,16958,16668,16384]
def invoke(name):
 reg(8,sp);pack(sp,'I',stop);ok(u.uc_emu_start(h,sy[name],stop,1000000,5000));assert reg(18)==stop and reg(8)==sp+4
checks=0
try:
 for n in [65535]+list(range(65536)):
  pack(sy['_time_scalar_fields'],'H',n);reg(5,a4);reg(1,0x480000);invoke('_time_prepare_constants');assert reg(1)==0x480000
  loss=[round(65536*(1-x**(n/8))) for x in [7/8,9/10,3/4]];rate=rate_table[n] if n<=8 else (loss[2]*8+n//2)//n
  actual=struct.unpack('>HH4i',read(sy['_time_frame_constants'],20));expected=(n,0,*loss,rate);assert actual==expected,(n,actual,expected)
  for helper,v in zip(['_decay_throttle','_decay_spin','_decay_contact'],loss):
   reg(10,n);invoke(helper);assert reg(10)==v,(helper,n,reg(10),v)
  if n in [0,1,2,7,8,9,15,16,31,255,327,328,655,32767,32768,65535]:
   for error in [-720,-361,-5,-1,0,1,5,361,720]:
    for half in [0,1]:
     reg(9,error&0xffffffff);reg(10,n);reg(11,half);invoke('_contact_response')
     if n==8:
      q=int(error/4);exp=(q*65536,(q>>half)*65536)
     else:exp=(error*loss[2],(error*rate)>>half)
     assert (reg(9),reg(10))==tuple(x&0xffffffff for x in exp),(n,error,half,reg(9),reg(10),exp)
     checks+=1
 # Every decay routine must fall back to its original table for a different n.
 for n in range(65536):
  for helper,x in [('_decay_throttle',7/8),('_decay_spin',9/10),('_decay_contact',3/4)]:
   reg(10,n);invoke(helper);assert reg(10)==round(65536*(1-x**(n/8)))
 report=dict(passed=True,constant_blocks=65537,cached_coefficients=65537*3,mismatched_or_equal_coefficients=65536*3,contact_responses=checks)
 Path('tmp/p5-compact-constants-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
