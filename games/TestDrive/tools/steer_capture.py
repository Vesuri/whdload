#!/usr/bin/env python3
"""Guest input-tape over-rev reproduction in a separate emulator session."""
import os,sys,json,re,shutil,subprocess
from pathlib import Path
from harness import ROOT,sha
from check_inputs import check
from amigaxdev.gdbserve import Server
from private_run import private_server
from amigaxdev import barto
name=sys.argv[1];car=int(sys.argv[2]);c2=int(sys.argv[3]);out=ROOT/'tmp/steer-reversal'/name
out.mkdir();check()
source=Path(os.environ.get('STEER_SOURCE',str(ROOT/'src')));stage=out/'source';shutil.copytree(source,stage)
p=stage/'simulation-verify.s';s=p.read_text().replace('verify_input:\n','verify_input:\n    moveq #-1,d1\n    rts\n',1);p.write_text(s)
args=[os.environ['VASM'],'-DVERIFY=1','-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym','-I'+os.environ['AMIGA_INCLUDE'],'-I'+os.environ['WHDLOAD']+'/Include','-I'+os.environ['WHDLOAD']+'/Src/sources','-I'+os.environ['AMIGA_SHARE']+'/ndk/Include_I','-L',str(out/'slave.lst'),'-o',str(out/'slave.slave'),'TestDriveHD.s']
subprocess.run(args,cwd=stage,check=True,stdout=(out/'build.log').open('w'))
srv=private_server('rpmneedle',out)
env=dict(FSUAE=str(ROOT/'tmp/phase3/native-emulator/fs-uae'),TD_SETUP='',AMIGA_SETUP='a1200-040',WARP='1',JOY0='none',SLAVE=str(out/'slave.slave'),WHD_ARGS=f'CUSTOM2={c2} CUSTOM3=1 CUSTOM5={1+car*256}',FSUAE_CLAIM_STRICT='1')
g=srv.boot(env);h=0x1e548
try:
 g.cmd(f'break *{h+0xf6:#x}\ncondition $bpnum *(unsigned int*){h:#x} == 0x4e55ffcc && *(unsigned short*){h+0xf6:#x} == 0x4eb9');g.cmd('continue',timeout=300);g.cmd('delete')
 a4=int(re.search(r'a4\s+(0x[0-9a-f]+)',g.cmd('info registers a4'))[1],16);db=a4-0x7ffe
 g.cmd('cd '+str(ROOT));rel=out.relative_to(ROOT);states=[]
 def capture(i,label):
  g.cmd(f'dump binary memory {rel}/data-{i:03}.bin {db:#x} {db+0x32a4:#x}')
  raw=(out/f'data-{i:03}.bin').read_bytes()
  def v(o,n=2):return int.from_bytes(raw[0x7ffe+o:0x7ffe+o+n],'big',signed=True)
  state=dict(sample=i,label=label,field=v(-31782,4),speed=v(-22360,4)/65536,gear=v(-26336),rpm=v(-26340),input=v(-23276),steer=v(-22356,4)/65536,lane=v(-22376,4)/65536,draw_lane=v(-22372,4)/65536,bank=v(-26186,4)/65536,pose=v(-26204,4)/65536,motion=v(-26200,4)/65536,neutral=v(-26182,4)/65536,snap=v(-29896),left=v(-29290),right=v(-29288),event=v(-22480))
  states.append(state);print(state,flush=True)
  g.cmd(f'monitor profile 1 "" "{out}/screen-{i:03}.bin"');(out/f'screen-{i:03}.png').write_bytes(barto.load(out/f'screen-{i:03}.bin').fields[-1].shot)
 g.cmd('monitor key 4c 1\nmonitor key 40 1\nmonitor fields 30\nmonitor key 40 0\nmonitor fields 130\nmonitor key 4c 0',timeout=120)
 capture(0,'straight')
 old=None
 for i in range(1,25):
  key=0x4e if i%2 else 0x4f
  if old is not None:g.cmd(f'monitor key {old:x} 0')
  g.cmd(f'monitor key {key:x} 1\nmonitor fields 6',timeout=60)
  capture(i,'right' if i%2 else 'left');old=key
 g.cmd(f'monitor key {old:x} 0')
 (out/'states.json').write_text(json.dumps(states,indent=2)+'\n')
 (out/'metadata.json').write_text(json.dumps(dict(car=car,c2=c2,data_base=db,h4=h,slave_sha256=sha(out/'slave.slave'),source={p.name:sha(p) for p in source.iterdir() if p.is_file()},scope='Guest fixture selects player mode and car; steering and throttle use native debugger keys; read-only telemetry'),indent=2)+'\n')
 print('CAPTURED '+name,flush=True)
finally:
 g.p.terminate();g.p.wait(timeout=5);pid=int((out/'.run/fsuae.pid').read_text());cmd=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True);assert str(out) in cmd and 'fs-uae' in cmd;os.kill(pid,15)
