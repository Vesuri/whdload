from pathlib import Path
import json,struct,math
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5/c4-boundary-p5-v3-ab-a500-candidate-replay';j=json.loads((p/'result.json').read_text());state=(p/'start.bin').read_bytes();v=json.loads((p/'velocity.json').read_text());pos=json.loads((p/'position.json').read_text());bad=[];vc=[0]*8;pc=[0]*8
s16=lambda x:(x+32768)%65536-32768
s32=lambda x:(x+2**31)%2**32-2**31
trunc=lambda n,d:(abs(n)//d)*(-1 if n<0 else 1)
def i(data,off=0):return struct.unpack_from('>i',data,off)[0]
def h(data,off=0):return struct.unpack_from('>h',data,off)[0]
for n,row in enumerate(v):
 car=row['car'];vc[car]+=1;b=bytes.fromhex(row['scratch']);before=bytes.fromhex(row['shadow_before']);after=bytes.fromhex(row['shadow_after']);speed=bytes.fromhex(row['speed_after']);native=bytes.fromhex(row['native_velocity']);angle=row['angle']&1023
 sn=h(state,0x2180c+2*angle);co=h(state,0x21a0c+2*angle);target=(s32(row['speed_input'])*sn//32768,s32(row['speed_input'])*co//32768)
 old=(i(before),i(before,4));delta=tuple((t-o)//2-h(before,8+axis*2) for axis,(t,o) in enumerate(zip(target,old)))
 body=((delta[0]*co-delta[1]*sn)//32768,(delta[0]*sn+delta[1]*co)//32768);raw=tuple(s16(x>>16) for x in body);mag=math.isqrt(sum(x*x for x in raw));limit=h(b,38)
 limited=tuple(trunc(x*limit,mag) if mag else 0 for x in raw);inv=s16(-sn)
 response=(((limited[0]<<16)*co-(limited[1]<<16)*inv)//32768,((limited[0]<<16)*inv+(limited[1]<<16)*co)//32768)
 new=tuple(x+2*y for x,y in zip(old,response));norm=math.isqrt(sum(x*x for x in new));expected_speed=0 if norm<4*65536 else min(norm,500*65536)
 if expected_speed==0:new=(0,0)
 checks={'projection':(i(b,24),i(b,28))==target,'history':(i(b,40),i(b,44))==old and b[48:52]==before[8:12],'normalized_body':(i(b,52),i(b,56))==body,'raw_magnitude':(h(b,32),h(b,34),h(b,36))==(*raw,mag),'limited':(h(b,20),h(b,22))==limited and limit>=0,'response':(i(b,60),i(b,64))==response,'new_velocity':(i(b,68),i(b,72))==new and (i(after),i(after,4))==new,'zero_carry':b[76:80]==bytes(4) and after[8:12]==bytes(4),'speed':i(speed)==expected_speed and speed[4:]==bytes(2),'native_words':(h(native),h(native,2))==tuple(s16(x>>16) for x in new)}
 if not all(checks.values()):bad.append({'kind':'velocity','record':n,'car':car,'checks':checks})
for n,row in enumerate(pos):
 car=row['car'];pc[car]+=1;a=bytes.fromhex(row['shadow_before']);z=bytes.fromhex(row['shadow_after']);vel=bytes.fromhex(row['velocity']);native=bytes.fromhex(row['native_before']);end=bytes.fromhex(row['native_after']);expected=[]
 for axis in range(2):
  before=h(native,6+axis*2)*65536+(i(a,axis*6)&65535);value=before+2*i(vel,axis*4)
  if axis==1:value=max(0,value)
  expected.append(value)
 okay=(i(z),i(z,6))==tuple(expected) and z[4:6]==z[10:12]==bytes(2) and (h(end,6),h(end,8))==tuple(s16(x>>16) for x in expected)
 if not okay:bad.append({'kind':'position','record':n,'car':car,'expected':expected,'actual':[i(z),i(z,6)]})
passed=j['status']=='complete' and j['updates']==100 and j['error']==0 and vc==pc==[100]*8 and not bad
out={'status':'passed' if passed else 'failed','scope':'Independent integer replay of observed integrated projection, normalized body derivative, native limiter, inverse response rotation, doubled velocity integration, magnitude/stop/clamp, native velocity publication and doubled position integration with native integer rebasing. All eight cars, 100 updates. Does not establish unobserved event/contact/transition correctness.','velocity_records':len(v),'position_records':len(pos),'velocity_per_car':vc,'position_per_car':pc,'failures':bad[:30],'slave_sha256':j['slave_sha256']}
(r/'manifest/step5-c4-motion-replay-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));assert passed
