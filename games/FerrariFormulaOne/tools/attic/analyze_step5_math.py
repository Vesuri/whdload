from pathlib import Path
import json,struct,hashlib
r=Path(__file__).resolve().parents[1];root=r/'tmp/step5';hz=3546895/71051
blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[{'name':'gear_display_transition','address':'0x6bf84','bytes':4}]
out={'scope':'100 completed native demo loops; no drawing; not adapted physics or playable FPS','pal_hz':hz,'runs':{},'comparisons':{}}
for p in sorted(root.glob('*-math-v[23456]-*')):
 if not (p/'result.json').exists():continue
 report=json.loads((p/'result.json').read_text())
 if report.get('status')!='complete':continue
 points={}
 for tick in (125,150,175,225):
  b=(p/f'loop{tick}.bin').read_bytes()
  points[str(tick)]={'field':struct.unpack_from('>H',b,0x24ad2)[0],'sha256':hashlib.sha256(b).hexdigest(),'state':{k['name']:b[int(k['address'],16):int(k['address'],16)+k['bytes']].hex() for k in blocks}}
 fields=(points['225']['field']-points['125']['field'])%65536
 out['runs'][p.name]={'fields':fields,'ms_per_loop':fields/hz*10,'probe':report['probe'],'points':points}
for name,run in out['runs'].items():
 variant=name.rsplit('-',1)[-1]
 control=name.rsplit('-',1)[0]+('-cache' if '-v5-' in name else '-control')
 if name==control or control not in out['runs']:continue
 ref=out['runs'][control];checks={t:[k for k,v in point['state'].items() if v!=ref['points'][t]['state'][k]] for t,point in run['points'].items()}
 out['comparisons'][control+' vs '+name]={'mismatches':checks,'exact':not any(checks.values()),'whole_loop_reduction_percent':100*(1-run['ms_per_loop']/ref['ms_per_loop'])}
 print(name,round(run['ms_per_loop'],3),'ms',round(out['comparisons'][control+' vs '+name]['whole_loop_reduction_percent'],2),'% saved','exact',not any(checks.values()))
(r/'manifest/step5-math-measurements.json').write_text(json.dumps(out,indent=2)+'\n')
