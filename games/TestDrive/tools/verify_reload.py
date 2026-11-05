#!/usr/bin/env python3
"""Exercise an actual h4 unload/reload and verify every installed range again."""
import os,json,re,shutil,subprocess,sys,time,socket
from harness import ROOT,server,command,sha,live_regions,dump,listing
from race_capture import resolve
from check_disabled import check
from check_units import MARK
out=ROOT/'tmp/phase7/final-reload-confirmed'
if out.exists():raise RuntimeError('fresh output required')
s=socket.socket(socket.AF_UNIX);s.settimeout(.2)
try:s.connect(server.sock)
except (FileNotFoundError,ConnectionRefusedError):pass
else:raise RuntimeError('existing server; stop it first')
finally:s.close()
out.mkdir()
slave=ROOT/'tmp/build/verify/TestDrive.Slave';shutil.copyfile(slave,out/'slave.slave');shutil.copyfile(listing(slave),out/'slave.lst')
env=dict(os.environ,FSUAE=str(ROOT/'tmp/phase3/native-emulator/fs-uae'),TD_SETUP='a500',WARP='1',JOY0='none',SLAVE=str(out/'slave.slave'),WHD_ARGS='CUSTOM3=1',BOOT_BREAK='0x1e63e',BOOT_CONDITION='*(unsigned int*)0x1e548 == 0x4e55ffcc && *(unsigned short*)0x1e63e == 0x4eb9')
env.pop('AMIGA_SETUP',None)
f=(out/'serve.log').open('w');proc=subprocess.Popen([sys.executable,str(ROOT/'tools/td.py'),'serve'],env=env,stdout=f,stderr=subprocess.STDOUT)
end=time.monotonic()+300
while 'serving on' not in (out/'serve.log').read_text():
 if proc.poll() is not None:raise RuntimeError('server exited')
 if time.monotonic()>end:raise TimeoutError('inspect live boot')
 time.sleep(.5)
try:
 base,rr=resolve(out/'first');ram=(out/'first/code.bin').read_bytes()
 syms={n:int(a,16) for n,a in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)$',(out/'slave.lst').read_text(encoding='latin1'),re.M)}
 at=(ram.index(MARK)+len(MARK)+1)&~1;sb=base+at-syms['verify_unit_results']
 with (out/'actions.txt').open('w') as log:
  for label in ['overlay_unload_end','verify_race_entry']:
   cmd='until '+hex(sb+syms[label]);reply=server.request(cmd);log.write(label+'\n'+reply);log.flush();print(label,reply,flush=True)
   if label=='overlay_unload_end':
    stub=dump(out/'unloaded-stub.bin',rr['td-data']+668,rr['td-data']+676).read_bytes()
    assert stub[:2]==bytes.fromhex('6100'),('h4 was not unloaded',stub.hex())
 base,rr=live_regions(out)
 ram=(out/'code.bin').read_bytes();stub=rr['td-data']-base+668
 assert ram[stub:stub+2]==bytes.fromhex('4ef9')
 rr['h4']=int.from_bytes(ram[stub+2:stub+6],'big')
 assert (out/'chip.bin').read_bytes()[rr['h4']:rr['h4']+4]==bytes.fromhex('4e55ffcc')
 (out/'capture.json').write_text(json.dumps(dict(base=base,regions=rr,options=dict(C1=0,C2=0,C3=1,C4=0,C5=0),slave_sha256=sha(out/'slave.slave')),indent=2)+'\n')
 shutil.copyfile(ROOT/'tmp/run/default/.run/machine.json',out/'machine.json')
 (out/'options.json').write_text(json.dumps(check(out),indent=2)+'\n')
 print('PASS: unload followed by race re-entry; all optional patches installed correctly',flush=True)
finally:
 server.request('quit');proc.wait(timeout=20);f.close()
