#!/usr/bin/env python3
"""Summarize same-build stationary timing plus explicitly identified pixel evidence."""
import argparse,json,re,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('prefix');p.add_argument('--machine',choices=['a500','020'],required=True)
for name in ('off','on','pixel-off','pixel-on'):p.add_argument('--'+name,type=Path)
a=p.parse_args();assert bool(a.off)==bool(a.on) and bool(a.pixel_off)==bool(a.pixel_on)
paths=[a.off,a.on] if a.off else [Path(a.prefix+'-'+a.machine+'-'+str(i)) for i in (0,1)]
pixel_paths=[a.pixel_off,a.pixel_on] if a.pixel_off else paths
read=lambda p,n:json.loads((p/n).read_text())
def active_normal(path):
 s=(path/'state.bin').read_bytes()
 assert struct.unpack_from('>H',s,0x7ffe-188)[0]==10
 assert struct.unpack_from('>H',s,0x7ffe-0x15fa)[0]==10 and s[0x7ffe-0x173a]==10
# vasm source listings prove the pixel fixture leaves production assembly and
# conditional emission unchanged. PC displacements/padding can differ by layout.
def production_listing(path):
 source=None;lines=[]
 for line in (path/'slave.lst').read_text(encoding='latin1').splitlines():
  match=re.match(r'Source: "([^"]+)"',line)
  if match:source=match[1]
  if source not in {'performance.s','geometry.s','math.s','bookkeeping.s'}:continue
  match=re.search(r'\t\s*\d+: (.*)',line)
  if match and not match[1].lstrip().startswith('CNOP'):
   lines.append((source,match[1],bool(re.match(r'00:[0-9A-F]+ [0-9A-F]+',line))))
 return lines
meta=[read(p,'anchor.json') for p in paths];pm=[read(p,'anchor.json') for p in pixel_paths]
assert meta[0]['slave_sha256']==meta[1]['slave_sha256']
assert pm[0]['slave_sha256']==pm[1]['slave_sha256']
assert all(m['graphics_level']==0 and m['simulation']=='Normal' and m['frame']==10 for m in meta+pm)
assert [m['settings']['WHD_ARGS'] for m in meta]==['CUSTOM2=0','CUSTOM2=1']
assert {k:v for k,v in meta[0]['settings'].items() if k!='WHD_ARGS'}=={k:v for k,v in meta[1]['settings'].items() if k!='WHD_ARGS'}
for t,v,tm,vm in zip(paths,pixel_paths,meta,pm):
 assert tm['settings']==vm['settings'];active_normal(t);active_normal(v)
 assert production_listing(t)==production_listing(v),'Production assembly/emission differs'
assert all(read(p,'capture.json')['parts']==[100,100,50] for p in paths)
pixels=read(pixel_paths[1],'pixel-comparison.json')
assert pixels['off_capture']==str(pixel_paths[0]) and pixels['on_capture']==str(pixel_paths[1])
assert pixels['all_output_bytes_equal'] and len(pixels['matching_primitive_pairs'])==16
assert all(len(read(p,'draw-pixels/results.json'))==4 for p in pixel_paths)
assert all(all(v['primitives']==40 for v in read(p,'draw-pixels/results.json')) for p in pixel_paths)
fps=[read(p,'display-check.json')['validated_fps_within_contiguous_parts'] for p in paths]
irq=[read(p,'w1-trace.json') for p in paths]
r={'machine':a.machine,'timing_build':meta[0]['slave_sha256'],'pixel_build':pm[0]['slave_sha256'],'production_assembly_and_emission_equal':True,'fps_off_on':fps,'fps_increase_percent':100*(fps[1]/fps[0]-1),'blit_entries_off_on':[v['counts']['blit_entries'] for v in irq],'guest_level3_cycles_off_on':[sum(v['guest_level3_cycles'].values()) for v in irq],'fields_each':250,'timing_evidence':[str(p) for p in paths],'pixel_evidence':[str(p) for p in pixel_paths],'scope':'Stationary starting scene, FULL and verified active Normal. Timing uses the same slave and machine, changing only CUSTOM2; complete display intervals within independent 100/100/50-field parts. Separate pixel captures match 40 primitives and 32000 output bytes across 16 pairs; initial bitmaps differ. A differing pixel-build hash denotes the VERIFY-only native WaitBlit checkpoint, absent from timing. Production assembly and conditional emission match. This is scene-specific, not a moving-race benchmark.'}
Path(a.prefix+'-'+a.machine+'-comparison.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
