#!/usr/bin/env python3
"""Independent models for W6 live state clearing and primitive depth/header output."""
import argparse,json,re,struct,time
from pathlib import Path
from profile_window import command
from geometry_model import s16,s32
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('kind',choices=['clear','epilogue']);p.add_argument('--calls',type=int,default=24);a=p.parse_args()
meta=json.loads((a.capture/'anchor.json').read_text());g=meta['game_base'];entry,exit={'clear':(0xfc6,0xfcc),'epilogue':(0x20c8,0x217c)}[a.kind]
out=a.capture/('model-'+a.kind);out.mkdir(exist_ok=False)
def regs(t):return {k:int(v,16) for k,v in re.findall(r'^(\w+)\s+0x([0-9a-f]+)',t,re.M)}
def read(n,label,addr,size):
 target=out/f'{n:03}-{label}.bin'
 for _ in range(3):
  target.unlink(missing_ok=True);ans=command(f'gdb dump binary memory {target} {addr:#x} {addr+size:#x}')
  for _ in range(30):
   if target.exists() and target.stat().st_size==size:return target.read_bytes()
   time.sleep(.1)
 raise RuntimeError(ans)
command('stop');command('gdb delete')
for n in range(a.calls):
 r=regs(command(f'gdb tbreak *{g+entry:#x}\ncontinue\ninfo registers'));assert r['pc']==g+entry,r
 origin=r['a5']-0xbd6;frame=read(n,'frame-in',origin,0xbd6);want=bytearray(frame);wr=dict(r)
 if a.kind=='clear':
  count=(r['d1']&0xffff)+1;at=r['a0']-origin
  assert 0<=at and at+count<=len(frame)
  want[at:at+count]=bytes([r['d2']&255])*count
  wr['d1']=r['d1']|0xffff;wr['a0']+=count
 else:
  glob=read(n,'globals',r['a4']-0x19b4,36);num=glob[0];dest=struct.unpack_from('>I',glob,32)[0]
  record=bytearray(read(n,'record-in',dest,6));total=struct.unpack_from('>i',frame,len(frame)-0x1a4)[0];translation=struct.unpack_from('>h',frame,len(frame)-0x1c8)[0]
  if num in (1,2,4,8):q=total>>{1:0,2:1,4:2,8:3}[num]
  else:
   div=num if num<128 else num-256;assert div
   q=abs(total)//abs(div)
   if (total<0)!=(div<0):q=-q
   wr['d1']=div&0xffffffff
  depth=s16(q+translation)
  struct.pack_into('>h',want,len(want)-2,depth)
  counter=struct.unpack_from('>H',want,len(want)-0x94)[0];struct.pack_into('>H',want,len(want)-0x94,(counter+1)&0xffff)
  struct.pack_into('>h',record,0,depth);record[2]=frame[-0x21];record[3]=num;record[4]=frame[-0x95];record[5]=0x7f
  wr['d0']=((0 if num==1 else q)&0xffff0000)|(translation&0xffff);wr['a0']=dest
 rr=regs(command(f'gdb tbreak *{g+exit:#x}\ncontinue\ninfo registers'));assert rr['pc']==g+exit,rr
 actual=read(n,'frame-out',origin,0xbd6)
 assert actual==want,(n,[hex(i-0xbd6) for i,(x,y) in enumerate(zip(actual,want)) if x!=y][:20])
 for key in [f'd{i}' for i in range(8)]+[f'a{i}' for i in range(7)]+['sp']:assert rr[key]==wr[key],(n,key,hex(rr[key]),hex(wr[key]))
 if a.kind=='epilogue':assert read(n,'record-out',dest,6)==record,n
 (out/f'{n:03}.json').write_text(json.dumps({'before':r,'after':rr,'expected_regs':wr},indent=2)+'\n')
 print(f'{a.kind} {n+1}/{a.calls}: frame, output and registers match',flush=True)
