#!/usr/bin/env python3
"""Read live W2/W3 inputs and compare native/replacement outputs with Python models."""
import argparse,json,re,struct,time
from pathlib import Path
from profile_window import command
from geometry_model import model
p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('kind',choices=['vertices','emit']);p.add_argument('--calls',type=int,default=32);p.add_argument('--label',default='');p.add_argument('--resume',action='store_true');a=p.parse_args()
meta=json.loads((a.capture/'anchor.json').read_text());g=meta['game_base'];base=meta.get('memory_base',0x200000);end=base+int(meta.get('memory_size',0x200000));entry,exit={'vertices':(0x1440,0x161c),'emit':(0x1662,0x194a)}[a.kind]
chip_end=int(meta.get('settings',{}).get('CHIP_KB') or 1024)*1024
out=a.capture/('model-'+a.kind+a.label);out.mkdir(exist_ok=a.resume)
def regs(t):return {k:int(v,16) for k,v in re.findall(r'^(\w+)\s+0x([0-9a-f]+)',t,re.M)}
def dump_range(target,lo,hi):
 for attempt in range(3):
  target.unlink(missing_ok=True)
  answer=command(f'gdb dump binary memory {target} {lo:#x} {hi:#x}')
  for _ in range(30):
   if target.exists() and target.stat().st_size==hi-lo:return target.read_bytes()
   time.sleep(.1)
 raise RuntimeError('Snapshot missing/incomplete: '+str(target)+' '+repr(answer))
def dump(target):
 if base:return dump_range(target,base,end)
 result=bytearray(end)
 for bank,lo,hi in [('chip',0,chip_end),('slow',0xc00000,end)]:
  part=target.with_suffix('.'+bank);result[lo:hi]=dump_range(part,lo,hi);part.unlink()
 target.write_bytes(result);return bytes(result)
command('stop');command('gdb delete')
for n in range(a.calls):
 if a.resume and (out/f'{n:03}.json').exists():continue
 r=regs(command(f'gdb tbreak *{g+entry:#x}\ncontinue\ninfo registers'))
 assert r['pc']==g+entry,r
 before=dump(out/f'{n:03}-in.bin')
 chip_path=out/f'{n:03}-chip-in.bin';chip=dump_range(chip_path,0,chip_end)
 a5=r['a5'];a4=r['a4'];lo=a5-0xbd6-base
 frame=before[lo:lo+0xbd6]; glob=before[meta['data_base']-base:meta['data_base']-base+0xa77c]
 def read(addr,size):
  if 0<=addr and addr+size<=len(chip):return chip[addr:addr+size]
  assert base<=addr and addr+size<=end,hex(addr)
  return before[addr-base:addr-base+size]
 expected,writes=model(a.kind,frame,a5,glob,read)
 rr=regs(command(f'gdb tbreak *{g+exit:#x}\ncontinue\ninfo registers'))
 assert rr['pc']==g+exit,rr
 after=dump(out/f'{n:03}-out.bin');actual=after[lo:lo+0xbd6]
 diffs=[hex(i-0xbd6) for i,(x,y) in enumerate(zip(expected,actual)) if x!=y]
 assert not diffs,(n,diffs[:30])
 chip_out=out/f'{n:03}-chip-out.bin';co=dump_range(chip_out,0,chip_end)
 for at,value in writes.items():
  got=co[at:at+len(value)] if at<len(co) else after[at-base:at-base+len(value)]
  assert got==value,(n,hex(at))
 (out/f'{n:03}.json').write_text(json.dumps({'before':r,'after':rr,'data_base':meta['data_base'],'base':base,'kind':a.kind},indent=2)+'\n')
 print(f'{a.kind} {n+1}/{a.calls}: frame and output match',flush=True)
print('All live calls match the original-code model')
