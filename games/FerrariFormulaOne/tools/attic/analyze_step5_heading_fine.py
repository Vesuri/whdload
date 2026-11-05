from pathlib import Path
import json,struct,hashlib
r=Path(__file__).resolve().parents[1];blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[{'name':'gear_display_transition','address':'0x6bf84','bytes':4}]
report={'scope':'Native controls and position and heading 1/5 increment diagnostic. Forces/velocity/other timing remain native; NOT 20 ms gameplay or performance acceptance.','profiles':{}}
for profile in ('a1200','a1200-fast'):
 paths=[r/'tmp/step5'/(profile+'-heading-fine-'+v) for v in ('control','bridge','heading')]
 if not all((p/'result.json').exists() for p in paths):continue
 results=[json.loads((p/'result.json').read_text()) for p in paths]
 if not all(x['status']=='complete' for x in results):continue
 for variant,result in zip(('control','bridge','heading'),results):
  expected=hashlib.sha256((r/'tmp/build/step5-heading-fine'/(variant+'.slave')).read_bytes()).hexdigest()
  assert result.get('slave_sha256')==expected,(profile,variant,'stale capture')
 comparisons={}
 for tick in (125,150,175,225):
  data=[(p/f'loop{tick}.bin').read_bytes() for p in paths[:2]]
  comparisons[tick]=[b['name'] for b in blocks if data[0][int(b['address'],16):int(b['address'],16)+b['bytes']]!=data[1][int(b['address'],16):int(b['address'],16)+b['bytes']]]
 raw=(paths[2]/'fine-records.bin').read_bytes();failures=[];cars=[0]*8;clamps=0;nonzero=0
 for i in range(800):
  rec=raw[i*32:(i+1)*32];car,flag,vx,vz=struct.unpack_from('>HHhh',rec);cars[car]+=1
  expected=bytearray();clamped=0
  for axis,v in enumerate((vx,vz)):
   before,rem=struct.unpack_from('>ih',rec,8+axis*6)
   total=(v<<16)+rem;q=(abs(total)//5)*(1 if total>=0 else -1);newrem=total-q*5;position=before+q
   if axis==1 and position*5+newrem<0:position=0;newrem=0;clamped=1
   expected+=struct.pack('>ih',position,newrem)
   if position&65535 or newrem:nonzero+=1
  clamps+=clamped
  if rec[20:]!=expected or flag!=clamped:failures.append({'record':i,'car':car,'actual':rec.hex(),'expected':expected.hex(),'expected_clamp':clamped})
 shadow=(paths[2]/'shadow.bin').read_bytes();state=(paths[2]/'loop225.bin').read_bytes()
 final_ok=all(shadow[c*12:c*12+2]==state[0x6a61a+c*2:0x6a61c+c*2] and shadow[c*12+6:c*12+8]==state[0x6a62a+c*2:0x6a62c+c*2] for c in range(8))
 remainder_ok=all(-4<=struct.unpack_from('>h',shadow,c*12+axis*6+4)[0]<=4 for c in range(8) for axis in range(2))
 row={'native_controls_exact':not any(comparisons.values()),'control_mismatches':comparisons,'integrated_records':800,'per_car':cars,'record_failures':failures,'nonzero_axis_outputs':nonzero,'longitudinal_clamps':clamps,'final_integer_states_match':final_ok,'final_remainders_in_range':remainder_ok,'probe':results[2]['probe']}
 heading_raw=(paths[2]/'heading-records.bin').read_bytes();heading_failures=[];heading_counts=[[0,0] for _ in range(8)]
 for i in range(len(heading_raw)//24):
  car,axis,inc,before,rem,pad,after,newrem,status=struct.unpack_from('>HHiIhHIhH',heading_raw,i*24)
  heading_counts[car][axis]+=1
  total=inc+rem;q=(abs(total)//5)*(1 if total>=0 else -1)
  if after!=(before+q)&0xffffffff or newrem!=total-q*5 or status!=0 or pad!=0:heading_failures.append(i)
 hs=(paths[2]/'heading-shadow.bin').read_bytes()
 heading_final=all(hs[c*12+axis*6:c*12+axis*6+4]==state[base+c*4:base+c*4+4] for c in range(8) for axis,base in enumerate((0x2278a,0x227aa)))
 heading_remainders=all(-4<=struct.unpack_from('>h',hs,c*12+axis*6+4)[0]<=4 for c in range(8) for axis in range(2))
 row.update(heading_records=len(heading_raw)//24,heading_per_car=heading_counts,heading_record_failures=heading_failures,heading_final_matches=heading_final,heading_remainders_in_range=heading_remainders)
 row['passed']=row['native_controls_exact'] and not failures and final_ok and remainder_ok and cars==[100]*8 and nonzero>0 and row['probe']['error']==0 and row['probe']['bridge_rotations']>0 and not heading_failures and heading_final and heading_remainders and heading_counts==[[100,100]]*8
 report['profiles'][profile]=row;print(profile,json.dumps(row)[:3500])
report['status']='passed' if len(report['profiles'])==2 and all(x['passed'] for x in report['profiles'].values()) else 'incomplete_or_failed'
(r/'manifest/step5-heading-fine-validation.json').write_text(json.dumps(report,indent=2)+'\n')
