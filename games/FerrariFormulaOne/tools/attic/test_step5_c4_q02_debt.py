from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a500';kind='debt';variant=os.environ.get('C1_VARIANT','candidate');name='c4-q02-'+kind+'-'+profile+'-'+variant;out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);b=r/'tmp/build/step5-c4-divide-frame-r3g-v1-ab-contact'/('000' if profile.startswith('a500') else '020')/(variant+'.slave');profiles=json.loads((r/'manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1 CUSTOM2=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'),KICKSTART=os.environ['KICKSTART_A1200'] if profile.startswith('a1200') else os.environ['KICKSTART'])
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
 for attempt in range(200):
  v=cmd('continue');assert 'Breakpoint' in v,v
  if val('*(unsigned int*)$a3')==0x22f30:
   race=val('$d0+*(unsigned int*)($a3+28)');break
 else:raise AssertionError('No race overlay entered')
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
 cmd('monitor warp 0')
 context=probe+sym(fine_listing,'C1Context');records=[]
 for index in range(50):
  if index:assert 'Breakpoint' in cmd('continue'),log[-1]
  assert val('$pc')==probe+sym(fine_listing,'C1Checkpoint')
  cmd(f'dump binary memory {out.relative_to(r)}/context.bin {context} {context+56}')
  values=struct.unpack('>14I',(out/'context.bin').read_bytes())
  pending=(values[1]<<32|values[2])-(values[3]<<32|values[4])
  counts=probe+sym(fine_listing,'C2Injections')
  cmd(f'dump binary memory {out.relative_to(r)}/counts.bin {counts} {counts+8}')
  injections,hits=struct.unpack('>2I',(out/'counts.bin').read_bytes())
  records.append(dict(injections=injections,wall_hits=hits,step=index+1,fields=values[0],elapsed_units=values[1]<<32|values[2],consumed_units=values[3]<<32|values[4],pending_units=pending,pending_intervals=pending/values[5],interval_units=values[5],interval_ms=values[7]))
  (out/'debt-records.json').write_text(json.dumps(records,indent=2)+'\n')
 report['contact']={n:val(f'*(unsigned int*){probe+sym(fine_listing,n)}') for n in ('C2Injections','C2WallHits','C1Completed','error')}
 report['peak_pending_intervals']=max(x['pending_intervals'] for x in records)
 report['recovery_steps']=next((x['step']-20 for x in records if x['step']>20 and x['pending_intervals']<1),None)
 assert all(x['pending_units']>=0 and x['interval_ms']==200 for x in records)
 assert report['contact']['C2WallHits']>0 and report['contact']['C2Injections']>=10 and report['contact']['error']==0,report
 report['injection_steps']=[x['step'] for i,x in enumerate(records) if x['injections']>(records[i-1]['injections'] if i else 0)]
 assert report['injection_steps']==list(range(11,21)),report
 assert report['recovery_steps'] is not None,report
 report['scope']='Untraced 50-update warp-off bounded forced-wall episode; full actual TimeField units minus consumed units, no debt rebasing or paused-time deletion. Observed recovery, not a universal bound.'
 report['status']='complete';(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)

finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
