from pathlib import Path
import json,struct,hashlib,math
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/step5-velocity-ownership'
blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[{'name':'gear_display_transition','address':'0x6bf84','bytes':4}]
report={'scope':'Native-step velocity observation and Q16 projection; not fractional velocity ownership, adapted physics or timing acceptance','profiles':{}}
def w(x):return ((x+32768)&65535)-32768
for profile in ('a1200','a1200-fast'):
 paths=[r/'tmp/step5'/(profile+'-velocity-ownership-'+v) for v in ('control','bridge')]
 if not all((p/'result.json').exists() for p in paths):continue
 results=[json.loads((p/'result.json').read_text()) for p in paths]
 if not all(d.get('status')=='complete' and d.get('slave_sha256')==hashlib.sha256((b/(v+'.slave')).read_bytes()).hexdigest() for d,v in zip(results,('control','bridge'))):continue
 mismatches={}
 for tick in (125,150,175,225):
  data=[(p/f'loop{tick}.bin').read_bytes() for p in paths]
  mismatches[tick]=[x['name'] for x in blocks if data[0][int(x['address'],16):int(x['address'],16)+x['bytes']]!=data[1][int(x['address'],16):int(x['address'],16)+x['bytes']]]
 state=(paths[1]/'loop225.bin').read_bytes();raw=(paths[1]/'velocity_records.bin').read_bytes();shadow=(paths[1]/'velocity_shadow.bin').read_bytes()
 assert len(raw)==32000 and len(shadow)==96
 failures=[];cars=[0]*8;max_delta=0;max_raw=0;max_response=0;fractions=0
 for i in range(800):
  car,angle,speed,outspd,ox,oz,tx,tz,fx,fz,lx,lz,qx,qz,rx,rz,mag,pad=struct.unpack_from('>H11h2i4h',raw,i*40)
  cars[car]+=1;s,c=[struct.unpack_from('>h',state,base+(angle&1023)*2)[0] for base in (0x2180c,0x21a0c)]
  expected_q=(speed*s*2,speed*c*2);expected_native=(w(speed*s//32768),w(speed*c//32768))
  dx,dz=w(tx-ox),w(tz-oz);ex=w(w(dx*c//32768)-w(dz*s//32768));ez=w(w(dx*s//32768)+w(dz*c//32768))
  projected=(qx,qz)==expected_q and (tx,tz)==expected_native
  raw_ok=(rx,rz)==(ex,ez) and mag==min(math.isqrt(ex*ex+ez*ez),1023)
  nx=w(ox+w(w(lx*c//32768)+w(lz*s//32768)));nz=w(oz-w(lx*s//32768)+w(lz*c//32768))
  norm=min(math.isqrt(nx*nx+nz*nz),1023);expected_speed=min(norm,500)
  if norm<4:nx=nz=expected_speed=0
  response_ok=(fx,fz,outspd)==(nx,nz,expected_speed)
  if not projected or not raw_ok or not response_ok or pad!=0:failures.append({'record':i,'projection':projected,'raw':raw_ok,'response':response_ok,'actual':[fx,fz,outspd],'expected':[nx,nz,expected_speed]})
  max_delta=max(max_delta,abs(dx),abs(dz));max_raw=max(max_raw,abs(rx),abs(rz));max_response=max(max_response,abs(lx),abs(lz));fractions+=bool(qx&65535)+bool(qz&65535)
 shadow_ok=all(struct.unpack_from('>i',shadow,car*12+axis*4)[0]==struct.unpack_from('>h',state,base+car*2)[0]*65536 for car in range(8) for axis,base in enumerate((0x6f13c,0x6f14c)))
 probe=results[1]['probe'];passed=not any(mismatches.values()) and not failures and shadow_ok and cars==[100]*8 and all(probe[k]==800 for k in ('velocity_loads','velocity_stores','velocity_projects','velocity_raws','velocity_records_count')) and probe['velocity_rotations']>0 and probe['error']==0
 row={'passed':passed,'native_states_exact':not any(mismatches.values()),'mismatches':mismatches,'records':800,'per_car':cars,'failures':failures,'shadow_matches_native':shadow_ok,'max_native_component_delta':max_delta,'max_raw_body_component':max_raw,'max_limited_body_component':max_response,'fractional_projected_components':fractions,'probe':probe}
 report['profiles'][profile]=row;print(profile,json.dumps(row)[:3000],flush=True)
report['status']='passed' if len(report['profiles'])==2 and all(x['passed'] for x in report['profiles'].values()) else 'incomplete_or_failed'
(r/'manifest/step5-velocity-ownership-validation.json').write_text(json.dumps(report,indent=2)+'\n')
