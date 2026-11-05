#!/usr/bin/env python3
"""Read-only intro-loop cadence comparison in isolated normal-release sessions."""
import os,sys,subprocess,shutil,json,re
from pathlib import Path
from harness import ROOT,sha
from check_inputs import check
from amigaxdev.gdbserve import Server
from private_run import private_server
from amigaxdev import barto
name,variant,cache=sys.argv[1:];out=ROOT/'tmp/intro-cadence'/name;out.mkdir(parents=True);check()
slave=ROOT/('tmp/build/TestDrive-1.4-rebuilt.slave' if variant=='baseline' else 'tmp/dist/2.0b/TestDrive.slave')
shutil.copyfile(slave,out/'slave.slave')
s=private_server('introcadence',out)
env=dict(FSUAE=str(ROOT/'tmp/phase3/native-emulator/fs-uae'),TD_SETUP='',AMIGA_SETUP='a1200-040',WARP='1',JOY0='none',WINDOW='back',SLAVE=str(out/'slave.slave'),WHD_ARGS=('CUSTOM2=1 ' if variant=='release' else '')+('CACHE' if cache=='1' else ''),FSUAE_CLAIM_STRICT='1')
g=s.boot(env)
try:
 g.cmd('cd '+str(out))
 sig=(ROOT/'tmp/phase2/overlay3.bin').read_bytes()[:32]
 h=None
 for attempt in range(30):
  g.cmd('monitor fields 200',timeout=120)
  reply=g.cmd('dump binary memory resolve.bin 0x200000 0xa00000')
  if not (out/'resolve.bin').exists():
   print(reply,flush=True);continue
  data=(out/'resolve.bin').read_bytes();start=0
  while True:
   at=data.find(sig,start)
   if at<0:break
   addr=0x200000+at
   if bytes.fromhex('4ef9')+addr.to_bytes(4,'big')+bytes.fromhex('00b6') in data:
    h=addr;break
   start=at+1
  if h is not None:break
 assert h is not None,'intro overlay not resolved'
 print('resolved h3 '+hex(h),flush=True)
 cmds=['set $intro_n=0']
 for off,label,phase in [(0x6be,'scroll','*(short*)($a5-12)')]:
  cmds += [f'break *{h+off:#x}',f'condition $bpnum *(unsigned int*){h:#x} == 0x4e55ffee','commands','silent',f'printf "INTRO {label} %d %d %d\\n", *(int*)($a4-31782), {phase}, *(short*)($a5-2)','set $intro_n=$intro_n+1','if *(short*)($a5-12) != 1 || *(short*)($a5-2) < 300','continue','end','end']
 g.cmd('\n'.join(cmds));log=g.cmd('continue',timeout=300);(out/'timing.txt').write_text(log)
 print('\n'.join(x for x in log.splitlines() if x.startswith('INTRO'))[-1200:],flush=True)
 g.cmd('delete');g.cmd(f'monitor profile 1 "" "{out}/screen.bin"');(out/'screen.png').write_bytes(barto.load(out/'screen.bin').fields[-1].shot)
 (out/'metadata.json').write_text(json.dumps(dict(slave_sha256=sha(slave),variant=variant,cache=cache,h3=h),indent=2)+'\n')
finally:
 g.p.terminate();g.p.wait(timeout=5);pid=int((out/'.run/fsuae.pid').read_text());cmd=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True);assert str(out) in cmd and 'fs-uae' in cmd;os.kill(pid,15)
