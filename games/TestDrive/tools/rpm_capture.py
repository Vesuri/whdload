#!/usr/bin/env python3
"""Guest input-tape over-rev reproduction in a separate emulator session."""
import os,sys,json,re,shutil,subprocess
from pathlib import Path
from harness import ROOT,sha
from check_inputs import check
from amigaxdev.gdbserve import Server
from private_run import private_server
from amigaxdev import barto
name=sys.argv[1];car=int(sys.argv[2]);c2=int(sys.argv[3]);out=ROOT/'tmp/rpm-needle'/name
out.mkdir();check()
source=ROOT/'src';stage=out/'source';shutil.copytree(source,stage)
p=stage/'simulation-verify.s';s=p.read_text();a=s.index('verify_tape:\n');b=s.index('verify_tape_straight:',a)
s=s[:a]+'''verify_tape:
    move.l d0,-(sp)
    move.w #$100,d0
    moveq #0,d1
    cmp.l #30,(sp)
    bcc.b .done
    moveq #1,d1
.done
    addq.l #4,sp
    rts
'''+s[b:];p.write_text(s)
if os.environ.get('RPM_NEUTRAL'):
 s=p.read_text().replace('    moveq #1,d1\n.done\n    addq.l #4,sp','    moveq #0,d1\n.done\n    addq.l #4,sp');p.write_text(s)
if os.environ.get('RPM_WAIT'):
 p=stage/'simulation-patches.i';p.write_text(p.read_text()+'\n    PL_PS $02aee,rpm_wait_draw\n')
 p=stage/'simulation.s';p.write_text(p.read_text()+"""
rpm_wait_draw:
    movem.l d0-d1/a0-a1/a6,-(sp)
    move.l -31786(a4),a6
    jsr -228(a6)
    movem.l (sp)+,d0-d1/a0-a1/a6
    tst.w -2(a5)
    bne.b .done
    add.l #$76,(sp)
.done
    rts
""")
args=[os.environ['VASM'],'-DVERIFY=1','-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym','-I'+os.environ['AMIGA_INCLUDE'],'-I'+os.environ['WHDLOAD']+'/Include','-I'+os.environ['WHDLOAD']+'/Src/sources','-I'+os.environ['AMIGA_SHARE']+'/ndk/Include_I','-L',str(out/'slave.lst'),'-o',str(out/'slave.slave'),'TestDriveHD.s']
subprocess.run(args,cwd=stage,check=True,stdout=(out/'build.log').open('w'))
srv=private_server('rpmneedle',out)
env=dict(FSUAE=str(ROOT/'tmp/phase3/native-emulator/fs-uae'),TD_SETUP='',AMIGA_SETUP='a1200-040',WARP='1',JOY0='none',SLAVE=str(out/'slave.slave'),WHD_ARGS=f'CUSTOM2={c2} CUSTOM3=1 CUSTOM5={1+car*256}',FSUAE_CLAIM_STRICT='1')
g=srv.boot(env);h=0x1e548
try:
 g.cmd(f'break *{h+0xf6:#x}\ncondition $bpnum *(unsigned int*){h:#x} == 0x4e55ffcc && *(unsigned short*){h+0xf6:#x} == 0x4eb9');g.cmd('continue',timeout=300);g.cmd('delete')
 a4=int(re.search(r'a4\s+(0x[0-9a-f]+)',g.cmd('info registers a4'))[1],16);db=a4-0x7ffe
 g.cmd('cd '+str(ROOT));rel=out.relative_to(ROOT);states=[]
 syms={n:int(a,16) for n,a in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)$',(out/'slave.lst').read_text(encoding='latin1'),re.M)}
 limit_addr=None
 if 'instrument_car' in syms:
  g.cmd(f'dump binary memory {rel}/instrument-hook.bin {h+0x82a2:#x} {h+0x82a8:#x}')
  target=int.from_bytes((out/'instrument-hook.bin').read_bytes()[2:6],'big');limit_addr=target-syms['instrument_car']+syms['instrument_limit']
  g.cmd(f'dump binary memory {rel}/display-limit.bin {limit_addr:#x} {limit_addr+2:#x}')
  print('DISPLAY LIMIT',int.from_bytes((out/'display-limit.bin').read_bytes(),'big'),flush=True)
 for i in range(151):
  g.cmd(f'dump binary memory {rel}/data-{i:03}.bin {db:#x} {db+0x32a4:#x}')
  raw=(out/f'data-{i:03}.bin').read_bytes()
  def v(o,n=2):return int.from_bytes(raw[0x7ffe+o:0x7ffe+o+n],'big',signed=True)
  s=dict(sample=i,field=v(-31782,4),car=v(-22500),rpm=v(-26340),gear=v(-26336),event=v(-22480),speed=v(-22360,4)/65536,rev_count=v(-27130),maximum=v(-26328),redline=v(-26326));states.append(s)
  if i%10==0 or s['rpm']>=7500:
   print(s,flush=True);g.cmd(f'monitor profile 1 "" "{out}/screen-{i:03}.bin"');(out/f'screen-{i:03}.png').write_bytes(barto.load(out/f'screen-{i:03}.bin').fields[-1].shot)
  if s['event']:break
  g.cmd('monitor fields 5',timeout=60)
 (out/'states.json').write_text(json.dumps(states,indent=2)+'\n')
 (out/'metadata.json').write_text(json.dumps(dict(car=car,c2=c2,data_base=db,h4=h,slave_sha256=sha(out/'slave.slave'),source={p.name:sha(p) for p in source.iterdir() if p.is_file()},scope='Guest tape engages first gear then holds throttle; no host game memory writes'),indent=2)+'\n')
 print('CAPTURED '+name,flush=True)
finally:
 g.p.terminate();g.p.wait(timeout=5);pid=int((out/'.run/fsuae.pid').read_text());cmd=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True);assert str(out) in cmd and 'fs-uae' in cmd;os.kill(pid,15)
