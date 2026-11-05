import json,re,sys,os
from pathlib import Path
from profile_window import command
p=Path(sys.argv[1]);b=(p/'memory.bin').read_bytes();m=json.loads((p/'anchor.json').read_text());syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(p/'slave.lst').read_text(encoding='latin1'),re.M)};base=m.get('slave_base',m['memory_base']+b.index(b'4DFRAMTW')-syms['raster_frame_marker'])
# Completed-frame counters are readable while replay is paused; do not wait for another live frame.
command('gdb delete')
names=['raster_frames_passed','raster_frames_failed','raster_bg_passed','raster_bg_failed','raster_bg_seeded','raster_staged_count','raster_fallback_count','raster_fallback_pc']
if 'raster_bg_prefix_passed' in syms:names.append('raster_bg_prefix_passed')
s=command('gdb '+'\n'.join(f'p /u *(unsigned int*){base+syms[n]:#x}' for n in names));v=[int(x) for x in re.findall(r'^\$\d+ = (\d+)',s,re.M)];assert len(v)==len(names);r=dict(zip(names,v));r['fallback_offset']=hex(r['raster_fallback_pc']-m['game_base']) if r['raster_fallback_pc'] else None;(p/'background-twin.json').write_text(json.dumps(r,indent=2)+'\n');print(r);assert r['raster_frames_passed']>=10 and r['raster_bg_passed']>=10 and r['raster_frames_failed']==r['raster_bg_failed']==0

if os.environ.get('P3_PREFIX_REQUIRED')=='1':assert r.get('raster_bg_prefix_passed',0)>0,r
