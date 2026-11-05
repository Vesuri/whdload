"""Separate MMU-on functional checks; never use these runs for timing claims."""
import json,os,struct,shutil
from capture_demo import ROOT,command
from capture_session import Session
from count_demo_swaps import count
from check_disabled import check
from PIL import Image
os.chdir(ROOT)
for profile,cpu in [('a4000-040-25','68040'),('a4000-060-50','68060')]:
 out=ROOT/'tmp/prof'/('s2-mmu-'+cpu);out.mkdir(exist_ok=False)
 shutil.copyfile(ROOT/'tmp/build/HardDrivin-drive.slave',out/'slave.slave')
 s=Session(out,profile,out/'slave.slave',0x10ed4);s.env['CPU']=cpu
 try:
  print('FUNCTIONAL',cpu,flush=True);s.boot();r=count(s,500);images=s.dump_banks('after')
  def read(a,n):
   for base,b in images:
    if base<=a and a+n<=base+len(b):return b[a-base:a-base+n]
   raise ValueError(hex(a))
  a4=s.layout['a4'];front=struct.unpack('>I',read(a4-0x6a0e,4))[0];palette=struct.unpack('>I',read(a4-0x7036,4))[0]
  b=read(front,32000);colors=struct.unpack('>16H',read(palette,32));pal=[tuple(((c>>shift)&15)*17 for shift in [8,4,0]) for c in colors]
  im=Image.new('RGB',(320,200));im.putdata([pal[sum(((b[k*8000+y*40+x//8]>>(7-x%8))&1)<<k for k in range(4))] for y in range(200) for x in range(320)]);im.resize((640,400),Image.Resampling.NEAREST).save(out/'cockpit.png')
  assert r['swaps']>0;assert check(out,['VERIFY_DRIVE'])['passed']
  (out/'functional.json').write_text(json.dumps(dict(cpu=cpu,fields_observed=500,swaps=r['swaps'],disabled_ranges_pass=True,timing_valid=False),indent=2)+'\n');print(cpu,r['swaps'],'functional only',flush=True)
 finally:s.close()
