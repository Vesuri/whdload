#!/usr/bin/env python3
"""Capture native primitive inputs and actual planar output around the drawer.
Compare matched input signatures across same-build W1-off/on captures separately.
"""
import argparse,json,re,struct,hashlib,time
from pathlib import Path
from profile_window import command, ROOT
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--calls',type=int,default=12);a=p.parse_args();cap=a.capture
meta=json.loads((cap/'anchor.json').read_text());g=meta['game_base'];out=cap/'draw-pixels';out.mkdir(exist_ok=False)
slave=(cap/'slave.slave').read_bytes();sl=meta['marker']-slave.index(b'4DTAPE!!')+32
symbols={n:int(v,16)+sl for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
pixel_ready=symbols.get('tape_pixels_ready')
assert pixel_ready,'Build with VERIFY=1 PIXELS=1 for a native WaitBlit completion boundary'
def regs():return {k:int(v,16) for k,v in re.findall(r'^(\w+)\s+0x([0-9a-f]+)',command('gdb info registers'),re.M)}
def read(addr,size):
 path=out/'scratch.bin'
 for _ in range(3):
  path.unlink(missing_ok=True);answer=command(f'gdb dump binary memory {path.resolve().relative_to(ROOT)} {addr:#x} {addr+size:#x}')
  for _ in range(30):
   if path.exists() and path.stat().st_size==size:return path.read_bytes()
   time.sleep(.1)
 raise RuntimeError(answer)
def u16(b,o=0):return struct.unpack_from('>H',b,o)[0]
def u32(b,o=0):return struct.unpack_from('>I',b,o)[0]
def digest(b):return hashlib.sha256(b).hexdigest()
command('stop');command('gdb delete');results=[]
for n in range(a.calls):
 command(f'gdb tbreak *{g+0xab82:#x}\ncontinue');r=regs();assert r['pc']==g+0xab82,r
 ret=u32(read(r['sp'],4));a4=r['a4'];data=read(meta['data_base'],0xa77c);bias=a4-meta['data_base'];count=u16(data,bias-0x19b8);assert 0<count<=300,count
 records=[];idx=300
 for _ in range(count):
  idx=u16(data,bias-0x20c6+2*idx);assert idx<300,idx
  ptr=u32(data,bias-0x1e6c+4*idx);header=read(ptr,6);num=header[3]
  records.append(read(ptr,6+4*num))
 # The active drawing descriptor is copied to a4+$BEA by $33E1C.
 desc=data[bias+0xbea:bias+0xbea+0x108];bpr=u16(desc,0xea);rows=u16(desc,0xec);depth=desc[0x11]
 assert bpr==40 and rows==200 and depth==4,(bpr,rows,depth)
 planes=[u32(desc,0x14+4*i) for i in range(depth)]
 before=b''.join(read(addr,bpr*rows) for addr in planes)
 tables=b''.join(read(u32(data,bias+off),size) for off,size in [(0xb40,512),(0xb44,512),(0xb48,512),(0xb4c,1024)])
 inputs=b''.join(struct.pack('>I',len(b))+b for b in records)+tables+data[bias+0xce0:bias+0xcf0]+bytes([data[bias-0x7708]])+data[bias-0x7538:bias-0x7536]+before
 command(f'gdb tbreak *{ret:#x}\ncontinue');rr=regs();assert rr['pc']==ret and rr['sp']==r['sp']+4,rr
 # DisownBlitter may return with the last DMA still active on a fast CPU.
 # Preserve the immediate result, then wait for actual blitter completion.
 immediate=b''.join(read(addr,bpr*rows) for addr in planes)
 command(f'gdb tbreak *{pixel_ready:#x}\ncontinue');rr=regs();assert rr['pc']==pixel_ready,rr
 after=b''.join(read(addr,bpr*rows) for addr in planes)
 (out/f'{n:03}-return-planes.bin').write_bytes(immediate)
 (out/f'{n:03}-input.bin').write_bytes(inputs);(out/f'{n:03}-planes.bin').write_bytes(after)
 results.append({'call':n,'primitives':count,'input_sha256':digest(inputs),'output_sha256':digest(after),'changed_bytes':sum(x!=y for x,y in zip(before,after)),'planes':planes,'completion_boundary':'native graphics WaitBlit','bytes_changed_after_return':sum(x!=y for x,y in zip(immediate,after))})
 (out/'results.json').write_text(json.dumps(results,indent=2)+'\n');print(results[-1],flush=True)
(out/'scratch.bin').unlink(missing_ok=True)
