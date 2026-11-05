"""Two-window replay evidence from a frozen VERIFY_DRIVE tape (fixed A500)."""
import sys,os,json,struct,subprocess,time,shutil,re,hashlib
from pathlib import Path
from capture_demo import ROOT,SOCK,command,sha
os.chdir(ROOT);name=sys.argv[1];end=int(sys.argv[2]);out=ROOT/'tmp/prof'/name;out.mkdir(exist_ok=False);rel=out.relative_to(ROOT)
if SOCK.exists():
 try:command('quit')
 except (ConnectionError,FileNotFoundError):pass
slave=ROOT/'tmp/build/HardDrivin-slow.slave';shutil.copyfile(slave,out/'slave.slave')
env=dict(os.environ,WHD_ARGS='CUSTOM4='+os.environ.get('DELAY_FIELDS','0'),FSUAE=shutil.which('fs-uae'),SLAVE=str(slave),JOY0='none',JOY1='none',DETERMINISTIC='1',WARP='1',WINDOW='none',WAIT_FOR_EXIT='0',BOOT_BREAK='0xd0c0a4',CPU='68000',AMIGA_MODEL='A500',CHIP_KB='512',FAST_KB='0',SLOW_KB='1536')
with (out/'server.log').open('w') as log:
 p=subprocess.Popen([sys.executable,str(ROOT/'tools/harddrivin.py'),'serve'],env=env,stdout=log,stderr=subprocess.STDOUT)
 try:
  while 'serving on' not in (out/'server.log').read_text():
   assert p.poll() is None;time.sleep(.3)
  regs=command('gdb info registers pc a4');assert '0xd0c0a4' in regs and '0xd15f16' in regs
  command(f'gdb dump binary memory {rel}/anchor-slow.bin 0xc00000 0xd80000')
  command(f'gdb dump binary memory {rel}/anchor-chip.bin 0 0x80000')
  b=(out/'anchor-slow.bin').read_bytes();lst=(ROOT/'tmp/build/slow.lst').read_text(encoding='latin1')
  syms={k:int(re.search(r'^'+k+r'\s+00:([0-9A-Fa-f]+)',lst,re.M).group(1),16) for k in ['_code_start','_verify_drive_state']}
  match=[i for i in range(0,len(b)-8,2) if b[i:i+8]==bytes.fromhex('00cfb1d000011a4e')];assert len(match)==1
  state=0xc00000+match[0]-syms['_code_start']+syms['_verify_drive_state'];assert struct.unpack_from('>H',b,state-0xc00000)[0]==2
  print('Capturing fields through',end,'state',hex(state),flush=True)
  script=f'''gdb break *0xcfb5c2
break *0xcfb284
break *0xd07f7e
break *0xd0bd86
set $hd_f=0
while $hd_f < {end}
continue
if $pc == 0xcfb5c2
set $hd_f=*(unsigned long*){state+4:#x}
eval "dump binary memory {rel}/state-%05d.bin 0xd0ee16 0xd16016", $hd_f
eval "dump binary memory {rel}/tape-%05d.bin {state:#x} {state+20:#x}", $hd_f
set $hd_front=*(unsigned long*)0xd0f508
eval "dump binary memory {rel}/front-%05d.bin %u %u", $hd_f, $hd_front, $hd_front+32000
else
printf "EVENT %x %u\\n", $pc-0xcfb1d0, *(unsigned long*){state+4:#x}
end
end
delete
'''
  # VBL +3f2; swap +b4; physics exit +cdae; replay iteration +10bb6.
  (out/'capture.log').write_text(command(script))
  meta=dict(custom4=int(os.environ.get('DELAY_FIELDS','0')),fields=end,code='0xcfb1d0',a4='0xd15f16',fixture_state=hex(state),slave_sha256=sha(slave),emulator_sha256=sha(env['FSUAE']),configuration={k:env[k] for k in ['CPU','AMIGA_MODEL','CHIP_KB','SLOW_KB','FAST_KB','JOY0','JOY1','DETERMINISTIC']})
  (out/'capture.json').write_text(json.dumps(meta,indent=2)+'\n');print('DONE',name,flush=True)
 finally:
  command('quit');p.wait(timeout=10)
