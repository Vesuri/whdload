from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a500';kind='release-frame-'+os.environ.get('ARM','production');variant=os.environ.get('C1_VARIANT','candidate');name='c4-q03-'+kind+'-'+profile+'-'+variant;out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);arm=os.environ.get('ARM','production');kind='000' if profile.startswith('a500') else '020' if profile=='a1200' else 'fine';b=r/f'tmp/build/production-frames/{arm}-{kind}.slave';profiles=json.loads((r/'manifest/step3-profiles.json').read_text());runb=b
if arm=='accepted':
 raw=b.read_bytes();target=(r/'tmp/build/production-matched/FerrariFormulaOne.slave').read_bytes();code=bytearray(raw[32:-4]);assert len(raw)<=len(target);code+=bytes(len(target)-len(raw));header=bytearray(raw[:32]);struct.pack_into('>I',header,20,len(code)//4);struct.pack_into('>I',header,28,len(code)//4);runb=r/f'tmp/build/production-matched/accepted-{kind if False else profile}.slave';runb.write_bytes(header+code+bytes.fromhex('000003f2'))
os.environ.update(profiles[profile]);os.environ.update(json.loads(os.environ.get('RELEASE_PROFILE_OVERRIDES','{}')));os.environ.update(SLAVE=str(runb),WARP='1',WINDOW='none',JOY0='mouse',WHD_ARGS=os.environ.get('RELEASE_WHD_ARGS','CUSTOM1=1 CUSTOM2=1'),DETERMINISTIC='1',FSUAE=str(r/'tmp/step5-frame-observer-build/fs-uae'),FF1_FRAME_SENTINEL='0',KICKSTART=os.environ['KICKSTART_A1200'] if not profile.startswith('a500') else os.environ['KICKSTART'])
s=Server('ff1measure',root=str(r),profile_window=False);log=[]
try:
 g=s.boot()
 def cmd(c):
  v=g.cmd(c,timeout=180);log.append(c+'\n'+v);(out/'live.log').write_text('\n'.join(log));return v
 def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
 def dump(label):
  chip=int(os.environ['CHIP_KB'])*1024
  cmd(f'dump binary memory {out.relative_to(r)}/{label}.bin 0 {chip}')
  mem=(out/(label+'.bin')).read_bytes()
  for bank,base,key in [('fast',0x200000,'FAST_KB'),('slow',0xc00000,'SLOW_KB')]:
   size=int(os.environ[key])*1024
   if size:
    cmd(f'dump binary memory {out.relative_to(r)}/{label}-{bank}.bin {base} {base+size}')
    mem+=bytes(base-len(mem))+(out/(label+'-'+bank+'.bin')).read_bytes()
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
 report=dict(root=hex(root),table=hex(table),race=hex(race),marker=hex(marker),pc=val('$pc'),slave_sha256=hashlib.sha256(runb.read_bytes()).hexdigest())
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
 cmd('delete');cmd(f'break *{root+0x2e6}')
 cmd('condition $bpnum *(unsigned int*)$a3 == 0x22f30')
 assert 'Breakpoint' in cmd('continue')
 race=val('$d0+*(unsigned int*)($a3+28)')
 report['race']=hex(race);(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')

 import re
 kind='000' if profile.startswith('a500') else '020' if profile=='a1200' else 'fine'
 meta=json.loads(b.with_suffix('.json').read_text());hs=meta['host_symbols'];sy=meta['symbols'];host=marker-hs['FF1PublicMarker'];probe=host+meta['offset']
 report.update(host=hex(host),probe=hex(probe),kind=kind,arm=arm)
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 cmd('delete')
 faults=['FF1WrongVersion'] if arm=='production' else []
 for n in faults:cmd(f'break *{host+hs[n]}')
 for n in (['C1Fault','velocity_stop'] if kind=='000' else ['C1Fault'] if kind=='020' else ['velocity_fault','schedule_bad']):
  if n in sy:cmd(f'break *{probe+sy[n]}')
 checkpoint=probe+sy['FF1PresentationAfterTick' if kind=='fine' else 'C1Checkpoint'];cmd(f'break *{checkpoint}')
 assert 'Breakpoint' in cmd('continue')
 report['stop_pc']=hex(val('$pc'));report['error']=val(f'*(unsigned int*){probe+sy["error"]}')
 if val('$pc')!=checkpoint:
  report['regs']=cmd('info registers');dump('fault');(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');raise AssertionError(report)
 ctx=probe+sy['schedule_context' if kind=='fine' else 'C1Context'];report['context_address']=hex(ctx)
 from amigaxdev import barto
 from PIL import Image
 listing=Path(meta['listing']).read_text();instruction='bsr.l B8Draw' if kind=='fine' else 'bsr.w B8Draw'
 matches=[int(m[1],16) for m in re.finditer(r'^00:([0-9A-F]{8}) [0-9A-F]+\s+\d+:\s+'+re.escape(instruction)+r'$',listing,re.M)]
 assert len(matches)==1,matches
 draw_return=probe+matches[0]+(6 if kind=='fine' else 4)
 cmd('monitor warp 0');cmd('delete');cmd(f'break *{draw_return}');frames=[]
 for i in range(30):
  assert 'Breakpoint' in cmd('continue')
  completed=val(f'*(unsigned int*){ctx+24}')
  path=out/f'frame-{completed}.bin';cmd(f'monitor profile 2 "" "{path}"')
  _,pixels=barto.last_screenshot(path);png=path.with_suffix('.png');png.write_bytes(pixels);path.unlink()
  im=Image.open(png).convert('RGB');frames.append({'update':completed,'size':im.size,'pixel_sha256':hashlib.sha256(im.tobytes()).hexdigest()})
 report['frames']=frames;report['error']=val(f'*(unsigned int*){probe+sy["error"]}');report['status']='captured';assert report['error']==0
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(profile,arm,'captured',len(frames),'frames',flush=True)

finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
