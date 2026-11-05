"""Read-only before/after native draw snapshots. No synthetic drawing or state writes."""
import argparse,json,re,struct
from pathlib import Path
import route_status as r
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());sim=m['entry']['sim'];h3=json.loads((a.capture/'entry-steps.json').read_text())['h3']
banks=r.memory_regions();frames=[]
def read_words(at,count=1):
 raw=r.command(f'gdb x/{count}wx {at:#x}')
 return [int(v,16) for line in raw.splitlines() if ':' in line for v in re.findall(r'0x[0-9a-f]+',line.split(':',1)[1])]
def stop(addresses):
 cmd=['delete']+[f'break *{at:#x}' for at in addresses]+['continue','printf "STOP %u %u\\n", $pc, $sp']
 raw=r.command('gdb '+'\n'.join(cmd));match=re.search(r'STOP (\d+) (\d+)',raw)
 if not match:raise RuntimeError(raw[-2000:])
 pc,sp=map(int,match.groups())
 if pc not in addresses:raise RuntimeError('Unexpected stop')
 return pc,sp

def snapshot(name):
 files=[]
 for base,end in banks:
  dest=a.capture/f'{name}-{base:x}.bin'
  r.command(f'gdb dump binary memory {dest} {base:#x} {end:#x}')
  if dest.stat().st_size!=end-base:raise RuntimeError('Short snapshot')
  files.append(dict(base=base,file=dest.name,size=end-base))
 return files
for frame in range(3):
 pc,sp=stop([sim+0x56c]);root_sp=sp;root_return=read_words(sp)[0]
 row=dict(index=frame,outer_return=root_return-sim,before=snapshot(f'{frame}-outer-before'))
 pc,sp=stop([sim+0x2c552,root_return])
 if pc==root_return:raise RuntimeError('Draw did not enter 3D; retain evidence and inspect path')
 render_sp=sp
 ret,context,objects=read_words(sp,3)
 raw=r.command(f'gdb x/uh {sp+12:#x}');count=int(raw.split(':',1)[1].strip())
 if not 0<=count<=512:raise RuntimeError('Invalid object count')
 row.update(context=context,objects=read_words(objects,count) if count else [],renderer_return=ret-sim,render_before=snapshot(f'{frame}-3d-before'))
 pc,sp=stop([ret]);assert sp==render_sp+4,('3D return stack',sp,render_sp);row['render_after']=snapshot(f'{frame}-3d-after')
 pc,sp=stop([root_return]);assert sp==root_sp+4,('outer return stack',sp,root_sp);row['return_stack_checked']=True;row['after']=snapshot(f'{frame}-outer-after')
 frames.append(row)
 (a.capture/'render-mutations.json').write_text(json.dumps(dict(sha256=m['slave_sha256'],sim=sim,h3=h3,frames=frames),indent=2)+'\n')
 print('Captured draw',frame,'objects',count,flush=True)
