#!/usr/bin/env python3
"""Isolated release/VERIFY smoke and optional cost trace for the road fix."""
import os,sys,json,re,subprocess
from pathlib import Path
from harness import ROOT,sha,listing
from amigaxdev.gdbserve import Server
from private_run import private_server
from amigaxdev import barto
from td_report import regions
name,preset,variant=sys.argv[1:4];c2=int(sys.argv[4]);out=ROOT/'tmp/road-shift'/name;out.mkdir()
slave=ROOT/'tmp/build'/('verify/TestDrive.Slave' if variant=='verify' else 'release/TestDrive.Slave')
import shutil
shutil.copyfile(slave,out/'slave.slave');shutil.copyfile(listing(slave),out/'slave.lst')
s=private_server('roadshift',out)
verify=variant=='verify';opts=json.loads(os.environ['ROAD_SHIFT_OPTIONS']) if os.environ.get('ROAD_SHIFT_OPTIONS') else dict(C1=0,C2=c2,C3=int(verify),C4=0,C5=65 if verify else 0)
env=dict(FSUAE=str(ROOT/'tmp/phase3/native-emulator/fs-uae'),TD_SETUP=preset if preset!='a1200-040' else '',AMIGA_SETUP='a1200-040' if preset=='a1200-040' else '',WARP='1',JOY0='none',SLAVE=str(out/'slave.slave'),WHD_ARGS=' '.join('CUSTOM'+k[1:]+'='+str(v if v<0x80000000 else v-0x100000000) for k,v in opts.items()),FSUAE_CLAIM_STRICT='1')
g=s.boot(env);h=0x1e548
try:
 g.cmd(f'break *{h+0xf6:#x}\ncondition $bpnum *(unsigned int*){h:#x} == 0x4e55ffcc && *(unsigned short*){h+0xf6:#x} == {0x4eb9 if verify else 0x2b6c}');g.cmd('continue',timeout=300);g.cmd('delete')
 g.cmd('cd '+str(ROOT));rel=out.relative_to(ROOT);machine=json.loads((out/'.run/machine.json').read_text());base=0xc00000 if preset=='a500' else 0x200000;size=int(machine['slow_memory'] if preset=='a500' else machine['fast_memory'])*1024;chip=int(machine['chip_memory'])*1024
 def snap(folder):
  folder.mkdir(exist_ok=True);prefix=folder.relative_to(ROOT);g.cmd(f'dump binary memory {prefix}/code.bin {base:#x} {base+size:#x}\ndump binary memory {prefix}/chip.bin 0 {chip:#x}')
 snap(out);rr={n:lo for lo,hi,n,o in regions((out/'code.bin').read_bytes(),base)}
 rr['h4']=h
 frame=int(re.search(r'a5\s+(0x[0-9a-f]+)',g.cmd('info registers a5'))[1],16)
 g.cmd('monitor fields 1000',timeout=300);snap(out/'trace-start')
 (out/'machine.json').write_text(json.dumps(machine,indent=2)+'\n');(out/'capture.json').write_text(json.dumps(dict(base=base,regions=rr,options=opts,fields=50,frame=frame,slave_sha256=sha(out/'slave.slave')),indent=2)+'\n')
 if os.environ.get('ROAD_SHIFT_VIEWS'):
  folder=out/'view-0';folder.mkdir();vr=folder.relative_to(ROOT);db=rr['td-data']
  for view,entry,ret in [('main',0x1114,0x116a),('mirror',0x11a2,0x11f2)]:
   g.cmd(f'break *{h+entry:#x}\ncontinue\ndelete',timeout=300)
   commands=[f'break *{h+0x1a38:#x}',f'break *{h+0x1b54:#x}','set $rs_row=0','continue',f'while $pc != {h+0x1b54:#x}',f'eval "dump binary memory {vr}/{view}-%02d.bin {db:#x} {db+0x32a4:#x}", $rs_row',f'eval "dump binary memory {vr}/{view}-%02d-desc.bin $a2 $a2+4", $rs_row','set $rs_row=$rs_row+1','continue','end','delete']
   (folder/(view+'-gdb.txt')).write_text(g.cmd('\n'.join(commands),timeout=300))
   g.cmd(f'dump binary memory {vr}/{view}-before.bin {db:#x} {db+0x32a4:#x}\nbreak *{h+ret:#x}\ncontinue\ndelete\ndump binary memory {vr}/{view}-after.bin {db:#x} {db+0x32a4:#x}',timeout=300)
  (folder/'metadata.json').write_text(json.dumps(rr,indent=2)+'\n')

 if preset=='a500' and not verify:(out/'profile.txt').write_text(g.cmd(f'monitor profile 50 "" "{out}/trace.bin"',timeout=300))
 snap(out/'end');g.cmd(f'monitor profile 1 "" "{out}/screen.bin"');(out/'screen.png').write_bytes(barto.load(out/'screen.bin').fields[-1].shot)
 (out/'quit.txt').write_text(g.cmd('monitor key 5d 1\nmonitor fields 40\nmonitor key 5d 0\nmonitor fields 80',timeout=300));g.cmd(f'monitor profile 1 "" "{out}/quit.bin"');(out/'quit.png').write_bytes(barto.load(out/'quit.bin').fields[-1].shot)
 print('SMOKE '+name,flush=True)
finally:
 g.p.terminate();g.p.wait(timeout=5);pid=int((out/'.run/fsuae.pid').read_text());cmd=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True);assert str(out) in cmd and 'fs-uae' in cmd;os.kill(pid,15)
