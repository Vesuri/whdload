"""Owned debugger boot and dynamic layout calibration; local VERIFY work only."""
import os,sys,time,subprocess,shutil,json,struct
from pathlib import Path
from capture_demo import ROOT,SOCK,command
os.chdir(ROOT);name=sys.argv[1];out=ROOT/'tmp/prof'/name;out.mkdir(exist_ok=False)
if SOCK.exists():
 try:command('quit')
 except (ConnectionError,FileNotFoundError):pass
env=dict(os.environ,FSUAE=shutil.which('fs-uae'),SLAVE=str(ROOT/'tmp/build/HardDrivin-drive.slave'),JOY0='none',JOY1='none',DETERMINISTIC='1',WARP='1',WINDOW='none',WAIT_FOR_EXIT='0',CPU='68000',AMIGA_MODEL='A500',CHIP_KB='512',FAST_KB='0',SLOW_KB='1536')
env.pop('BOOT_BREAK',None)
if len(sys.argv)>2:env['BOOT_BREAK']=sys.argv[2]
log=(out/'server.log').open('w');p=subprocess.Popen([sys.executable,str(ROOT/'tools/harddrivin.py'),'serve'],env=env,stdout=log,stderr=subprocess.STDOUT)
while 'serving on' not in (out/'server.log').read_text():
 assert p.poll() is None;time.sleep(.2)
if not env.get('BOOT_BREAK'):time.sleep(8)
print(command('stop'),flush=True)
print(command('gdb info registers a4'),flush=True)
command(f'gdb dump binary memory tmp/prof/{name}/slow.bin 0xc00000 0xd80000')
b=(out/'slow.bin').read_bytes();hits=[]
for i in range(0,len(b)-8,2):
 if b[i+4:i+8]==bytes.fromhex('00011a4e'):
  ptr=struct.unpack_from('>I',b,i)[0]
  if 0xc00000<=ptr<0xd80000 and b[ptr-0xc00000:ptr-0xc00000+2]==b'\x4e\xf9':hits.append((i+0xc00000,ptr))
print('LAYOUT',hits,flush=True)
import re
lst=(ROOT/'tmp/build/drive.lst').read_text(encoding='latin1')
off=int(re.search(r'^_verify_drive_state\s+00:([0-9A-Fa-f]+)',lst,re.M).group(1),16)
co=int(re.search(r'^_code_start\s+00:([0-9A-Fa-f]+)',lst,re.M).group(1),16)
layout=dict(code=hits[0][1],state=hits[0][0]-co+off,a4=0xd15f16)
(out/'layout.json').write_text(json.dumps(layout));print(layout,flush=True)
print('Session remains stopped and available.',flush=True)
p.wait()
