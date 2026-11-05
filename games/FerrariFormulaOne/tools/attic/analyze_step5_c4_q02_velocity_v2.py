from pathlib import Path
import json,struct,sys,hashlib
r=Path(__file__).resolve().parents[1];kind='velocity-v2';profile=sys.argv[1] if len(sys.argv)>1 else 'a500'
cases=json.loads((r/f'manifest/step5-c4-q02-{kind}-cases.json').read_text());p=r/f'tmp/step5/c4-q02-{kind}-{profile}-candidate';j=json.loads((p/'result.json').read_text());data=(p/'results.bin').read_bytes();assert len(data)==len(cases['cases'])*cases['record_size'];checks=[]
for i,c in enumerate(cases['cases']):
 car=c['car'];op=c['operation'];row=data[i*cases['record_size']:(i+1)*cases['record_size']]
 if kind=='position':
  if op=='snapshot':
   shadow=bytearray(b''.join(struct.pack('>hHhhHh',10,256+k*257,k-4,100,512+k*513,k-4) for k in range(8)));saved=bytearray(struct.pack('>hHh',50,0x1234,2)*8)
   x=[10]*8;z=[100]*8;ns=[50]*8;ns[car]=100;saved[car*6:car*6+6]=shadow[car*12+6:car*12+12]
  elif op=='restore':shadow[car*12+6:car*12+12]=saved[car*6:car*6+6]
  else:
   axis,value={'init_x_111':(0,111),'init_z_222':(1,222),'init_x_333':(0,333),'init_x_444':(0,444),'zero_z':(1,0)}[op];off=car*12+axis*6;shadow[off:off+6]=struct.pack('>hHH',value,0,0);(z if axis else x)[car]=value
  expected=shadow+saved+struct.pack('>24h',*(x+z+ns))
 else:
  expected=bytearray(b''.join(struct.pack('>IIhh',256+k*257,(200<<16)+512+k*513,k-4,4-k) for k in range(8)));native=bytearray(bytes(16)+struct.pack('>8h',*([200]*8)))
  axes=() if op.startswith('speed') else (0,1) if op=='zero_both' else (0,) if op.startswith('zero_x') else (1,)
  for axis in axes:
   value=200 if op=='set_z200' else 0;expected[car*12+axis*4:car*12+axis*4+4]=struct.pack('>i',value<<16);expected[car*12+8+axis*2:car*12+10+axis*2]=bytes(2);native[axis*16+car*2:axis*16+car*2+2]=struct.pack('>h',value)
  expected+=native
  # Lean C4 does not increment diagnostic cold-write counters.
  speed=bytearray(struct.pack('>hHh',100,0x1234,2)*8);nspeed=[100]*8
  if op.startswith('speed'):speed[car*6:car*6+6]=bytes(6);nspeed[car]=0
  expected+=speed+struct.pack('>8h',*nspeed)
  row=row[:128]+row[132:]
 checks.append(dict(c,passed=row==expected,actual_sha256=hashlib.sha256(row).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest()))
passed=all(c['passed'] for c in checks) and j['status']=='complete' and j['state']['error']==0 and j['state']['C1Completed']-j['start']['C1Completed']==20
out={'status':'passed' if passed else 'failed','kind':kind,'profile':profile,'scope':'Independent all-car native writer ownership model, including nonzero fractional/remainder tails and native arrays; subsequent 20 ordinary updates. Not full modal lifecycle.','cases':checks,'slave_sha256':j['slave_sha256']}
(r/f'manifest/step5-c4-q02-{kind}-{profile}.json').write_text(json.dumps(out,indent=2)+'\n');print(kind,profile,out['status'],[c for c in checks if not c['passed']][:3]);assert passed
