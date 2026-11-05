"""Observe native D-only planes only after the next register-write boundary.
The last plane is excluded: its routine may return with DMA still active.
"""
import json,re,hashlib,sys
from pathlib import Path
from profile_window import command,ROOT
cap=Path(sys.argv[1]);meta=json.loads((cap/'anchor.json').read_text());g=meta['game_base'];results=[]
def regs():return {k:int(v,16) for k,v in re.findall(r'^(\w+)\s+0x([0-9a-f]+)',command('gdb info registers'),re.M)}
def read(addr,n,label):
 p=cap/(label+'.bin');p.unlink(missing_ok=True)
 ans=command(f'gdb dump binary memory {p.relative_to(ROOT)} {addr:#x} {addr+n:#x}')
 assert p.exists(),ans
 b=p.read_bytes();assert len(b)==n;return b
def stop_next():
 command(f'gdb tbreak *{g+0x347cc:#x}\ncontinue');r=regs();assert r['pc']==g+0x347cc;return r
command('stop');command('gdb delete');r=stop_next()
while len(results)<9:
 if not r['d7']&255:r=stop_next();continue
 off=r['d1']&65535;off=off if off<32768 else off-65536;plane=r['a0']-off
 width=(r['d3']&63) or 64;rows=((r['d3']&65535)>>6) or 1024
 mod=r['d0']&65535;mod=mod if mod<32768 else mod-65536
 assert r['d2']&65535 in (0x100,0x1ff)
 i=len(results);before=read(plane,8000,f'native-{i:02}-before');expected=bytearray(before);fill=bytes([r['d2']&255])*(2*width)
 for y in range(rows):
  at=off+y*(2*width+mod);assert 0<=at and at+len(fill)<=8000;expected[at:at+len(fill)]=fill
 old=r;r=stop_next()
 assert r['a0']!=old['a0'],'Next plane must differ'
 actual=read(plane,8000,f'native-{i:02}-after');assert actual==expected,('Native blitter disagrees with model',i)
 results.append({'plane':plane,'offset':off,'width_pixels':width*16,'rows':rows,'fill':old['d2']&255,'equal_bytes':8000,'unchanged_outside_rectangle':True,'sha256':hashlib.sha256(actual).hexdigest(),'completion':'next plane register-write boundary after native BBUSY wait'})
cpu=json.loads((ROOT/'tmp/prof/p2-cpu-rect-layout/B/clear-pixels.json').read_text())['calls'];pairs=[]
for i,n in enumerate(results):
 for j,c in enumerate(cpu):
  if all(n[k]==c[k] for k in ['offset','width_pixels','rows','fill','sha256']):pairs.append([i,j])
assert pairs,'No whole-plane matches between native blitter and CPU captures'
report={'passed':True,'native_calls':results,'cpu_reference':'p2-cpu-rect-layout/B/clear-pixels.json','whole_plane_equal_pairs':pairs,'scope':'Actual native completed output against the same exact fill model, plus direct 8000-byte output hash matches where dimensions, offset and fill agree. Initial images are not asserted equal across boots. Last native plane excluded to avoid reading active DMA.'}
(cap/'native-clear-pixels.json').write_text(json.dumps(report,indent=2)+'\n');print('Native model checks:',len(results),'direct whole-plane output matches:',len(pairs))
