#!/usr/bin/env python3
"""Observe the actual helper call/return and native Control-C game exit."""
import os,re,json,sys,shutil,subprocess,time,socket
from pathlib import Path
from harness import ROOT,server,command,snapshot,sha,dump
from check_units import MARK
import native_input as n
out=ROOT/'tmp/phase9'/sys.argv[1];assert not out.exists();out.mkdir()
reference=ROOT/'tmp/phase9/candidate-a1200-on';meta=json.loads((reference/'capture.json').read_text())
raw=(reference/'code.bin').read_bytes();syms={k:int(a,16) for k,a in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)$',(reference/'slave.lst').read_text(encoding='latin1'),re.M)}
at=raw.index(MARK)+len(MARK);at=(at+1)&~1;slavebase=meta['base']+at-syms['verify_unit_results']
source=ROOT/'tmp/build/verify/TestDrive.Slave';assert sha(source)==sha(reference/'slave.slave'),'recalibrate after build change'
for p in ['slave.slave','slave.lst']:shutil.copyfile(reference/p,out/p)
entry=slavebase+syms['render_interrupt_option'];restore=slavebase+syms['render_interrupt_restore']
env=dict(os.environ,FSUAE=str(ROOT/'tmp/phase3/native-emulator/fs-uae'),TD_SETUP='a1200',WARP='1',JOY0='none',SLAVE=str(out/'slave.slave'),WHD_ARGS='CUSTOM2=1 CUSTOM3=1',BOOT_BREAK=hex(entry),BOOT_CONDITION=f'*(unsigned short*){entry:#x} == 0x48e7');env.pop('AMIGA_SETUP',None)
s=socket.socket(socket.AF_UNIX);s.settimeout(.2)
try:s.connect(server.sock)
except (FileNotFoundError,ConnectionRefusedError):pass
else:raise RuntimeError('existing server')
finally:s.close()
f=(out/'serve.log').open('w');proc=subprocess.Popen([sys.executable,str(ROOT/'tools/td.py'),'serve'],env=env,stdout=f,stderr=subprocess.STDOUT);n.LOG=out/'native-actions.jsonl'
def registers():
 text=command('info registers');return {k:int(v,16) for k,v in re.findall(r'^(d[0-7]|a[0-6]|sp|pc)\s+(0x[0-9a-f]+)',text,re.M)}
def hardware():
 text=command('x/1hx 0xdff002\nx/1hx 0xdff01c');return [int(v,16) for v in re.findall(r':\s+(0x[0-9a-f]+)',text)]
def call_return(label):
 before=registers();hw=hardware();ret=int.from_bytes(dump(out/(label+'-return.bin'),before['sp'],before['sp']+4).read_bytes(),'big')
 (out/(label+'-until.txt')).write_text(server.request('until '+hex(ret)));after=registers();hw_after=hardware()
 assert all(after[k]==v for k,v in before.items() if k not in ('sp','pc'))
 assert after['sp']==before['sp']+4 and after['pc']==ret
 return {'before':before,'after':after,'hardware_before':hw,'hardware_after':hw_after}
ready=False
try:
 until=time.monotonic()+300
 while 'serving on' not in (out/'serve.log').read_text():
  if proc.poll() is not None:raise RuntimeError('server exited')
  if time.monotonic()>until:raise TimeoutError('inspect existing live boot')
  time.sleep(.5)
 ready=True;assert registers()['pc']==entry
 enable=call_return('enable');assert enable['hardware_after'][0]&0x400 and not enable['hardware_after'][1]&0x40
 (out/'enable.json').write_text(json.dumps(enable,indent=2)+'\n');print('ENABLE registers and hardware: PASS',flush=True)
 (out/'race.txt').write_text(server.request('until '+hex(meta['regions']['h4']+0xfc)))
 # Control-C is original DOS break handling (root:$7418 tests signal bit 12).
 n.key(0x63,True);n.key(0x33,True)
 poll=meta['regions']['td']+0x544e
 reply=command(f'break *{restore:#x}\nbreak *{poll:#x}\nset $probe_n=0\nwhile $pc != {restore:#x} && $probe_n < 100\ncontinue\nset $probe_n=$probe_n+1\nend\ninfo registers pc\ndelete')
 (out/'exit-polls.txt').write_text(reply)
 n.key(0x33,False);n.key(0x63,False)
 if registers()['pc']!=restore:
  print('Original quit flag not reached within 100 polls',flush=True)
  server.request('quit');proc.wait(timeout=20)
  raise RuntimeError('bounded native exit probe did not reach restore')
 restored=call_return('restore')
 assert (restored['hardware_after'][0]&0x400)==(enable['hardware_before'][0]&0x400)
 assert (restored['hardware_after'][1]&0x40)==(enable['hardware_before'][1]&0x40)
 (out/'restore.json').write_text(json.dumps(restored,indent=2)+'\n')
 (out/'result.json').write_text(json.dumps({'status':'PASS','entry_registers_preserved':True,'return_registers_preserved':True,'priority_restored':True,'interrupt_restored':True,'exit':'native Control-C original game return'},indent=2)+'\n')
 print('RESTORE registers and original enable bits: PASS',flush=True)
 n.fields(200);print(server.request('shot '+str(out/'quit.png')),flush=True)
 server.request('quit');proc.wait(timeout=20)
finally:
 f.close()
