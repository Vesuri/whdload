from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a1200-fast';variant=os.environ.get('C1_VARIANT','candidate');name='c4-sine-r3d-v1-heavy-v2-'+profile+'-'+variant+'-heavy'+('-fps'+os.environ['C4_HEAVY_FRAMES'] if 'C4_HEAVY_FRAMES' in os.environ else '');out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);b=r/'tmp/build/step5-c4-sine-r3d-v1-heavy-v2'/('000' if profile.startswith('a500') else '020')/(variant+'.slave');profiles=json.loads((r/'manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1 CUSTOM2=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'),KICKSTART=os.environ['KICKSTART_A1200'] if profile.startswith('a1200') else os.environ['KICKSTART'])
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

 from step5_b7_addresses import Addresses

 from step5_b7_addresses import Addresses
 def scalar(name):return val(f'*(unsigned int*){probe+sym(fine_listing,name)}')
 def state():
  return {n:scalar(n) for n in ('HeavyFrames','HeavyIncomplete','HeavyCarCount','HeavyCarMask','C1Completed','C1Skipped','error')}|{'fields':scalar('C1Context')}
 def stop_at(label):
  cmd('delete')
  for n in (label,'C1Fault','velocity_stop'):cmd(f'break *{probe+sym(fine_listing,n)}')
  reply=cmd('continue');assert 'breakpoint' in reply.lower(),reply
  assert val('$pc')==probe+sym(fine_listing,label),(label,state(),cmd('info registers'))
 stop_at('HeavyRestored')
 cmd('monitor warp 0')
 memory=dump('restored-raw');addresses=Addresses(memory,table)
 canonical=addresses.canonical_memory(memory);(out/'restored.bin').write_bytes(canonical)
 blocks=[(0x6a60a,16),(0x6a61a,16),(0x6a62a,16),(0x6a66a,16),(0x6a67a,16),(0x2268e,16),(0x1c6a2,2),(0x66f96,2),(0x66c7c,2)]
 actual=b''.join(canonical[a:a+n] for a,n in blocks)
 saved_at=probe+sym(fine_listing,'HeavySaved')
 assert actual==memory[saved_at:saved_at+102],'render pose restoration mismatch'
 report['restoration_exact']=True
 stop_at('HeavyStartDone')
 memory=dump('fixed-raw');canonical=addresses.canonical_memory(memory)
 (out/'fixed.bin').write_bytes(canonical)
 report['fixed_scene_hex']=b''.join(canonical[a:a+n] for a,n in blocks).hex()
 stop_at('HeavyRestored')
 report['start']=state();report['warp_start']=cmd('monitor warp-status')
 frames=int(os.environ.get('C4_HEAVY_FRAMES','10'))
 cmd('delete');cmd(f'break *{probe+sym(fine_listing,"HeavyRestored")}')
 cmd(f'ignore $bpnum {frames-1}')
 assert 'breakpoint' in cmd('continue').lower()
 report['end']=state();report['warp_end']=cmd('monitor warp-status')
 count=report['end']['HeavyFrames']-report['start']['HeavyFrames']
 elapsed=(report['end']['fields']-report['start']['fields'])*71051/3546895
 report.update(presentations=count,elapsed_seconds=elapsed,presented_fps=count/elapsed,untraced=True)
 assert count==frames
 updates=report['end']['C1Completed']-report['start']['C1Completed']
 skips=report['end']['C1Skipped']-report['start']['C1Skipped']
 assert updates==count+(skips if variant!='native' else 0),(updates,count,skips)
 report['updates']=updates
 report['skipped_presentations']=skips
 report['intenar_end']=val('*(unsigned short*)0xdff01c')
 report['blit_owned']=val(f'*(unsigned short*){probe+sym(fine_listing,"C4BlitOwned")}')
 # Every counted native sprite draw must include each opponent once.
 report['all_opponents_drawn']=report['end']['HeavyIncomplete']==0 and report['end']['HeavyCarCount']==7 and report['end']['HeavyCarMask']==254
 cmd('delete');cmd(f'monitor profile 1 "" "{out}/screenshot.bin"')
 from amigaxdev import barto
 kind,pixels=barto.last_screenshot(out/'screenshot.bin');(out/'frame.png').write_bytes(pixels)
 report['status']='captured' if report['end']['error']==0 else 'failed'
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)

finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
