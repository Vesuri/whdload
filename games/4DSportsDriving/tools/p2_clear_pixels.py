import json,re,hashlib,sys
from pathlib import Path
from profile_window import command,ROOT
cap=Path(sys.argv[1]);meta=json.loads((cap/'anchor.json').read_text());g=meta['game_base'];results=[]
def regs(): return {k:int(v,16) for k,v in re.findall(r'^(\w+)\s+0x([0-9a-f]+)',command('gdb info registers'),re.M)}
def read(addr,n):
 p=cap/'clear-scratch.bin';p.unlink(missing_ok=True)
 ans=command(f'gdb dump binary memory {p.relative_to(ROOT)} {addr:#x} {addr+n:#x}')
 assert p.exists(),ans
 b=p.read_bytes();assert len(b)==n;return b
command('stop');command('gdb delete')
for i in range(12):
 command(f'gdb tbreak *{g+0x347b0:#x}\ncontinue');r=regs();assert r['pc']==g+0x347b0
 plane=r['a0'];off=r['d1']&65535;off=off if off<32768 else off-65536
 width=(r['d3']&63) or 64;rows=((r['d3']&65535)>>6) or 1024;mod=r['d0']&65535;mod=mod if mod<32768 else mod-65536
 assert r['d2']&65535 in (0x100,0x1ff)
 before=read(plane,8000);expected=bytearray(before);fill=bytes([r['d2']&255])*(2*width)
 for y in range(rows):
  at=off+y*(width*2+mod);assert 0<=at and at+len(fill)<=8000
  expected[at:at+len(fill)]=fill
 command(f'gdb tbreak *{g+0x347d8:#x}\ncontinue');rr=regs();assert rr['pc']==g+0x347d8
 for k in [f'd{x}' for x in range(8)]+[f'a{x}' for x in range(1,7)]+['sp']:
  assert r[k]==rr[k],(k,r[k],rr[k])
 assert rr['a0']==plane+off
 actual=read(plane,8000);assert actual==expected,('pixel mismatch',i)
 results.append({'plane':plane,'offset':off,'width_pixels':width*16,'rows':rows,'fill':r['d2']&255,'equal_bytes':8000,'unchanged_outside_rectangle':True,'registers_match':True,'sha256':hashlib.sha256(actual).hexdigest()})
(cap/'clear-pixels.json').write_text(json.dumps({'passed':True,'calls':results,'scope':'Whole 8000-byte plane against exact D-only fill model, including unchanged pixels outside the rectangle'},indent=2)+'\n')
print('All',len(results),'rectangle planes match exactly, including outside pixels and registers')
