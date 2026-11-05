from pathlib import Path
import json,struct,hashlib
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/step5-b5-scalar-hooks-v5-fixed';cases=json.loads((b/'cases.json').read_text());report={'profiles':{},'scope':'All ten scalar and four heading hook entries, 80 boundary cases per arm. Exact VERIFY/lean result, all D0-D7/A0-A6 values, CCR and carried state; independent arithmetic expectations.'}
for profile in ('a1200','a1200-fast'):
 data=[]
 for variant in ('verify','lean'):
  p=r/f'tmp/step5/b5-scalar-hooks-v5-fixed-{profile}-{variant}';result=json.loads((p/'result.json').read_text());assert result['status']=='complete';assert result['slave_sha256']==hashlib.sha256((b/(variant+'.slave')).read_bytes()).hexdigest();data.append((p/'results.bin').read_bytes())
 failures=[]
 for i,c in enumerate(cases):
  raw=data[1][i*72:(i+1)*72];regs=struct.unpack_from('>15I',raw,2);heading=c.get('kind')=='heading';d0=c['proposal']&0xffffffff if heading else c['expected_speed'];expected_regs=[d0]+[0x10101010+k for k in range(1,8)]+[0x20202020+k for k in range(7)]
  q,rem=struct.unpack_from('>Ih',raw,62);native=struct.unpack_from('>I' if heading else '>H',raw,68)[0];word=c['proposal']&65535;ccr=20 if heading else 16+(4 if word==0 else 8 if word&32768 else 0)
  if raw!=data[0][i*72:(i+1)*72] or list(regs)!=expected_regs or q!=c['expected_q16'] or rem!=c['expected_rem'] or native!=(q if heading else c['expected_speed']) or struct.unpack_from('>H',raw)[0]&31!=ccr:failures.append(dict(index=i,case=c,verify_exact=raw==data[0][i*72:(i+1)*72],registers_exact=list(regs)==expected_regs,q=q,rem=rem,native=native,ccr=struct.unpack_from('>H',raw)[0],expected_ccr=ccr))
 report['profiles'][profile]=dict(passed=not failures,cases=len(cases),failures=failures);print(profile,len(failures),'failures',failures[:2])
report['status']='passed' if all(x['passed'] for x in report['profiles'].values()) else 'failed';(r/'manifest/step5-b5-hook-validation.json').write_text(json.dumps(report,indent=2)+'\n');assert report['status']=='passed'
