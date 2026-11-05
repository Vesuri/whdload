from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile='a1200-fast';out=r/'tmp/step5/a1200-fast-b7-v1-profile';out.mkdir(parents=True,exist_ok=True);b=r/'tmp/build/step5-b7-v1/lean/fine.slave';profiles=json.loads((r/'manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1 CUSTOM2=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'),KICKSTART=os.environ['KICKSTART_A1200'])
s=Server('ff1measure',root=str(r),profile_window=False);log=[]
try:
 g=s.boot()
 def cmd(c):
  v=g.cmd(c,timeout=180);log.append(c+'\n'+v);(out/'live.log').write_text('\n'.join(log));return v
 def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
 for boot_attempt in range(20):
  g.cont();time.sleep(1);g.stop()
  cmd('dump binary memory tmp/step5/a1200-fast-b7-v1-profile/memory.bin 0 0x600000')
  mem=(out/'memory.bin').read_bytes();u=lambda a:struct.unpack_from('>I',mem,a)[0]
  hits=[];at=0
  while True:
   at=mem.find(b'FF1B7PUBLICROOT',at)
   if at<0:break
   root=u(at-4)*4+4
   if 0<root<len(mem) and mem[root:root+2]==bytes.fromhex('6000'):hits.append((at,root))
   at+=1
  if hits:break
 assert len(hits)==1,hits
 marker,root=hits[0];table=u(root+16)*4;race=u(table+160*4)*4+4
 report=dict(root=hex(root),table=hex(table),race=hex(race),marker=hex(marker),pc=val('$pc'),slave_sha256=hashlib.sha256(b.read_bytes()).hexdigest())
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
 cmd('delete');cmd(f'break *{root+0x2e6}')
 for attempt in range(200):
  v=cmd('continue');assert 'Breakpoint' in v,v
  if val('*(unsigned int*)$a3')==0x22f30:
   race=val('$d0+*(unsigned int*)($a3+28)');break
 else:raise AssertionError('No race overlay entered')
 report['race']=hex(race);(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 from step5_b7_addresses import Addresses
 cmd('delete');cmd(f'break *{race+0xb9e}');cmd('ignore $bpnum 119');assert 'Breakpoint' in cmd('continue')
 cmd('monitor warp 0');cmd('ignore $bpnum 4');assert 'Breakpoint' in cmd('continue')
 cmd('delete');cmd(f'break *{race+0x70c}');assert 'Breakpoint' in cmd('continue')
 cmd('ignore $bpnum 6');assert 'Breakpoint' in cmd('continue')
 cmd('dump binary memory tmp/step5/a1200-fast-b7-v1-profile/start-raw.bin 0 0x600000')
 memory=(out/'start-raw.bin').read_bytes();addresses=Addresses(memory,table)
 (out/'start.bin').write_bytes(addresses.canonical_memory(memory));(out/'addresses.json').write_text(json.dumps(addresses.rows,indent=2)+'\n')
 cmd('delete');cmd(f'monitor profile 48 "" "{out}/detail.bin"')
 cmd('dump binary memory tmp/step5/a1200-fast-b7-v1-profile/end-raw.bin 0 0x600000')
 (out/'end.bin').write_bytes(addresses.canonical_memory((out/'end-raw.bin').read_bytes()))
 report['normalization']=addresses.normalize_trace(out/'detail.bin');report['slave']=str(b);report['status']='complete';report['start_loop']=132
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print('B7 profile capture complete',flush=True)
finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
