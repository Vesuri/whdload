from pathlib import Path
import json,struct,sys,hashlib
r=Path(__file__).resolve().parents[1];profile=sys.argv[1] if len(sys.argv)>1 else 'a500';p=r/f'tmp/step5/c4-q02-work-v2-{profile}-candidate';j=json.loads((p/'result.json').read_text());cases=json.loads((r/'manifest/step5-c4-q02-work-v2-cases.json').read_text())['cases'];b=(p/'results.bin').read_bytes();assert len(b)==len(cases)*40;checks=[]
for i,c in enumerate(cases):
 kind=c['kind'];v=c['value'];pos=[10,0x1234,-3,100,0x5678,2];vel=[7,0x789a,200,0xbcde,-4,4];speed=[50,0x1111,3];native=[10,100,7,200,50]
 if kind.startswith('offroad'):
  axis=1 if kind=='offroad_z' else 0;rate=-v if axis else 30 if kind=='offroad_right' else -30;vel[axis*2]+=2*rate;vel[4:6]=[0,0];native[2]=vel[0];native[3]=vel[2]
 elif kind.startswith('p'):
  axis=0 if kind.startswith('px') else 1;value=0 if kind.endswith('zero') else 350 if kind.endswith('350') else v;pos[axis*3]=value;native[axis]=value
  if not kind.endswith('sync'):pos[axis*3+1:axis*3+3]=[0,0]
 elif kind in ('vx_reset','vz_reset'):
  axis=0 if kind.startswith('vx') else 1;native[2+axis]=v;vel=[native[2],0,native[3],0,0,0]
 elif kind=='vz_clamp':native[3]=v;vel[2:4]=[v,0];vel[5]=0
 else:
  value=100 if kind=='speed_100' else v;speed=[value,0,0];native[4]=value
 expected=struct.pack('>20H',*[x&65535 for x in pos+vel+speed+native]);row=b[i*40:(i+1)*40];checks.append(dict(c,passed=row==expected,expected=expected.hex(),actual=row.hex()))
passed=all(c['passed'] for c in checks) and j['state']['error']==0 and j['state']['C1Completed']-j['start']['C1Completed']==20
out={'status':'passed' if passed else 'failed','profile':profile,'cases':checks,'slave_sha256':j['slave_sha256'],'scope':'432 installed working-state writer cases; independent native/shadow reset/clamp/sync expectations, every non-target car unchanged, 20 subsequent ordinary updates.'};(r/f'manifest/step5-c4-q02-work-v2-{profile}.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'],[c for c in checks if not c['passed']][:4]);assert passed
