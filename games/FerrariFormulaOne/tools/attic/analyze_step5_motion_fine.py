from pathlib import Path
import json,struct,hashlib,math
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/step5-motion-fine'
blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[{'name':'gear_display_transition','address':'0x6bf84','bytes':4}]
report={'scope':'Combined position/heading/velocity/scalar diagnostic. Persistent Q16 velocity with scalar continuous rates scaled to 20 ms. Scalar fractions persist across load/store and velocity feedback; events, wear and scheduler remain unconverted. Not 20 ms gameplay or capacity acceptance.','physics_accepted':False,'profiles':{}}
def w(x):return ((x+32768)&65535)-32768
for profile in ('a1200','a1200-fast'):
 paths=[r/'tmp/step5'/(profile+'-motion-fine-'+v) for v in ('control','bridge','fine')]
 if not all((p/'result.json').exists() for p in paths):continue
 results=[json.loads((p/'result.json').read_text()) for p in paths]
 if not all(d.get('status')=='complete' and d.get('slave_sha256')==hashlib.sha256((b/(v+'.slave')).read_bytes()).hexdigest() for d,v in zip(results,('control','bridge','fine'))):continue
 mismatches={}
 for tick in (125,150,175,225):
  data=[(p/f'loop{tick}.bin').read_bytes() for p in paths[:2]]
  mismatches[tick]=[x['name'] for x in blocks if data[0][int(x['address'],16):int(x['address'],16)+x['bytes']]!=data[1][int(x['address'],16):int(x['address'],16)+x['bytes']]]
 state=(paths[2]/'loop225.bin').read_bytes();raw=(paths[2]/'velocity_records.bin').read_bytes();shadow=(paths[2]/'velocity_shadow.bin').read_bytes()
 assert len(raw)==64000 and len(shadow)==96
 feedback=(paths[2]/'speed_feedback_records.bin').read_bytes()
 target_speeds=struct.unpack('>800i',(paths[2]/'velocity_target_speeds.bin').read_bytes())
 failures=[];cars=[0]*8;max_delta=0;max_raw=0;max_response=0;fractions=0;wide_magnitudes=0;wide_products=0;max_magnitude=0
 for i in range(800):
  car,angle,speed,outspd,ox,oz,tx,tz,fx,fz,lx,lz,qx,qz,rx,rz,mag,pad=struct.unpack_from('>H11h2i4h',raw,i*80)
  wide_magnitudes+=rx*rx+rz*rz>1023*1023
  wide_products+=any(not -32768<=v*pad<=32767 for v in (rx,rz))
  max_magnitude=max(max_magnitude,mag)
  cars[car]+=1;s,c=[struct.unpack_from('>h',state,base+(angle&1023)*2)[0] for base in (0x2180c,0x21a0c)]
  expected_q=(target_speeds[i]*s//32768,target_speeds[i]*c//32768);expected_native=(w(speed*s//32768),w(speed*c//32768))
  dx,dz=w(tx-ox),w(tz-oz);ex=w(w(dx*c//32768)-w(dz*s//32768));ez=w(w(dx*s//32768)+w(dz*c//32768))
  projected=(qx,qz)==expected_q and (tx,tz)==expected_native
  raw_ok=True  # Checked below against normalized fractional body values.
  nx=w(ox+w(w(lx*c//32768)+w(lz*s//32768)));nz=w(oz-w(lx*s//32768)+w(lz*c//32768))
  norm=min(math.isqrt(nx*nx+nz*nz),1023);expected_speed=min(norm,500)
  if norm<4:nx=nz=expected_speed=0
  response_ok=(fx,fz,outspd)==(nx,nz,expected_speed)
  if not projected:failures.append({'record':i,'projection':projected,'raw':raw_ok,'response':response_ok,'actual':[fx,fz,outspd],'expected':[nx,nz,expected_speed]})
  oldx,oldz,oldrx,oldrz,bx,bz,wx,wz,nqx,nqz,nrx,nrz=struct.unpack_from('>iihh6ihh',raw,i*80+40)
  dxq,dzq=5*(qx-oldx)-oldrx,5*(qz-oldz)-oldrz
  body_expected=((dxq*c-dzq*s)//32768,(dxq*s+dzq*c)//32768)
  response_expected=(((lx<<16)*c+(lz<<16)*s)//32768,(-(lx<<16)*s+(lz<<16)*c)//32768)
  expected_state=[]
  for before,rem,rate in zip((oldx,oldz),(oldrx,oldrz),response_expected):
   total=rate+rem;q=(abs(total)//5)*(1 if total>=0 else -1)
   expected_state.append((before+q,total-q*5))
  physical=[q*5+rem for q,rem in expected_state]
  norm5=math.isqrt(sum(v*v for v in physical));stopped=int(norm5<4*65536*5)
  if stopped:
   eqspeed=erspeed=0;expected_state=[(0,0),(0,0)]
  else:eqspeed,erspeed=divmod(min(norm5,500*65536*5),5)
  feedback_ok=struct.unpack_from('>ihh',feedback,i*8)==(eqspeed,erspeed,stopped)
  pipeline_ok=(oldx>>16,oldz>>16)==(ox,oz) and -4<=oldrx<=4 and -4<=oldrz<=4 and (bx,bz)==body_expected and (wx,wz)==response_expected and ((nqx,nrx),(nqz,nrz))==tuple(expected_state)
  pipeline_ok=pipeline_ok and feedback_ok and (rx,rz)==(bx>>16,bz>>16) and mag==math.isqrt(rx*rx+rz*rz) and (fx,fz)==(nqx>>16,nqz>>16) and outspd==eqspeed>>16
  def truncdiv(a,b):return (abs(a)//b)*(1 if a>=0 else -1)
  limited_expected=tuple(truncdiv(v*pad,mag) for v in (rx,rz)) if mag else (0,0)
  pipeline_ok=pipeline_ok and pad>=0 and (lx,lz)==limited_expected
  if not pipeline_ok:failures.append({'record':i,'fractional_pipeline':False})
  max_delta=max(max_delta,abs(dx),abs(dz));max_raw=max(max_raw,abs(rx),abs(rz));max_response=max(max_response,abs(lx),abs(lz));fractions+=bool(qx&65535)+bool(qz&65535)
 shadow_ok=all((struct.unpack_from('>i',shadow,car*12+axis*4)[0]>>16)==struct.unpack_from('>h',state,base+car*2)[0] for car in range(8) for axis,base in enumerate((0x6f13c,0x6f14c)))
 speed_shadow=(paths[2]/'speed_shadow.bin').read_bytes()
 scalar_shadow_ok=all(struct.unpack_from('>h',speed_shadow,car*6)[0]==struct.unpack_from('>h',state,0x2275a+car*2)[0] for car in range(8))
 probe=results[2]['probe']
 rate_bytes=(paths[2]/'speed_records.bin').read_bytes();rate_failures=[];rate_sites={};rate_clamps=0
 for i in range(probe['speed_records_count']):
  site,car,pad0,q,rem,newrem,proposal,newq,tick,pad1=struct.unpack_from('>IHHihhiiII',rate_bytes,i*32)
  total=(proposal-(q>>16))*65536+rem
  delta=(abs(total)//5)*(1 if total>=0 else -1);er=total-delta*5;eq=q+delta
  if eq*5+er<0:eq=er=0;rate_clamps+=1
  elif eq*5+er>500*65536*5:eq=500*65536;er=0;rate_clamps+=1
  okay=0<=q<=500*65536 and -4<=rem<=4 and (newq,newrem)==(eq,er) and car<8 and pad0==pad1==0
  if not okay:rate_failures.append({'record':i,'site':hex(site),'actual':[newq,newrem],'expected':[eq,er]})
  rate_sites[hex(site)]=rate_sites.get(hex(site),0)+1
 passed=scalar_shadow_ok and probe['speed_loads']==probe['speed_stores']==800 and not rate_failures and probe['speed_records_count']>0 and not any(mismatches.values()) and not failures and shadow_ok and cars==[100]*8 and all(probe[k]==800 for k in ('velocity_loads','velocity_stores','velocity_projects','velocity_raws','velocity_records_count')) and probe['velocity_rotations']>0 and probe['error']==0
 position_raw=(paths[2]/'fine_records.bin').read_bytes();position_inputs=(paths[2]/'position_velocity_inputs.bin').read_bytes();position_failures=[];position_counts=[0]*8
 for i in range(800):
  rec=position_raw[i*32:(i+1)*32];car,flag,vx,vz=struct.unpack_from('>HHhh',rec);position_counts[car]+=1
  vqx,vqz,vrx,vrz=struct.unpack_from('>iihh',position_inputs,i*12)
  expected=bytearray();clamped=0
  for axis,v,vr in ((0,vqx,vrx),(1,vqz,vrz)):
   before,rem=struct.unpack_from('>ih',rec,8+axis*6)
   total=5*v+vr+rem;q=(abs(total)//25)*(1 if total>=0 else -1);nr=total-q*25;pos=before+q
   if axis==1 and pos*25+nr<0:pos=nr=0;clamped=1
   expected+=struct.pack('>ih',pos,nr)
  same_update=position_inputs[i*12:(i+1)*12]==raw[i*80+68:i*80+80]
  if rec[20:]!=expected or flag!=clamped or (vx,vz)!=(vqx>>16,vqz>>16) or not same_update:
   position_failures.append({'record':i,'same_update_velocity':same_update,'actual':rec.hex(),'expected_position':expected.hex()})
 ps=(paths[2]/'position_shadow.bin').read_bytes();position_final=all(struct.unpack_from('>h',ps,c*12+axis*6)[0]==struct.unpack_from('>h',state,base+c*2)[0] and -24<=struct.unpack_from('>h',ps,c*12+axis*6+4)[0]<=24 for c in range(8) for axis,base in enumerate((0x6a61a,0x6a62a)))
 heading_raw=(paths[2]/'heading_records.bin').read_bytes();heading_failures=[];heading_counts=[[0,0] for _ in range(8)]
 for i in range(1600):
  car,axis,inc,before,rem,pad,after,nr,status=struct.unpack_from('>HHiIhHIhH',heading_raw,i*24);heading_counts[car][axis]+=1
  total=inc+rem;q=(abs(total)//5)*(1 if total>=0 else -1)
  if after!=(before+q)&0xffffffff or nr!=total-q*5 or status!=0 or pad!=0:heading_failures.append(i)
 hs=(paths[2]/'heading_shadow.bin').read_bytes();heading_final=all(hs[c*12+axis*6:c*12+axis*6+4]==state[base+c*4:base+c*4+4] and -4<=struct.unpack_from('>h',hs,c*12+axis*6+4)[0]<=4 for c in range(8) for axis,base in enumerate((0x2278a,0x227aa)))
 passed=passed and not position_failures and position_counts==[100]*8 and position_final and not heading_failures and heading_counts==[[100,100]]*8 and heading_final and probe['fine_steps']==800 and probe['heading_steps']==1600
 row={'passed':passed,'position_records':800,'position_failures':position_failures,'position_final_matches':position_final,'heading_records':1600,'heading_failures':heading_failures,'heading_final_matches':heading_final,'scalar_shadow_matches_native':scalar_shadow_ok,'fractional_feedback_speeds':sum(bool(struct.unpack_from('>i',feedback,i*8)[0]&65535) for i in range(800)),'stopped_feedbacks':sum(struct.unpack_from('>h',feedback,i*8+6)[0] for i in range(800)),'scalar_rate_records':probe['speed_records_count'],'scalar_rate_sites':rate_sites,'scalar_rate_clamps':rate_clamps,'scalar_rate_failures':rate_failures,'fractional_target_speeds':sum(bool(x&65535) for x in target_speeds),'native_states_exact':not any(mismatches.values()),'mismatches':mismatches,'records':800,'per_car':cars,'failures':failures,'shadow_matches_native':shadow_ok,'max_native_component_delta':max_delta,'max_raw_body_component':max_raw,'max_limited_body_component':max_response,'fractional_projected_components':fractions,'normalized_magnitudes_above_legacy_sqrt_range':wide_magnitudes,'records_requiring_full_product':wide_products,'max_exact_magnitude':max_magnitude,'probe':probe}
 report['profiles'][profile]=row;print(profile,json.dumps(row)[:3000],flush=True)
report['status']='passed' if len(report['profiles'])==2 and all(x['passed'] for x in report['profiles'].values()) else 'incomplete_or_failed'
(r/'manifest/step5-motion-fine-validation.json').write_text(json.dumps(report,indent=2)+'\n')
