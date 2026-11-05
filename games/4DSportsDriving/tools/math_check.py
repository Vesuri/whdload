#!/usr/bin/env python3
"""Compare live original/replacement C calls with independent arithmetic models."""
import argparse,json,re,struct,time
from pathlib import Path
from profile_window import command
from geometry_model import rotate_parent,s16
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('kind',choices=['face','parent']);p.add_argument('--calls',type=int,default=32);a=p.parse_args()
meta=json.loads((a.capture/'anchor.json').read_text());g=meta['game_base'];entry=g+{'face':0xaad4,'parent':0xa756}[a.kind]
out=a.capture/('model-'+a.kind);out.mkdir(exist_ok=True);assert not list(out.glob('*.json')),'Use a new capture for repeated model checks'
def regs(t):return {k:int(v,16) for k,v in re.findall(r'^(\w+)\s+0x([0-9a-f]+)',t,re.M)}
def read(n,label,addr,size):
 target=out/f'{n:03}-{label}.bin'
 ans=command(f'gdb dump binary memory {target} {addr:#x} {addr+size:#x}')
 for _ in range(30):
  if target.exists() and target.stat().st_size==size:return target.read_bytes()
  time.sleep(.1)
 raise RuntimeError(ans)
command('stop');command('gdb delete')
for n in range(a.calls):
 r=regs(command(f'gdb tbreak *{entry:#x}\ncontinue\ninfo registers'));assert r['pc']==entry,r
 raw=read(n,'args',r['sp'],8 if a.kind=='face' else 22);ret=struct.unpack_from('>I',raw)[0]
 args=raw[4:]
 if a.kind=='face':
  pt=struct.unpack('>I',args)[0];points=struct.unpack('>6h',read(n,'points',pt,12))
  x0,y0,x1,y1,x2,y2=points
  dx1=x0-x1;dx2=x2-x1;dy1=s16(y0-y1);dy2=s16(y2-y1)
  expected=int(dx2*dy1>dx1*dy2) if (dx1 or dx2) and (dy1 or dy2) else 0
 else:
  parent,rec,matrix,dest=struct.unpack_from('>4I',args);mode=args[16]
  pv=struct.unpack('>3h',read(n,'parent',parent,6));rv=struct.unpack('>3h',read(n,'rec',rec,6));mv=struct.unpack('>9h',read(n,'matrix',matrix,18))
  expected=rotate_parent(pv,rv,mv,mode)
 rr=regs(command(f'gdb tbreak *{ret:#x}\ncontinue\ninfo registers'));assert rr['pc']==ret,rr
 assert rr['sp']==r['sp']+4
 for reg in ['d2','d3','d4','d5','d6','d7','a2','a3','a4','a5','a6']:assert r[reg]==rr[reg],(n,reg)
 if a.kind=='face':actual=rr['d0']
 else:
  actual=list(struct.unpack('>3h',read(n,'output',dest,6)))
  after=read(n,'args-after',rr['sp'],18);expected_args=bytearray(args)
  struct.pack_into('>I',expected_args,0,parent+4);struct.pack_into('>I',expected_args,12,dest+4)
  assert after==expected_args,(n,after.hex(),expected_args.hex())
 assert actual==expected,(n,actual,expected)
 (out/f'{n:03}.json').write_text(json.dumps({'before':r,'after':rr,'expected':expected,'actual':actual},indent=2)+'\n')
 print(f'{a.kind} {n+1}/{a.calls}: model, registers and arguments match',flush=True)
