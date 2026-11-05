"""Capture actual W6 rendering leases without writing game RAM."""
import argparse,json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from presentation_state import symbol
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--frames',type=int,default=4);a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(encoding='latin-1').splitlines();base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');h3=json.loads((a.capture/'entry-steps.json').read_text())['h3'];banks=r.memory_regions();frames=[]
terrain=any('time_terrain_cache_result:' in line for line in lines)
def stop(label):
 at=base+symbol(lines,label)
 trace=[]
 if terrain:
  for off,label,value in [(0xf03e,'TERRAIN_KEY','$d0'),(0xf06c,'TERRAIN_REBUILD','1'),(0xf066,'TERRAIN_REUSE','1')]:
   trace += [f'break *{m["entry"]["sim"]+off:#x}','commands','silent',f'printf "{label} %u\\n", {value}','continue','end']
 raw=r.command('gdb '+ '\n'.join(['delete']+trace+[f'break *{m["entry"]["sim"]+0x1098:#x}','commands','silent','printf "WORLD\\n"','continue','end',f'break *{at:#x}','continue','printf "STOP %u %u\\n", $pc, $sp']))
 match=re.search(r'STOP (\d+) (\d+)',raw)
 if not match or int(match[1])!=at:raise RuntimeError(raw[-1500:])
 return int(match[2]),len(re.findall(r'^WORLD$',raw,re.M)),raw

def snapshot(name):
 files=[]
 for address,end in banks:
  file=a.capture/f'{name}-{address:x}.bin'
  r.command(f'gdb dump binary memory {file} {address:#x} {end:#x}')
  assert file.stat().st_size==end-address
  files.append(dict(base=address,size=end-address,file=file.name))
 return files
for i in range(a.frames):
 sp,world,raw=stop('time_render_frame')
 r.command(f'gdb set $shape_record=*(unsigned int*){h3+0x4262:#x}+12\nset *(unsigned int*){h3+0xa278:#x}=$shape_record\nset *(unsigned int*){h3+0x4278:#x}=*(unsigned int*)($shape_record+6)')
 row=dict(index=i,world_before=world,entry_sp=sp,before=snapshot(f'lease-{i}-before'))
 sp2,world2,raw2=stop('time_render_before_draw');row.update(during=snapshot(f'lease-{i}-during'))
 extra_world=0;extra_raw=''
 if any('time_present_list_count:' in line for line in lines):
  _,extra_world,extra_raw=stop('time_present_list_restore')
  r.command(f'gdb set $shape_record=*(unsigned int*){h3+0x4262:#x}+72\nset *(unsigned int*){h3+0xa278:#x}=$shape_record\nset *(unsigned int*){h3+0x4278:#x}=*(unsigned int*)($shape_record+6)')
  row['list_before_restore']=snapshot(f'lease-{i}-list-rendered')
 sp3,world3,raw3=stop('time_render_restored')
 raw3=extra_raw+raw3;world3+=extra_world
 row.update(after=snapshot(f'lease-{i}-after'),world_during=world2+world3)
 assert sp2==sp-64 and sp3==sp-60,(sp,sp2,sp3)
 row['stack_checked']=True
 if terrain:
  row['terrain_keys']=[int(v) for v in re.findall(r'^TERRAIN_KEY (\d+)',raw3,re.M)]
  row['terrain_rebuilds']=len(re.findall(r'^TERRAIN_REBUILD ',raw3,re.M))
  row['terrain_reuses']=len(re.findall(r'^TERRAIN_REUSE ',raw3,re.M))
 (a.capture/f'lease-{i}-events.txt').write_text(raw+raw2+raw3)
 frames.append(row)
 (a.capture/'render-phase.json').write_text(json.dumps(dict(sha256=m['slave_sha256'],h3=h3,frames=frames,fixture='Explicit restoration component fixture: valid record 1 at entry, valid record 6 just before restore; no native mutation or performance claim'),indent=2)+'\n')
 print('Captured render lease',i,'world updates during',world2+world3,flush=True)
