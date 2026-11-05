import os,json,shutil
from capture_demo import ROOT,command
from capture_session import Session
os.chdir(ROOT);out=ROOT/'tmp/prof/s5-wait-boot-debug';out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s5-wait-a.slave',out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0);s.env['WHD_ARGS']+=' CUSTOM1=1 CUSTOM3=6'
try:
 s.start(tag='debug')
 for i in range(4):
  command('wait 1');command('stop');r=command('gdb info registers\nx/10i $pc');(out/f'registers-{i}.txt').write_text(r);print(r[:1300],flush=True)
 s.layout=s.locate(s.dump_banks('debug'));(out/'layout.json').write_text(json.dumps(s.layout));print(s.layout,flush=True)
finally:s.close()
