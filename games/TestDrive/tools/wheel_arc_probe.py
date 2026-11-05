#!/usr/bin/env python3
"""Isolated release/VERIFY smoke and optional cost trace for the road fix."""
import os,sys,json,re,subprocess
from pathlib import Path
from harness import ROOT,sha,listing
from amigaxdev.gdbserve import Server
from private_run import private_server
from amigaxdev import barto
from td_report import regions
name,preset,variant=sys.argv[1:4];c2=int(sys.argv[4]);out=ROOT/'tmp/wheel-dot'/name;out.mkdir(parents=True)
slave=Path(os.environ['CORNER_SLAVE']) if os.environ.get('CORNER_SLAVE') else ROOT/'tmp/build'/('verify/TestDrive.Slave' if variant=='verify' else 'release/TestDrive.Slave')
profile_fields=int(os.environ.get('CORNER_PROFILE_FIELDS','50'))
import shutil
shutil.copyfile(slave,out/'slave.slave');shutil.copyfile(os.environ.get('CORNER_LISTING',listing(slave)),out/'slave.lst')
s=private_server('roadshift',out)
verify=variant=='verify';opts=json.loads(os.environ['ROAD_SHIFT_OPTIONS']) if os.environ.get('ROAD_SHIFT_OPTIONS') else dict(C1=2,C2=c2,C3=int(verify),C4=0,C5=3 if verify else 0)
env=dict(FSUAE=str(ROOT/'tmp/phase3/native-emulator/fs-uae'),TD_SETUP=preset if preset!='a1200-040' else '',AMIGA_SETUP='a1200-040' if preset=='a1200-040' else '',WARP='1',JOY0='none',SLAVE=str(out/'slave.slave'),WHD_ARGS=' '.join('CUSTOM'+k[1:]+'='+str(v if v<0x80000000 else v-0x100000000) for k,v in opts.items())+' CACHE',FSUAE_CLAIM_STRICT='1')
g=s.boot(env);h=0x1e548
try:
 g.cmd(f'break *{h+0xf6:#x}\ncondition $bpnum *(unsigned int*){h:#x} == 0x4e55ffcc && *(unsigned short*){h+0xf6:#x} == {0x4eb9 if verify else 0x2b6c}');g.cmd('continue',timeout=300);g.cmd('delete')
 g.cmd('cd '+str(ROOT));rel=out.relative_to(ROOT);machine=json.loads((out/'.run/machine.json').read_text());base=0xc00000 if preset=='a500' else 0x200000;size=int(machine['slow_memory'] if preset=='a500' else machine['fast_memory'])*1024;chip=int(machine['chip_memory'])*1024
 def snap(folder):
  folder.mkdir(exist_ok=True);prefix=folder.relative_to(ROOT);g.cmd(f'dump binary memory {prefix}/code.bin {base:#x} {base+size:#x}\ndump binary memory {prefix}/chip.bin 0 {chip:#x}')
 snap(out);rr={n:lo for lo,hi,n,o in regions((out/'code.bin').read_bytes(),base)}
 rr['h4']=h
 frame=int(re.search(r'a5\s+(0x[0-9a-f]+)',g.cmd('info registers a5'))[1],16)

 def photo(name):
  g.cmd(f'monitor profile 1 "" "{out}/{name}.bin"');(out/(name+'.png')).write_bytes(barto.load(out/(name+'.bin')).fields[-1].shot)
 g.cmd(f'break *{h+0x7f16:#x}\ncondition $bpnum *(short*)($a4-26214) <= -17\ncontinue\ndelete',timeout=300)
 snap(out/'steered');photo('steered')
 (out/'capture.json').write_text(json.dumps(dict(base=base,regions=rr,options=opts,frame=frame,slave_sha256=sha(out/'slave.slave')),indent=2)+'\n')
 print('CAPTURE '+name,flush=True)

finally:
 g.p.terminate();g.p.wait(timeout=5);pid=int((out/'.run/fsuae.pid').read_text());cmd=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True);assert str(out) in cmd and 'fs-uae' in cmd;os.kill(pid,15)
