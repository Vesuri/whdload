#!/usr/bin/env python3
"""Read-only intro sample/IRQ event capture in an isolated emulator."""
import os,sys,subprocess,shutil,json
from harness import ROOT,sha
from check_inputs import check
from amigaxdev.gdbserve import Server
from private_run import private_server
from td_report import game_bytes,locate
name,setup,variant,dc=sys.argv[1:]
out=ROOT/'tmp/audio'/name;out.mkdir(parents=True);check()
slave=ROOT/('tmp/build/TestDrive-1.4-rebuilt.slave' if variant=='baseline' else 'tmp/build/release/TestDrive.Slave' if variant=='candidate' else 'tmp/dist/2.0b/TestDrive.slave')
shutil.copyfile(slave,out/'slave.slave')
s=private_server('tdaudioprobe',out)
env=dict(FSUAE=str(ROOT/'tmp/phase3/native-emulator/fs-uae'),TD_SETUP='',AMIGA_SETUP=setup,WARP='1',JOY0='none',WINDOW='back',SLAVE=str(out/'slave.slave'),WHD_ARGS=('CUSTOM2=1 ' if variant!='baseline' else '')+'CACHE',FSUAE_CLAIM_STRICT='1',EXTRA_ARGS='--fast_memory=8192 --uae_cpu_data_cache='+dc)
g=s.boot(env)
try:
 g.cmd('cd '+str(out));root=None
 g.cmd('monitor fields '+os.environ.get('AUDIO_BOOT_FIELDS','600'),timeout=60)
 for attempt in range(100):
  g.cmd('monitor fields 20',timeout=60)
  g.cmd('dump binary memory resolve.bin 0x200000 '+'0xa00000')
  data=(out/'resolve.bin').read_bytes();root=locate(data,game_bytes()[0x28:0x7c34],0x200000)
  if root is not None:break
 assert root is not None
 db=int.from_bytes(data[root-0x200000-4:root-0x200000],'big')*4+4;a4=db+0x7ffe
 print('resolved root',hex(root),'a4',hex(a4),'attempt',attempt,flush=True)
 specs=[(0x24c4,'PLAY','*(unsigned int*)($sp+4), *(unsigned int*)($sp+8), *(unsigned short*)($sp+12), *(unsigned short*)($sp+14)', '%x %u %u %u'),(0x2658,'IRQ','$d0, $d2, *(short*)($a0+20), *(unsigned int*)$a0','%x %x %d %x'),(0x26f8,'START','$d1, *(unsigned int*)$a0, *(unsigned short*)($a0+10), *(short*)($a0+18)','%x %x %u %d'),(0x2546,'STOP','*(unsigned short*)($sp+4)','%u'),(0x2436,'MASK','*(unsigned short*)($a5+8)','%x')]
 cmds=[]
 for off,label,expr,fmt in specs:
  if label=='IRQ':
   off=0x2660;expr='$d0, $d2, *(short*)($a0+20), *(unsigned int*)$a0'
  cmds += [f'break *{root+off:#x}']
  cmds += ['commands','silent',f'printf "{label} %u %08x {fmt}\\n", *(unsigned int*){a4-31548:#x}, *(unsigned int*)0xdff004, {expr}','continue','end']
 cmds += [f'break *{root+0x26b6:#x}', f'condition $bpnum *(unsigned int*){a4-31548:#x} >= {int(os.environ.get("AUDIO_FIELDS","1000"))}']
 (out/'breakpoints.txt').write_text(g.cmd('set logging file live.txt\nset logging enabled on\n'+'\n'.join(cmds)))
 print('capturing events',flush=True)
 log=g.cmd('continue',timeout=600);(out/'events.txt').write_text(log)
 print('events',log.count('\n'),log[-400:],flush=True)
 g.cmd(f'dump binary memory root.bin {root:#x} {root+0x7c0c:#x}');g.cmd(f'dump binary memory state.bin {db:#x} {db+0x32a4:#x}')
 (out/'metadata.json').write_text(json.dumps(dict(root=root,a4=a4,setup=setup,variant=variant,dc=dc,slave_sha256=sha(slave)),indent=2)+'\n')
finally:
 g.p.terminate();g.p.wait(timeout=5)
 pid=int((out/'.run/fsuae.pid').read_text());cmd=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True);assert str(out) in cmd and 'fs-uae' in cmd;os.kill(pid,15)
