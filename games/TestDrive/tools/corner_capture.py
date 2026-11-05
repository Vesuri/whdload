#!/usr/bin/env python3
"""Isolated native renderer sweep; guest VERIFY fixture changes draw snapshots only."""
import os,sys,json,re,shutil,subprocess,time,hashlib
from pathlib import Path
from harness import ROOT,sha
from check_inputs import check
from amigaxdev.gdbserve import Server
from private_run import private_server
from amigaxdev import barto
bank=int(os.environ.get('CORNER_BANK','0'));name=sys.argv[1];lane=int(sys.argv[2]);segment=int(sys.argv[3]);out=ROOT/'tmp/corner-jump'/name
assert not out.exists();out.mkdir(parents=True);check()
source=Path(os.environ.get('ROAD_SHIFT_SOURCE',str(ROOT/'src')));stage=out/'source';shutil.copytree(source,stage)
phases=sorted(set(range(0,65536,1024))|set(range(64872,64900))|{65534,65535})
s=(stage/'render.s').read_text();a=s.index('    move.w d0,-22338(a4)',s.index('render_verify_fixture:'))
s=s[:a]+s[a:].replace('    move.w d0,-22338(a4)','    lea corner_phase_index(pc),a0\n    move.w (a0),d0\n    addq.w #2,(a0)\n    cmp.w #'+str(len(phases)*2)+',(a0)\n    bcs.b .phase_ok\n    clr.w (a0)\n.phase_ok\n    lea corner_phases(pc),a0\n    move.w (a0,d0.w),-22338(a4)',1)
s=s.replace('move.l #100*65536+16384,-22372(a4)',f'move.l #{lane}*65536,-22372(a4)')
s=s.replace('render_verify_fixture:\n','corner_phase_index: dc.w 0\ncorner_phases: dc.w '+','.join(map(str,phases))+'\nrender_verify_fixture:\n')
if 'render_curve_pose:' in s:
 s=s.replace('move.l -26186(a4),(a0)',f'move.l #{bank}*65536,(a0)')
else:
 s += f'\nrender_sweep_curve:\n    move.l #{bank}*65536,-29840(a4)\n    rts\n'
 p=stage/'render-patches.i';p.write_text(p.read_text()+'\n    PL_P $07eaa,render_sweep_curve\n')
a=s.index('render_row:');z=s.index('render_lane_seed:',a)
r=s[a:z].replace('.original\n    move.w -29844(a4),d0',""".original
    movem.l d0/a0,-(sp)
    move.w -29832(a4),d0
    lsl.w #4,d0
    lea corner_rows(pc),a0
    adda.w d0,a0
    move.l -29844(a4),(a0)+
    move.l -29848(a4),(a0)+
    move.l -29840(a4),(a0)+
    move.w -29852(a4),(a0)+
    move.w -29832(a4),(a0)
    movem.l (sp)+,d0/a0
    move.w -29844(a4),d0""")
s=s[:a]+r+s[z:]+ '\ncorner_rows: dcb.b 640,0\n';(stage/'render.s').write_text(s)
args=[os.environ['VASM'],'-DVERIFY=1','-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym','-I'+os.environ['AMIGA_INCLUDE'],'-I'+os.environ['WHDLOAD']+'/Include','-I'+os.environ['WHDLOAD']+'/Src/sources','-I'+os.environ['AMIGA_SHARE']+'/ndk/Include_I','-L',str(out/'slave.lst'),'-o',str(out/'slave.slave'),'TestDriveHD.s']
subprocess.run(args,cwd=stage,check=True,stdout=(out/'build.log').open('w'))
server=private_server('roadshift',out)
env=dict(FSUAE=str(ROOT/'tmp/phase3/native-emulator/fs-uae'),TD_SETUP='',AMIGA_SETUP='a1200-040',WARP='1',JOY0='none',SLAVE=str(out/'slave.slave'),WHD_ARGS=f'CUSTOM2=1 CUSTOM3=1 CUSTOM1={segment<<16} CUSTOM5=32 CACHE',FSUAE_CLAIM_STRICT='1')
# A unique work-directory-derived port and .run keep the user's game untouched.
g=server.boot(env);h=0x1e548
try:
 g.cmd(f'break *{h+0xf6:#x}\ncondition $bpnum *(unsigned int*){h:#x} == 0x4e55ffcc && *(unsigned short*){h+0xf6:#x} == 0x4eb9');g.cmd('continue',timeout=300);g.cmd('delete')
 a4=int(re.search(r'a4\s+(0x[0-9a-f]+)',g.cmd('info registers a4'))[1],16);db=a4-0x7ffe
 g.cmd('cd '+str(ROOT));rel=out.relative_to(ROOT)
 syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)$',(out/'slave.lst').read_text(encoding='latin1'),re.M)}
 script=[f'set $cs_rows=*(unsigned int*){h+0x1a3a:#x}-{syms["render_row"]}+{syms["corner_rows"]}',f'break *{h+0x116a:#x}']
 for i in range(len(phases)+2):
  script+=['continue',f'dump binary memory {rel}/frame-{i:02}.bin {db:#x} {db+0x32a4:#x}',f'dump binary memory {rel}/rows-{i:02}.bin $cs_rows $cs_rows+640']
 (out/'capture-gdb.txt').write_text(g.cmd('\n'.join(script),timeout=300));g.cmd('delete')
 # Retain a full native screenshot after the latest drawing is published.
 g.cmd('monitor fields 8');trace=out/'screen.bin';g.cmd(f'monitor profile 1 "" "{trace}"');(out/'screen.png').write_bytes(barto.load(trace).fields[-1].shot)
 (out/'metadata.json').write_text(json.dumps(dict(lane=lane,bank=bank,phases=phases,segment=segment,slave_sha256=sha(out/'slave.slave'),source={p.name:sha(p) for p in source.iterdir() if p.is_file()},data_base=db,h4=h,scope='Guest draw-only fixture; simulation unmodified; read-only debugger captures'),indent=2)+'\n')
 print('CAPTURED '+name,flush=True)
finally:
 g.p.terminate();g.p.wait(timeout=5)
 pid=int((out/'.run/fsuae.pid').read_text());cmd=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True);assert str(out) in cmd and 'fs-uae' in cmd
 os.kill(pid,15)
