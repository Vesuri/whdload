import os,shutil
from capture_demo import ROOT,command
from capture_session import Session
os.chdir(ROOT);out=ROOT/'tmp/prof/s5-wait-patch-debug';out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s5-wait-a.slave',out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0);s.env['WHD_ARGS']+=' CUSTOM1=1 CUSTOM3=6'
try:
 s.start(anchor=0xd73c6c,tag='debug');r=command('gdb info registers\nx/12hx $a0\nx/8hx $a1');print(r,flush=True);(out/'before.txt').write_text(r)
 r=command('gdb nexti\ninfo registers\nx/8hx 0xd694d2',timeout=60);print(r,flush=True);(out/'after.txt').write_text(r)
finally:s.close()
