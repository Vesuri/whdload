#!/usr/bin/env python3
"""Check all three coherent A4000 positions against frozen native-family bands."""
import json,hashlib,struct,sys
from pathlib import Path
from simulation_fixture import read_fixture
root=Path('tmp/prof');path=root/'native-contact-phase-criteria.json';digest=hashlib.sha256(path.read_bytes()).hexdigest();assert digest=='74afe3d039870269ccf4d160434ec52f05fe195dfb8dc6c338a3aeca613d64ce';criteria=json.loads(path.read_text())
nominal,minus,plus=sys.argv[1:];initial=read_fixture(root/nominal,'bridge-end.bin')[0][2]
def flights(rows):
 result=[];block=[]
 for r in rows:
  if not any(r[f'w{i}'] for i in range(4)):block.append(r)
  elif block:
   result.append(dict(takeoff=block[0]['tick']/50,landing=r['tick']/50,peak_height=max(x['y'] for x in block),minimum_pitch=min(x['pitch'] for x in block),maximum_pitch=max(x['pitch'] for x in block)));block=[]
 assert not block
 return result
report={}
for delta,name in [(0,nominal),(-64,minus),(64,plus)]:
 p=root/name;d=json.loads((p/'bridge.json').read_text());assert d['rate']==50 and d['end']==800;rows=d['rows'];ix={r['tick']:r for r in rows}
 b=read_fixture(p,'bridge-end.bin')[0][2];expected=bytearray(initial);struct.pack_into('>i',expected,0x15a,struct.unpack_from('>i',initial,0x15a)[0]+delta)
 for i in range(4):
  off=0x152+0x78+6*i;v=struct.unpack_from('>h',initial,off)[0]+delta//64;struct.pack_into('>h',expected,off,(v+32768)%65536-32768)
 assert b==expected,(name,[(hex(i),x,y) for i,(x,y) in enumerate(zip(b,expected)) if x!=y])
 checks=[]
 for t,bands in criteria['common_bands'].items():
  r=ix[int(t)*5]
  for k,band in bands.items():
   v=r[k];checks.append(dict(kind='common',time=int(t)/10,field=k,actual=v,**band,passed=band['low']<=v<=band['high']))
 fs=flights(rows);checks += [dict(kind='outcome',field='two_flights',actual=len(fs),passed=len(fs)==2),dict(kind='outcome',field='crash_free',passed=not any(r['crash'] for r in rows)),dict(kind='outcome',field='ends_grounded',passed=rows[-1]['contact']==4)]
 for i,(f,bands) in enumerate(zip(fs,criteria['flight_bands'])):
  for k,band in bands.items():
   v=f[k];passed=band['low']<=v+1e-8 and v-(.02 if k in ('takeoff','landing') else 0)<=band['high']+1e-8
   checks.append(dict(kind='flight',flight=i,field=k,actual=v,low=band['low'],high=band['high'],passed=passed))
 failed=[c for c in checks if not c['passed']];r=dict(capture=name,initial_z_delta=delta,initial1510_bytes_verified=True,criteria_sha256=digest,passed=not failed,check_count=len(checks),failures=failed,flights=fs,scope='Additional native-family diagnostic only; original failed gates are not waived. Zero-shift results were already known at criterion freeze; perturbed cases were not.')
 (p/'contact-phase-check.json').write_text(json.dumps(r,indent=2)+'\n');report[str(delta)]=r
path=root/(nominal+'-phase-family.json');path.write_text(json.dumps(report,indent=2)+'\n')
for delta,r in report.items():
 summary={}
 for c in r['failures']:
  key=c['kind']+':'+c['field'];summary[key]=summary.get(key,0)+1
 print(delta,r['passed'],summary)
