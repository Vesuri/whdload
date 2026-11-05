from pathlib import Path
import sys,json,struct,hashlib
sys.path.insert(0,str(Path(__file__).parent));from compare_step2 import FIELDS
r=Path(__file__).resolve().parents[1];d=r/'tmp/step4';hz=49.9204102
blocks=[(n,a,48 if n=='segments_and_positions' else z) for n,a,z in FIELDS]+[('resident_settings',0x1bde8,1700),('resident_globals',0x1c498,25432),('car_work',0x32f18,180),('race_condition_and_status',0x66be0,0x9c),('boost_sound_controls',0x6bf70,20),('engine_data',0x6ef28,432),('engine_work',0x6f0e0,416)]
def world(b):return {n:b[a:a+z].hex() for n,a,z in blocks}
def clock(b,a):
 v=b[a:a+10];return sum(x*w for x,w in zip(v[3:],(360000,36000,6000,600,100,10,1)))
def field(b):return struct.unpack_from('>H',b,0x24ad2)[0]
def mismatches(a,b):return [n for n in a if a[n]!=b[n]]
out={'scope':'68000, 68020, 68020+Fast; PAL; native no-input demo except explicitly labeled synthetic contact and ESC boundary checks','semantic_blocks':[{'name':n,'address':hex(a),'bytes':z} for n,a,z in blocks],'projection_exclusion':{'address':'0x6a63a','bytes':48,'reason':'Draw projection/sort workspace, referenced by race hunks 170,195,197; not authoritative segment/lateral/longitudinal arrays at 0x6a60a..0x6a639.'},'runs':{},'comparisons':{}}
accepted={f'{p}-{arm}' for p in ('a500','a1200','a1200-fast') for arm in ('c0','c1','control-v2','slow-v2','logic-v2','contact3-control','contact3-logic')}
for p in d.iterdir():
 if p.name not in accepted:continue
 if not p.is_dir() or not (p/'loop225.bin').exists():continue
 x=json.loads((p/'result.json').read_text()) if (p/'result.json').exists() else {}
 if x.get('status')!='complete':continue
 points={}
 for tick in (125,126,150,175,225):
  f=p/f'loop{tick}.bin'
  if f.exists():
   b=f.read_bytes();points[tick]={'field':field(b),'calendar_tenths':clock(b,0x226c0),'session_tenths':clock(b,0x226ca),'world':world(b),'sha256':hashlib.sha256(b).hexdigest()}
 a=points[125];b=points[225];elapsed=(b['field']-a['field'])%65536
 out['runs'][p.name]={'field_count':elapsed,'ms_per_update':elapsed/hz*10,'updates_per_second':100*hz/elapsed,'calendar_tenths':b['calendar_tenths']-a['calendar_tenths'],'session_tenths':b['session_tenths']-a['session_tenths'],'points':points}
 if 'contact' in p.name:out['runs'][p.name]['first_contact_tick_fields']=(points[126]['field']-a['field'])%65536
for p in ('a500','a1200','a1200-fast'):
 pairs=[(f'{p}-c0',f'{p}-c1'),(f'{p}-control-v2',f'{p}-slow-v2'),(f'{p}-control-v2',f'{p}-logic-v2'),(f'{p}-contact3-control',f'{p}-contact3-logic')]
 for a,b in pairs:
  if a not in out['runs'] or b not in out['runs']:continue
  checks={str(t):mismatches(out['runs'][a]['points'][t]['world'],out['runs'][b]['points'][t]['world']) for t in out['runs'][a]['points'] if t in out['runs'][b]['points']}
  out['comparisons'][a+' vs '+b]=checks
  print(a,'vs',b,checks)
for n,v in out['runs'].items():
 print(n,round(v['ms_per_update'],3),v['calendar_tenths'],v['session_tenths'])
(r/'manifest/step4-measurements.json').write_text(json.dumps(out,indent=2)+'\n')
