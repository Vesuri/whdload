#!/usr/bin/env python3
"""Isolated native renderer sweep; guest VERIFY fixture changes draw snapshots only."""
import os,sys,json,re,shutil,subprocess,time,hashlib
from pathlib import Path
from harness import ROOT,sha
from check_inputs import check
from amigaxdev.gdbserve import Server
from private_run import private_server
from amigaxdev import barto
name=sys.argv[1];lane=int(sys.argv[2]);out=ROOT/'tmp/steer-reversal'/name
assert not out.exists();out.mkdir();check()
source=Path(os.environ.get('ROAD_SHIFT_SOURCE',str(ROOT/'src')));stage=out/'source';shutil.copytree(source,stage)
s=(stage/'render.s').read_text();a=s.index('    move.w d0,-22338(a4)',s.index('render_verify_fixture:'));s=s[:a]+s[a:].replace('    move.w d0,-22338(a4)','    move.w #32768,-22338(a4)\n    lea render_sweep_phase(pc),a0\n    add.w #128,(a0)',1)
s=s.replace('move.l #100*65536+16384,-22372(a4)',f'move.l #{lane}*65536,-22372(a4)')
s=s.replace('render_verify_fixture:\n','render_sweep_phase: dc.w -4224\nrender_verify_fixture:\n');(stage/'render.s').write_text(s)
# Pin only the draw-side near-curve seed, not its simulation source.
s += '\nrender_sweep_curve:\n    move.l d0,-(sp)\n    move.w render_sweep_phase(pc),d0\n    ext.l d0\n    move.l d0,-29840(a4)\n    move.l (sp)+,d0\n    rts\n'
(stage/'render.s').write_text(s)
p=stage/'render-patches.i';p.write_text(p.read_text()+'\n    PL_P $07eaa,render_sweep_curve\n')
args=[os.environ['VASM'],'-DVERIFY=1','-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym','-I'+os.environ['AMIGA_INCLUDE'],'-I'+os.environ['WHDLOAD']+'/Include','-I'+os.environ['WHDLOAD']+'/Src/sources','-I'+os.environ['AMIGA_SHARE']+'/ndk/Include_I','-L',str(out/'slave.lst'),'-o',str(out/'slave.slave'),'TestDriveHD.s']
subprocess.run(args,cwd=stage,check=True,stdout=(out/'build.log').open('w'))
server=private_server('roadshift',out)
env=dict(FSUAE=str(ROOT/'tmp/phase3/native-emulator/fs-uae'),TD_SETUP='',AMIGA_SETUP='a1200-040',WARP='1',JOY0='none',SLAVE=str(out/'slave.slave'),WHD_ARGS='CUSTOM2=1 CUSTOM3=1 CUSTOM1=1966080 CUSTOM5=32',FSUAE_CLAIM_STRICT='1')
# A unique work-directory-derived port and .run keep the user's game untouched.
g=server.boot(env);h=0x1e548
try:
 g.cmd(f'break *{h+0xf6:#x}\ncondition $bpnum *(unsigned int*){h:#x} == 0x4e55ffcc && *(unsigned short*){h+0xf6:#x} == 0x4eb9');g.cmd('continue',timeout=300);g.cmd('delete')
 a4=int(re.search(r'a4\s+(0x[0-9a-f]+)',g.cmd('info registers a4'))[1],16);db=a4-0x7ffe
 g.cmd('cd '+str(ROOT));rel=out.relative_to(ROOT)
 script=[f'break *{h+0x116a:#x}','set $rs_frame=0']
 for i in range(66):
  script+=['continue',f'dump binary memory {rel}/frame-{i:02}.bin {db:#x} {db+0x32a4:#x}']
 (out/'capture-gdb.txt').write_text(g.cmd('\n'.join(script),timeout=300));g.cmd('delete')
 # Retain a full native screenshot after the latest drawing is published.
 g.cmd('monitor fields 8');trace=out/'screen.bin';g.cmd(f'monitor profile 1 "" "{trace}"');(out/'screen.png').write_bytes(barto.load(trace).fields[-1].shot)
 (out/'metadata.json').write_text(json.dumps(dict(lane=lane,slave_sha256=sha(out/'slave.slave'),source={p.name:sha(p) for p in source.iterdir() if p.is_file()},data_base=db,h4=h,scope='Guest draw-only fixture; simulation unmodified; read-only debugger captures'),indent=2)+'\n')
 print('CAPTURED '+name,flush=True)
finally:
 g.p.terminate();g.p.wait(timeout=5)
 pid=int((out/'.run/fsuae.pid').read_text());cmd=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True);assert str(out) in cmd and 'fs-uae' in cmd
 os.kill(pid,15)
