from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a500';kind='modal-v2';variant=os.environ.get('C1_VARIANT','candidate');name='c4-q03-'+kind+'-'+profile+'-'+variant;out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);b=r/'tmp/build/step5-c4-divide-frame-r3g-v1-ab'/('000' if profile.startswith('a500') else '020')/(variant+'.slave');profiles=json.loads((r/'manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',JOY0='mouse',WHD_ARGS='CUSTOM1=1 CUSTOM2=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae-q03-release'),KICKSTART=os.environ['KICKSTART_A1200'] if profile.startswith('a1200') else os.environ['KICKSTART'])
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
    report.setdefault('key_reads',[]).append(dict(event=event,expected=code,actual=got,pc=hex(pc),raw_caller=hex(val('*(unsigned int*)($a6+4)')),translated_caller=hex(val('*(unsigned int*)(*(unsigned int*)$a6+4)'))))
    if got==code:found=True;break
   if attempt==3 and event=='KEY_SPACE':
    cmd('monitor input '+event+' 0')
    cmd('monitor input '+event+' 1')
  cmd('monitor input '+event+' 0')
  (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
  if not found:dump('input-delivery-failure')
  assert found,report
 def save():
  (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 def snapshot(label):
  m=dump(label);ctx=list(struct.unpack_from('>14I',m,probe+sym(fine_listing,'C1Context')))
  v={'context':ctx,'completed':struct.unpack_from('>I',m,probe+sym(fine_listing,'C1Completed'))[0],'owned':struct.unpack_from('>H',m,probe+sym(fine_listing,'C4BlitOwned'))[0],'calendar':m[native(0x226c0):native(0x226c0)+10].hex(),'session':m[native(0x226ca):native(0x226ca)+10].hex()}
  report[label]=v;save();return m,v
 def advance_fields(n,active=True):
  cmd('delete');cmd(f'break *{probe+sym(fine_listing,"C1Vbl") if active else native(0x2482a)}');cmd(f'ignore $bpnum {n-1}');assert 'Breakpoint' in cmd('continue')
 cmd('monitor warp 0')
 key('KEY_SPACE',0x40)
 until(probe+sym(fine_listing,'C1Checkpoint'))
 memory,take=snapshot('takeover')
 ledger_at=probe+sym(fine_listing,'C1Ledger');ledger_data,ledger_capacity,ledger_used=struct.unpack_from('>III',memory,ledger_at+8);assert 0<ledger_used<=ledger_capacity and ledger_used%6==0
 expected={}
 for offset in range(0,ledger_used,6):
  address,word=struct.unpack_from('>IH',memory,ledger_data+offset);expected.setdefault(address,word)
 report['ledger_entries']=len(expected);save()
 key('KEY_ESC',0x45)
 until(probe+sym(fine_listing,'C1Pause'))
 until(native(0x2546a))
 memory,paused=snapshot('pause-start');assert paused['context'][11]==1 and paused['owned']==0
 advance_fields(50)
 memory,held=snapshot('pause-held')
 assert held['completed']==paused['completed'] and held['calendar']==paused['calendar'] and held['session']==paused['session']
 assert held['context'][0]>paused['context'][0] and held['context'][3:11]==paused['context'][3:11] and held['context'][11:]==paused['context'][11:]
 key('KEY_ESC',0x45)
 until(probe+sym(fine_listing,'C1Resume'))
 until(native(0x654be))
 memory,resume=snapshot('resume-boundary');p=paused['context'];v=resume['context'];u=lambda x,i:(x[i]<<32)|x[i+1]
 duration=u(v,1)-u(p,12)
 assert u(v,3)==u(p,3)+duration and u(v,9)==u(p,9)+duration and v[8]==p[8]+1
 assert v[11:]==[0,0,0] and resume['owned']==64 and resume['completed']==paused['completed']
 assert resume['calendar']==paused['calendar'] and resume['session']==paused['session']
 report['pause_exact_debt_preserved']=True;report['excluded_pause_units']=duration;save()
 until(probe+sym(fine_listing,'C1Checkpoint'))
 memory,v=snapshot('resumed-update');assert v['completed']==resume['completed']+1
 report['phase']='pause-passed';save();print('Actual pause passed',flush=True)
 key('KEY_K',0x27)
 report['phase']='tow-key-delivered';save();cmd('monitor warp 1')
 until(probe+sym(fine_listing,'C1Exit'))
 until(native(0x65f48))
 memory,ex=snapshot('native-exit-restored')
 assert ex['owned']==0
 for address,word in expected.items():assert struct.unpack_from('>H',memory,address)[0]==word,hex(address)
 assert memory[ledger_at:ledger_at+24]==bytes(24)
 report['ledger_restored_words']=len(expected);report['phase']='actual-exit-passed';save();print('Actual exit restored',len(expected),flush=True)
 advance_fields(200,False)
 memory,menu=snapshot('after-exit')
 assert menu['context']==ex['context']
 cmd('delete');s.handle(g,'shot '+str(out/'after-exit.png'))
 report['phase']='after-exit-observed';report['error']=val(f'*(unsigned int*){probe+sym(fine_listing,"error")}');save();print(report,flush=True)

finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
