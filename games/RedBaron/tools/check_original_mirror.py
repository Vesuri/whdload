#!/usr/bin/env python3
"""Observe one complete original mirror call and check the host model and preserved registers."""
import argparse,json,re,struct,sys
from pathlib import Path
import route_status as r,step_log
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from mirror_model import mirror
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
state=step_log.collect();sim,h3=state['sim'],state['h3']
def regs():
    return {k:int(v,16) for k,v in re.findall(r'^(\w+)\s+0x([0-9a-f]+)',r.command('gdb info registers'),re.M)}
def dump(name,lo,size):
    path=a.out/name;r.command(f'gdb dump binary memory {path} {lo:#x} {lo+size:#x}');return path.read_bytes()
r.command(f'gdb break *{sim+0x304d0:#x}\ncontinue\ndelete')
before=regs()
if before['pc']!=sim+0x304d0:raise RuntimeError('Did not reach mirror entry')
desc=dump('descriptor.bin',before['a0'],18);planes,mask,w,h,ps,orient=struct.unpack('>IIHHIH',desc)
depth=struct.unpack('>H',dump('depth.bin',h3+0x9d3c,2))[0];stride=((w+15)//16)*2
source=dump('planes-before.bin',planes,stride*h*depth);dump('mask-before.bin',mask,(stride+2)*h)
r.command(f'gdb break *{sim+0x30570:#x}\ncontinue\ndelete')
after=regs()
if after['pc']!=sim+0x30570:raise RuntimeError('Did not reach mirror return')
actual=(dump('planes-after.bin',planes,len(source)),dump('mask-after.bin',mask,(stride+2)*h));expected=mirror(source,w,h,depth)
changed=[k for k in before if k not in ('pc','ps','sr') and before[k]!=after[k]]
result=dict(width=w,height=h,depth=depth,planes_match=actual[0]==expected[0],mask_match=actual[1]==expected[1],changed_registers=changed,before=before,after=after)
(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if not all([result['planes_match'],result['mask_match'],not changed]):raise SystemExit(1)
