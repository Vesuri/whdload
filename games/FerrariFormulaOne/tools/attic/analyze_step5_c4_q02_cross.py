from pathlib import Path
import sys,json,struct
r=Path(__file__).resolve().parents[1];profile=sys.argv[1] if len(sys.argv)>1 else 'a500';p=r/f'tmp/step5/c4-q02-cross-{profile}-candidate';j=json.loads((p/'result.json').read_text());cases=json.loads((r/'manifest/step5-c4-q02-cross-cases.json').read_text())['cases'];data=(p/'results.bin').read_bytes();assert len(data)==len(cases)*40
native=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes();h=lambda addr:struct.unpack_from('>h',native,addr)[0];s16=lambda x:(x+32768)%65536-32768;checks=[]
for i,c in enumerate(cases):
 vx=c['vx']*65536+0x4321;vz=500*65536+0x2345;x=10*65536+0x1234+2*vx;z=500*65536+0x5678+2*vz;segment=10;count=0;heading=0
 while True:
  angle=0 if c['pattern']==0 else 16 if c['pattern']==1 or segment%2==0 else -16
  sn=h(0x2180c+2*(angle&1023));co=h(0x21a0c+2*(angle&1023));ss=1000*sn//32768;cc=1000*co//32768
  assert cc>0
  if x*ss+z*cc<512*65536*cc:break
  nx=s16((s16(x>>16)*co//32768)-(s16((z>>16)-512)*sn//32768));nz=s16((s16(x>>16)*sn//32768)+(s16((z>>16)-512)*co//32768))
  fx=x&65535;fz=z&65535;x=nx*65536+(fx*co-fz*sn)//32768;z=nz*65536+(fx*sn+fz*co)//32768
  vx,vz=(vx*co-vz*sn)//32768,(vx*sn+vz*co)//32768
  heading=s16(heading-angle);segment+=1;count+=1;assert count<=64
 expected=struct.pack('>ihih2i2h8h',x,0,z,0,vx,vz,0,0,s16(x>>16),s16(z>>16),s16(vx>>16),s16(vz>>16),segment,count,heading,0)
 row=data[i*40:(i+1)*40];checks.append(dict(c,passed=row==expected,crossings=count,expected=expected.hex(),actual=row.hex()))
passed=all(c['passed'] and c['crossings']>=2 for c in checks) and j['state']['error']==0 and j['state']['C1Completed']-j['start']['C1Completed']==20
out={'status':'passed' if passed else 'failed','scope':'72 installed complete advance/boundary/native frame-transition loops, all cars; independent signed integer/Q16 model including native per-product rounding, tail rotation, velocity rotation, repeated predicate, segment count and heading. Restored state and 20 ordinary updates.','profile':profile,'cases':checks,'slave_sha256':j['slave_sha256']};(r/f'manifest/step5-c4-q02-cross-{profile}.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'],[c for c in checks if not c['passed']][:3]);assert passed
