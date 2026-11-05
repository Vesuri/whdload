"""Isolated synthetic native circle calls: native edge model and CPU/native pixel twin.
Preserve native circle construction/clipping, including its small-circle table.
No performance claim: debugger supplies arguments and same-input pixel buffers.
"""
import json,re,struct,sys
from pathlib import Path
from profile_window import command,ROOT
from p3_span_model import render
p=Path(sys.argv[1]).resolve();m=json.loads((p/'anchor.json').read_text());g=m['game_base'];base=m['slave_base'];out=p/'circles';out.mkdir();scratch=out/'scratch.bin'
command('gdb set remote binary-download-packet off\nset remote memory-write-packet-size 256\nset remote memory-write-packet-size fixed')
syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(p/'slave.lst').read_text(encoding='latin1'),re.M)}
def regs():return {k:int(v,16) for k,v in re.findall(r'^(\w+)\s+0x([0-9a-f]+)',command('gdb info registers'),re.M)}
def read(addr,n):
 scratch.unlink(missing_ok=True);s=command(f'gdb dump binary memory {scratch.relative_to(ROOT)} {addr:#x} {addr+n:#x}');b=scratch.read_bytes();assert len(b)==n,s;return b
def restore(addr,data,name):
 f=out/name;f.write_bytes(data);return f'restore {f.relative_to(ROOT)} binary {addr:#x}'
def u16(b,o):return struct.unpack_from('>H',b,o)[0]
def s16(b,o):return struct.unpack_from('>h',b,o)[0]
def u32(b,o):return struct.unpack_from('>I',b,o)[0]
command(f'gdb delete\ntbreak *{g+0xab8c:#x} if *(unsigned short*){base+syms["raster_frame_phase"]:#x}==1\ncontinue');saved=regs();assert saved['pc']==g+0xab8c
assert u16(read(base+syms['raster_frame_phase'],2),0)==1
a=saved['a4'];desc=read(a+0xbea,0x108);fast=list(struct.unpack_from('>4I',desc,0x14));chip=list(struct.unpack('>4I',read(base+syms['raster_frame_planes'],16)));assert fast==[fast[0]+8000*j for j in range(4)]
clip=struct.unpack('>4h',read(a+0xce0,8));assert desc[0x4c]==15
initial_fast=read(fast[0],32000);initial_chip=[read(x,8000) for x in chip];initial_extra=read(a-0x3a3e,10)
stack=saved['sp']-64;ret=saved['pc'];results=[]
cases=[(160,60,d) for d in (-1,0,1,2,3,8,17,38,39,40,41,80,160)]+[(x,y,d) for x,y in ((0,60),(319,60),(160,9),(160,129),(-100,60),(420,60)) for d in (17,41)]
reg_restore=[f'set ${k}={v:#x}' for k,v in saved.items() if re.fullmatch(r'd[0-7]|a[0-6]|sp',k)]
for i,(x,y,diam) in enumerate(cases):
 before=bytes(((j*13+i*37)^(j>>6))&255 for j in range(32000));colour=i%16;inputs=struct.pack('>Ihhhh',ret,x,y,diam,colour);prefix=f'{i:03}'
 init=[restore(stack,inputs,'args.bin'),f'set *(unsigned char*){a-0x3a3a:#x}=0']
 for j,addr in enumerate(chip):init.append(restore(addr,before[j*8000:(j+1)*8000],f'{prefix}-plane{j}.bin'))
 init += [f'set *(unsigned int*){a+0xbfe+j*4:#x}={addr:#x}' for j,addr in enumerate(chip)]
 init += [f'set *(unsigned short*){base+syms["raster_frame_phase"]:#x}=2']+reg_restore+[f'set $sp={stack:#x}',f'set $pc={g+0x286fe:#x}',f'break *{g+0x2c6d6:#x}',f'break *{ret:#x}','continue']
 answer=command('gdb '+'\n'.join(init[:-1]));(out/f'{prefix}-setup.log').write_text(answer)
 assert not any(x in answer.lower() for x in ('could not write','error','cannot')),answer
 setup_regs=regs();(out/f'{prefix}-setup-registers.json').write_text(json.dumps(setup_regs,indent=2))
 assert setup_regs['pc']==g+0x286fe and setup_regs['sp']==stack,setup_regs
 assert read(stack,12)==inputs
 print(i,'native call setup verified',hex(setup_regs['pc']),hex(stack),flush=True)
 command('gdb continue');expected=before;spans=[]
 while True:
  r=regs()
  if r['pc']==ret:break
  assert r['pc']==g+0x2c6d6,r
  f=read(r['a5']-0x36,0x12);h=u16(f,10);yy=s16(f,8)
  if h:
   left=struct.unpack('>'+str(h)+'h',read(u32(f,0),h*2));right=struct.unpack('>'+str(h)+'h',read(u32(f,4),h*2))
   c=dict(kind='solid',y=yy,height=h,spans=list(zip(left,right)),colour=u16(f,12),colour2=0,pattern=0,stipple=0,stipple_pattern=0,write_mask=15)
   expected=render(c,expected);spans.append(c)
  command('gdb continue')
 command('gdb delete')
 # Native dot construction bypasses the span core.
 if diam==1 and clip[0]<=x<clip[1] and clip[2]<=y<clip[3]:
  bb=bytearray(before)
  for plane in range(4):
   at=plane*8000+y*40+x//8;mask=128>>(x&7);bb[at]=bb[at]|mask if colour&(1<<plane) else bb[at]&(255^mask)
  expected=bytes(bb)
 native=b''.join(read(addr,8000) for addr in chip)
 assert native==expected,('native model mismatch',i,x,y,diam,sum(a!=b for a,b in zip(native,expected)))
 # Same geometry/colour and same initial bytes; phase1 invokes the CPU kernels.
 init=[restore(fast[0],before,f'{prefix}-before.bin')]
 for j,addr in enumerate(chip):init.append(restore(addr,before[j*8000:(j+1)*8000],f'{prefix}-plane{j}.bin'))
 init += [f'set *(unsigned int*){a+0xbfe+j*4:#x}={addr:#x}' for j,addr in enumerate(fast)]
 init += [f'set *(unsigned short*){base+syms["raster_frame_phase"]:#x}=1',f'set *(unsigned char*){a-0x3a3a:#x}=0']+reg_restore+[restore(stack,inputs,'args.bin'),f'set $sp={stack:#x}',f'set $pc={g+0x286fe:#x}',f'tbreak *{ret:#x}','continue']
 command('gdb '+'\n'.join(init));assert regs()['pc']==ret
 phase=u16(read(base+syms['raster_frame_phase'],2),0);assert phase==1,('Unexpected fallback',i,phase)
 cpu=read(fast[0],32000);assert cpu==native,('CPU/native mismatch',i,sum(a!=b for a,b in zip(cpu,native)))
 (out/f'{prefix}-native.bin').write_bytes(native);(out/f'{prefix}-cpu.bin').write_bytes(cpu)
 results.append(dict(x=x,y=y,diameter=diam,colour=colour,span_calls=spans,compared_bytes=32000,changed_bytes=sum(a!=b for a,b in zip(before,native))))
 (out/'cases.json').write_text(json.dumps(results,indent=2)+'\n');print(i,x,y,diam,len(spans),'model+CPU/native match',flush=True)
restore_cmd=[restore(fast[0],initial_fast,'restore-fast.bin'),restore(a-0x3a3e,initial_extra,'restore-extra.bin')]
for j,addr in enumerate(chip):restore_cmd.append(restore(addr,initial_chip[j],f'restore-chip{j}.bin'))
restore_cmd += [f'set *(unsigned int*){a+0xbfe+j*4:#x}={addr:#x}' for j,addr in enumerate(fast)]+reg_restore+[f'set $pc={ret:#x}']
command('gdb '+'\n'.join(restore_cmd));report=dict(cases=len(results),native_model_failures=0,cpu_native_failures=0,compared_bytes_per_case=32000,scope='Synthetic circle arguments and same initial bitmap; native clipping/edge construction retained. Small-table, large-helper, dot, zero/negative, and clipping/no-op cases. Not timing evidence.')
(p/'circle-twin.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
