#!/usr/bin/env python3
"""Verify coherent initial changes and measure native contact-phase sensitivity."""
import json,struct,sys
from pathlib import Path
from simulation_fixture import read_fixture
root=Path('tmp/prof');rates=[int(x) for x in sys.argv[1:]] or [10,20];report={}
def intervals(rows,hz):
 result=[];start=None;block=[]
 for r in rows:
  air=not any(r[f'w{i}'] for i in range(4))
  if air:
   if start is None:start=r['tick'];block=[]
   block.append(r)
  elif start is not None:
   result.append(dict(takeoff=start/hz,landing=r['tick']/hz,peak_height=max(x['y'] for x in block),minimum_pitch=min(x['pitch'] for x in block),maximum_pitch=max(x['pitch'] for x in block)));start=None
 assert start is None
 return result
for hz in rates:
 basepath=root/f'natural-crest{hz}';base=json.loads((basepath/'bridge.json').read_text());ix={r['tick']:r for r in base['rows']};initial=read_fixture(basepath,'bridge-end.bin')[0][2]
 runs={}
 for delta,name in [(0,f'natural-crest{hz}'),(-64,f'phase-minus64-native{hz}'),(64,f'phase-plus64-native{hz}')]:
  p=root/name;d=json.loads((p/'bridge.json').read_text());assert d['rate']==hz and d['end']==16*hz
  candidate=read_fixture(p,'bridge-end.bin')[0][2];expected=bytearray(initial)
  struct.pack_into('>i',expected,0x15a,struct.unpack_from('>i',initial,0x15a)[0]+delta)
  for i in range(4):
   off=0x152+0x78+6*i;v=struct.unpack_from('>h',initial,off)[0]+delta//64;struct.pack_into('>h',expected,off,(v+32768)%65536-32768)
  assert candidate==expected,(name,[(hex(i),x,y) for i,(x,y) in enumerate(zip(candidate,expected)) if x!=y])
  rows=d['rows'];common=[r for r in rows if r['tick']>=9*hz and r['tick']%(hz//5)==0];assert len(common)==36
  errors={}
  for k in ('x','y','z','heading','pitch','roll','speed'):
   r=max(common,key=lambda r:abs(r[k]-ix[r['tick']][k]));errors[k]=dict(maximum=abs(r[k]-ix[r['tick']][k]),time=r['tick']/hz,candidate=r[k],reference=ix[r['tick']][k])
  flights=intervals(rows,hz);assert len(flights)==2 and not any(r['crash'] for r in rows) and rows[-1]['contact']==4
  runs[str(delta)]=dict(capture=name,initial1510_bytes_verified=True,changed_initial_bytes=sum(x!=y for x,y in zip(initial,candidate)),common_errors=errors,flights=flights,final=rows[-1],slave_sha256=d['slave_sha256'])
 report[str(hz)]=runs
report['scope']='Native physics only, same route and throttle; exactly one-cell coherent initialZ shifts. This characterizes sensitivity and does not waive any existing A4000 failed gate or establish a replacement tolerance.'
(root/'native-contact-phase-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({hz:{offset:r['common_errors'] for offset,r in runs.items() if offset!='0'} for hz,runs in report.items() if hz!='scope'},indent=2))
