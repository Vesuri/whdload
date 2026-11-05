from pathlib import Path
import json,struct,hashlib,sys
r=Path(__file__).resolve().parents[1];profile=sys.argv[1] if len(sys.argv)>1 else 'a500';p=r/f'tmp/step5/c4-q02-contact-{profile}-candidate';j=json.loads((p/'result.json').read_text());data=(p/'results.bin').read_bytes();cases=json.loads((r/'manifest/step5-c4-q02-contact-cases.json').read_text())['cases'];assert len(data)==56*260
# Retained original native full-contact outputs from the independently seeded
# 100 ms control; these exercise the same native routine and input arrays.
control=r/'tmp/step5/native-velocity-contact-a1200-control';cj=json.loads((control/'result.json').read_text());assert cj['status']=='complete'
reference=(control/'results.bin').read_bytes();assert len(reference)==56*148
assert cj['slave_sha256']==hashlib.sha256((r/'tmp/build/step5-native-velocity-contact/control.slave').read_bytes()).hexdigest()
checks=[]
for i,c in enumerate(cases):
 row=data[i*260:(i+1)*260];old=reference[i*148:(i+1)*148];a=c['first'];b=c['second'];front=c['front'];dst=b if front else a;src=a if front else b
 vel=bytearray();pos=bytearray()
 for car in range(8):
  speed=120 if car==src else 100
  vel+=struct.pack('>IIhh',256+car*257,(speed<<16)+512+car*513,car-4,4-car)
  pos+=struct.pack('>hHhhHh',0,256+car*257,car-4,101 if car==dst else 100,512+car*513,car-4)
 assert old[:96]==vel
 seed=bytes(vel)
 for off,n in ((4,4),(10,2)):
  vel[a*12+off:a*12+off+n]=seed[b*12+off:b*12+off+n];vel[b*12+off:b*12+off+n]=seed[a*12+off:a*12+off+n]
 pos[dst*12+6:dst*12+8]=old[96+dst*2:98+dst*2];pos[dst*12+8:dst*12+12]=pos[src*12+8:src*12+12]
 for car in range(8):vel[car*12:car*12+2]=row[244+car*2:246+car*2]
 checks.append(dict(c,native_exact=row[96:144]==old[96:144],velocity_exact=row[:96]==vel,position_exact=row[148:244]==pos))
passed=all(all(c[k] for k in ('native_exact','velocity_exact','position_exact')) for c in checks) and j['state']['error']==0 and j['state']['C1Completed']-j['start']['C1Completed']==20
report={'status':'passed' if passed else 'failed','profile':profile,'scope':'All 28 native car pairs in both contact directions; independently seeded velocity exchange, native sideways impulse ownership and position tail assignment, original native reference arrays, restoration then 20 ordinary updates.','reference_slave_sha256':cj['slave_sha256'],'candidate_slave_sha256':j['slave_sha256'],'cases':checks}
(r/f'manifest/step5-c4-q02-contact-{profile}.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],[c for c in checks if not all(c[k] for k in ('native_exact','velocity_exact','position_exact'))][:4]);assert passed
