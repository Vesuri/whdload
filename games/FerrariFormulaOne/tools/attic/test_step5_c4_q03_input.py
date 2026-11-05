from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a500';kind='input-retry';variant=os.environ.get('C1_VARIANT','candidate');name='c4-q03-'+kind+'-'+profile+'-'+variant;out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);b=r/'tmp/build/step5-c4-divide-frame-r3g-v1-ab'/('000' if profile.startswith('a500') else '020')/(variant+'.slave');profiles=json.loads((r/'manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',JOY0='mouse',WHD_ARGS='CUSTOM1=1 CUSTOM2=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae-q03-input'),KICKSTART=os.environ['KICKSTART_A1200'] if profile.startswith('a1200') else os.environ['KICKSTART'])
s=Server('ff1measure',root=str(r),profile_window=False);log=[]
try:
 g=s.boot()
 def cmd(c):
  v=g.cmd(c,timeout=180);log.append(c+'\n'+v);(out/'live.log').write_text('\n'.join(log));return v
 def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
 def dump(label):
  limit=0x80000 if profile.startswith('a500') else 0x200000 if profile=='a1200' else 0x600000
  cmd(f'dump binary memory {out.relative_to(r)}/{label}.bin 0 {limit}')
  mem=(out/(label+'.bin')).read_bytes()
  if profile=='a500-fast':
   cmd(f'dump binary memory {out.relative_to(r)}/{label}-fast.bin 0x200000 0x400000')
   mem+=bytes(0x200000-len(mem))+(out/(label+'-fast.bin')).read_bytes()
  if profile.startswith('a500'):
   cmd(f'dump binary memory {out.relative_to(r)}/{label}-slow.bin 0xc00000 0xd80000')
   mem+=bytes(0xc00000-len(mem))+(out/(label+'-slow.bin')).read_bytes()
  return mem
 for boot_attempt in range(20):
  g.cont();time.sleep(1);g.stop()
  mem=dump('memory');u=lambda a:struct.unpack_from('>I',mem,a)[0]
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
 cmd('condition $bpnum *(unsigned int*)$a3 == 0x22f30')
 assert 'Breakpoint' in cmd('continue')
 race=val('$d0+*(unsigned int*)($a3+28)')
 report['race']=hex(race);(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')

 import re
 host_listing=(r/'tmp/build/step5-b7-loader-v3/build.list').read_text(errors='replace');fine_listing=(b.parent/'fine.list').read_text()
 def sym(text,n):return int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)',text,re.M)[1],16)
 probe=marker-sym(host_listing,'FF1PublicMarker')+len((r/'tmp/build/step5-b7-loader-v3/FerrariFormulaOne.slave').read_bytes()[32:-4])
 report['probe']=hex(probe)
 cmd('delete')
 for failure in ('C1Fault','velocity_stop'):
  cmd(f'break *{probe+sym(fine_listing,failure)}')
 cmd(f'break *{probe+sym(fine_listing,"C1Checkpoint")}');assert 'Breakpoint' in cmd('continue'),log[-1]
 if val('$pc')!=probe+sym(fine_listing,'C1Checkpoint'):
  report['error']=val(f'*(unsigned int*){probe+sym(fine_listing,"error")}')
  report['registers']=cmd('info registers')
  dump('fault')
  (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
  raise AssertionError(report)
 from step5_b7_addresses import Addresses
 memory=dump('input-start');addresses=Addresses(memory,table)
 def native(addr):return addresses.map(addr)
 def until(address,condition=None):
  cmd('delete');cmd(f'break *{address}')
  if condition:cmd('condition $bpnum '+condition)
  assert 'Breakpoint' in cmd('continue'),log[-1]
  assert val('$pc')==address
 def key(event,code):
  target=native(0x23708)
  cmd('delete');cmd(f'break *{target}')
  irq=probe-len((r/'tmp/build/step5-b7-loader-v3/FerrariFormulaOne.slave').read_bytes()[32:-4])+sym(host_listing,'keyboard_start')
  cmd(f'break *{irq}')
  cmd(f'break *{native(0x236b2)}')
  report.setdefault('input_commands',[]).append(cmd('monitor input '+event+' 1'))
  found=False
  for attempt in range(16):
   assert 'Breakpoint' in cmd('continue'),log[-1]
   pc=val('$pc')
   if pc in (irq,native(0x236b2)):
    report.setdefault('input_path',[]).append(dict(pc=hex(pc),d0=val('$d0')))
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
   if pc==target:
    got=val('$d0')&255
    report.setdefault('key_reads',[]).append(dict(event=event,expected=code,actual=got,pc=hex(pc)))
    if got==code:found=True;break
   if attempt==3:
    cmd('monitor input '+event+' 0')
    cmd('monitor input '+event+' 1')
  cmd('monitor input '+event+' 0')
  (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
  if not found:dump('input-delivery-failure')
  assert found,report
 cmd('monitor warp 0')
 key('KEY_SPACE',0x40)
 until(probe+sym(fine_listing,'C1Checkpoint'))
 memory=dump('after-takeover');(out/'after-takeover-canonical.bin').write_bytes(addresses.canonical_memory(memory))
 key('KEY_ESC',0x45)
 until(probe+sym(fine_listing,'C1Pause'))
 report['pause_entered']=True
 cmd('delete');g.cont();time.sleep(1);g.stop()
 memory=dump('paused');report['paused_context']=list(struct.unpack_from('>14I',memory,probe+sym(fine_listing,'C1Context')))
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 key('KEY_ESC',0x45)
 until(probe+sym(fine_listing,'C1Resume'))
 until(probe+sym(fine_listing,'C1Checkpoint'))
 memory=dump('resumed');report['resumed_context']=list(struct.unpack_from('>14I',memory,probe+sym(fine_listing,'C1Context')))
 report['error']=val(f'*(unsigned int*){probe+sym(fine_listing,"error")}')
 report['status']='complete';(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)

finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
