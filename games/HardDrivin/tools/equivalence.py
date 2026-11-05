import os,sys,time,subprocess,json,hashlib,shutil
from pathlib import Path
from capture_demo import ROOT,SOCK,command,sha
os.chdir(ROOT)
kind=sys.argv[1];out=ROOT/'tmp/prof'/('equivalence-'+kind+'-fields-v4');out.mkdir(exist_ok=False);rel=out.relative_to(ROOT)
if SOCK.exists():
 try:command('quit')
 except (ConnectionError,FileNotFoundError):pass
slave=ROOT/('tmp/game/HardDrivin_v3.0_0126/HardDrivin/HardDrivin.Slave' if kind=='original' else 'tmp/build/HardDrivin.Slave')
shutil.copyfile(slave,out/'slave.slave')
env=dict(os.environ,FSUAE=shutil.which('fs-uae'),SLAVE=str(slave),JOY0='none',JOY1='none',DETERMINISTIC='1',WARP='1',WINDOW='none',WAIT_FOR_EXIT='0',BOOT_BREAK='0xd036f0',CPU='68000',AMIGA_MODEL='A500',CHIP_KB='512',FAST_KB='0',SLOW_KB='1536')
with (out/'server.log').open('w') as log:
 p=subprocess.Popen([sys.executable,str(ROOT/'tools/harddrivin.py'),'serve'],env=env,stdout=log,stderr=subprocess.STDOUT)
 try:
  while 'serving on' not in (out/'server.log').read_text():
   assert p.poll() is None;time.sleep(.5)
  print(command('gdb info registers pc a4'),flush=True)
  command(f'gdb dump binary memory {rel}/title-code.bin 0xcfb1d0 0xcfb210')
  sig=(out/'title-code.bin').read_bytes().hex()
  print(command(f'poke 0xd0eede 0040 {sig} 0xcfb1d0'),flush=True)
  print(command('gdb x/hx 0xd0eede'),flush=True)
  anchor=command('until 0xd0ba14');print(anchor,flush=True);assert '0x00d0ba14' in anchor,anchor
  command(f'gdb dump binary memory {rel}/slow-anchor.bin 0xc00000 0xd80000')
  command(f'gdb dump binary memory {rel}/chip-anchor.bin 0 0x80000')
  print('Sampling 1001 VBL states...',flush=True)
  script=f'''gdb break *0xcfb214
set $hd_f=0
while $hd_f <= 1000
continue
eval "dump binary memory {rel}/state-%04d.bin 0xd0f716 0xd16016", $hd_f
eval "dump binary memory {rel}/screen-%04d.bin 0x20000 0x2fd00", $hd_f
set $hd_f=$hd_f+1
end
delete
'''
  (out/'sampling.log').write_text(command(script))
  (out/'metadata.json').write_text(json.dumps(dict(slave_sha256=sha(slave),fields=1000,states=1001,game_base='0xcfb1d0',a4='0xd15f16',input='raw space 0x40 into native keyboard queue at title +8520'),indent=2))
  print('DONE '+kind,flush=True)
 finally:
  command('quit');p.wait(timeout=10)
