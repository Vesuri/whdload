from pathlib import Path
import json,struct,hashlib,math,os
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/step5-recovery-fine'
blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[{'name':'gear_display_transition','address':'0x6bf84','bytes':4}]
report={'scope':'Combined motion with 100 ms steering-history separation; controller evaluated every 20 ms with held raw requests during inactive gaps. Persistent Q16 velocity with scalar continuous rates scaled to 20 ms. Scalar fractions persist across load/store and velocity feedback; continuous slip wear is divided by five before saturation; rotating component wear and opponent random failures use native 100 ms pulses; eligible native calendar/session clock calls use the same pulses; fuel consumption uses per-car /5 remainder before saturation; other events and the real-time scheduler remain unconverted. Not 20 ms gameplay or capacity acceptance.','boost_scope':'Pulse-gated CPU/audio/gear state in the existing drawing-omission fixture. Full presentation separation and audio quality remain unaccepted.','coverage_note':'Event gating changes the demo trajectory. Replay every observed wear update; missing branch sites are listed explicitly. Earlier all-six-branch wear captures are separate evidence, not coverage in this window.','physics_accepted':False,'profiles':{}}
def w(x):return ((x+32768)&65535)-32768
for profile in ('a1200','a1200-fast'):
 paths=[r/'tmp/step5'/(profile+('-b6-s5-matrix-verify-' if v=='fine' else '-recovery-fine-')+v) for v in ('control','bridge','fine')]
 if not all((p/'result.json').exists() for p in paths):continue
 results=[json.loads((p/'result.json').read_text()) for p in paths]
 if not all(d.get('status')=='complete' and d.get('slave_sha256')==hashlib.sha256(((r/('tmp/build/step5-b6-s5/verify') if v=='fine' else b)/(v+'.slave')).read_bytes()).hexdigest() for d,v in zip(results,('control','bridge','fine'))):continue
 mismatches={}
 for tick in (125,150,175,225):
  data=[(p/f'loop{tick}.bin').read_bytes() for p in paths[:2]]
  mismatches[tick]=[x['name'] for x in blocks if data[0][int(x['address'],16):int(x['address'],16)+x['bytes']]!=data[1][int(x['address'],16):int(x['address'],16)+x['bytes']]]
 state=(paths[2]/'loop225.bin').read_bytes();raw=(paths[2]/'velocity_records.bin').read_bytes();shadow=(paths[2]/'velocity_shadow.bin').read_bytes()
 assert len(raw)==64000 and len(shadow)==96
 feedback=(paths[2]/'speed_feedback_records.bin').read_bytes()
 target_speeds=struct.unpack('>800i',(paths[2]/'velocity_target_speeds.bin').read_bytes())
 failures=[];cars=[0]*8;max_delta=0;max_raw=0;max_response=0;fractions=0;wide_magnitudes=0;wide_products=0;max_magnitude=0
 for i in range(100):
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
 shadow_ok=all((struct.unpack_from('>i',shadow,car*12+axis*4)[0]>>16)==struct.unpack_from('>h',state,base+car*2)[0] for car in range(1) for axis,base in enumerate((0x6f13c,0x6f14c)))
 speed_shadow=(paths[2]/'speed_shadow.bin').read_bytes()
 scalar_shadow_ok=all(struct.unpack_from('>h',speed_shadow,car*6)[0]==struct.unpack_from('>h',state,0x2275a+car*2)[0] for car in range(1))
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
 passed=scalar_shadow_ok and probe['speed_loads']==probe['speed_stores']==100 and not rate_failures and probe['speed_records_count']>0 and not any(mismatches.values()) and not failures and shadow_ok and cars==[100]+[0]*7 and all(probe[k]==100 for k in ('velocity_loads','velocity_stores','velocity_projects','velocity_raws','velocity_records_count')) and probe['velocity_rotations']>0 and probe['error']==0
 position_raw=(paths[2]/'fine_records.bin').read_bytes();position_inputs=(paths[2]/'position_velocity_inputs.bin').read_bytes();position_failures=[];position_counts=[0]*8
 for i in range(100):
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
 ps=(paths[2]/'position_shadow.bin').read_bytes();position_final=all(struct.unpack_from('>h',ps,c*12+axis*6)[0]==struct.unpack_from('>h',state,base+c*2)[0] and -24<=struct.unpack_from('>h',ps,c*12+axis*6+4)[0]<=24 for c in range(1) for axis,base in enumerate((0x6a61a,0x6a62a)))
 heading_raw=(paths[2]/'heading_records.bin').read_bytes();heading_failures=[];heading_counts=[[0,0] for _ in range(8)]
 for i in range(200):
  car,axis,inc,before,rem,pad,after,nr,status=struct.unpack_from('>HHiIhHIhH',heading_raw,i*24);heading_counts[car][axis]+=1
  total=inc+rem;q=(abs(total)//5)*(1 if total>=0 else -1)
  if after!=(before+q)&0xffffffff or nr!=total-q*5 or status!=0 or pad!=0:heading_failures.append(i)
 hs=(paths[2]/'heading_shadow.bin').read_bytes();heading_final=all(hs[c*12+axis*6:c*12+axis*6+4]==state[base+c*4:base+c*4+4] and -4<=struct.unpack_from('>h',hs,c*12+axis*6+4)[0]<=4 for c in range(1) for axis,base in enumerate((0x2278a,0x227aa)))
 passed=passed and not position_failures and position_counts==[100]+[0]*7 and position_final and not heading_failures and heading_counts==[[100,100]]+[[0,0]]*7 and heading_final and probe['fine_steps']==100 and probe['heading_steps']==200
 steering_bytes=(paths[2]/'steering_records.bin').read_bytes();initial=(paths[2]/'loop125.bin').read_bytes();steering_failures=[];steering_counts=[0]*8;histories=[];different_delays=0
 for car in range(8):
  held=struct.unpack_from('>h',initial,0x32f7a+car*2)[0];histories.append({'h':[held]*5,'cursor':0,'last':125,'held':held})
 for i in range(probe['steering_samples']):
  tick,car,current,delayed,filtered,oldtick,gap=struct.unpack_from('>IHhhhII',steering_bytes,i*20);h=histories[car];steering_counts[car]+=1
  expected_gap=(tick-h['last'])&0xffffffff
  if oldtick!=h['last'] or gap!=expected_gap or not 0<gap<2**31:steering_failures.append({'record':i,'bad_quantum':True})
  if gap>=5:h['h']=[h['held']]*5;h['cursor']=0
  else:
   for _ in range(gap-1):h['h'][h['cursor']]=h['held'];h['cursor']=(h['cursor']+1)%5
  prior=h['h'][h['cursor']];ef=w(current+prior)//2;different_delays+=prior!=h['held']
  if (delayed,filtered)!=(prior,ef):steering_failures.append({'record':i,'actual':[delayed,filtered],'expected':[prior,ef]})
  h['h'][h['cursor']]=current;h['cursor']=(h['cursor']+1)%5;h['last']=tick;h['held']=current
 steering_shadow=(paths[2]/'steering_shadow.bin').read_bytes()
 steering_final=all(steering_shadow[car*18:(car+1)*18]==struct.pack('>5hHIh',*h['h'],h['cursor'],h['last'],h['held']) and h['held']==struct.unpack_from('>h',state,0x32f7a+car*2)[0] for car,h in enumerate(histories[:1]))
 passed=passed and not steering_failures and steering_final and steering_counts==[100]+[0]*7 and probe['steering_resets']==0
 wear_bytes=(paths[2]/'wear_records.bin').read_bytes();wear_failures=[];wear_sites={};wear_addresses={};wear_carry={};wear_depletions=0;wear_condition={}
 for i in range(probe['wear_samples']):
  site,address,condition,rate,delta,oldrem,newrem,tick,pad=struct.unpack_from('>5I2H2I',wear_bytes,i*32)
  q,rem=divmod(rate+oldrem,5)
  if q>=condition:q=condition;rem=0;wear_depletions+=1
  valid_address=address in [0x66c52+4*c for c in range(4)]+[0x22356+4*c for c in range(1,8)]
  continuous=probe['wear_resets']!=0 or oldrem==wear_carry.get(address,0)
  prior_condition=wear_condition.get(address,struct.unpack_from('>I',initial,address)[0])
  if probe['wear_resets']==0 and condition!=prior_condition:wear_failures.append({'record':i,'condition_continuity':False,'actual':condition,'expected':prior_condition})
  wear_condition[address]=condition-delta
  if not(valid_address and condition<2**31 and rate<2**31 and oldrem<5 and (delta,newrem)==(q,rem) and pad==0 and 126<=tick<=225 and continuous):
   wear_failures.append({'record':i,'site':hex(site),'actual':[delta,newrem],'expected':[q,rem],'continuous_carry':continuous})
  wear_carry[address]=newrem
  wear_sites[hex(site)]=wear_sites.get(hex(site),0)+1
  wear_addresses[hex(address)]=wear_addresses.get(hex(address),0)+1
 wear_shadow=(paths[2]/'wear_remainders.bin').read_bytes()
 wear_final=all(struct.unpack_from('>H',wear_shadow,((a-0x66c52)//4 if a>=0x66c52 else 4+(a-0x22356)//4)*2)[0]==rem for a,rem in wear_carry.items())
 wear_final=wear_final and all(struct.unpack_from('>I',state,a)[0]==value for a,value in wear_condition.items())
 passed=passed and probe['wear_samples']==400 and not wear_failures and wear_final and probe['wear_resets']==0 and set(wear_sites)<= {'0x6e018','0x6de96','0x6de74','0x6df2a','0x6defa','0x6ded4'} and len(wear_addresses)==4 and all(n==100 for n in wear_addresses.values())
 event_failures=[];event_stats={}
 for variant_index in (1,2):
  ep=results[variant_index]['probe'];eraw=(paths[variant_index]/'events_records.bin').read_bytes();percar=[0]*8;accepted=[0]*8;skipped=0;rng_saved=0;last_tick=125
  for i in range(ep['events_samples']):
   rec=eraw[i*160:(i+1)*160]
   tick,car,kind,ran,before_index,after_index,pad0,rng_before,rng_after,pad1,pad2=struct.unpack_from('>I6H4I',rec)
   percar[car]+=1;accepted[car]+=ran
   expected_run=int(variant_index==1 or (tick-125)%5==0)
   valid=126<=tick<=225 and tick>=last_tick and car<8 and kind==int(car!=0) and ran==expected_run and pad0==pad1==pad2==0
   last_tick=tick
   calls=(rng_after-rng_before)&0xffffffff
   if ran:
    valid=valid and (after_index==(before_index+1)%9 and calls>=9 if car==0 else after_index==before_index and calls in (1,2))
   else:
    skipped+=1;valid=valid and calls==0 and before_index==after_index and rec[32:96]==rec[96:160]
   if not valid:event_failures.append({'variant':variant_index,'record':i,'tick':tick,'car':car,'ran':ran,'calls':calls,'indices':[before_index,after_index]})
  expected_accepted=[100]*8 if variant_index==1 else [20]+[0]*7
  ok=percar==([100]*8 if variant_index==1 else [100]+[0]*7) and accepted==expected_accepted and ep['events_pulses']==(0 if variant_index==1 else 20)
  if not ok:event_failures.append({'variant':variant_index,'counts':percar,'accepted':accepted,'pulses':ep['events_pulses']})
  event_stats[('bridge','fine')[variant_index-1]]={'records':ep['events_samples'],'per_car':percar,'accepted':accepted,'skipped':skipped,'rng_calls_total':ep['events_rng_calls'],'pulses':ep['events_pulses']}
 passed=passed and not event_failures
 clock_failures=[];clock_stats={}
 for vi in (1,2):
  cp=results[vi]['probe'];cr=(paths[vi]/'clocks_records.bin').read_bytes();counts=[0,0];accepted=[0,0];previous={}
  for i in range(cp['clocks_samples']):
   rec=cr[i*32:(i+1)*32];tick,kind,ran=struct.unpack_from('>IHH',rec);before=rec[8:18];after=rec[18:28]
   counts[kind]+=1;accepted[kind]+=ran;expected=bytearray(before)
   erun=int(vi==1 or (tick-125)%5==0)
   if ran:
    carry=1
    for digit,base in ((9,10),(8,10),(7,6),(6,10),(5,6),(4,10)):
     if not carry:break
     expected[digit]+=1
     if expected[digit]>=base:expected[digit]=0
     else:carry=0
    if carry:clock_failures.append({'record':i,'unsupported_hour_rollover':True})
   if ran!=erun or after!=expected or rec[28:]!=bytes(4):clock_failures.append({'variant':vi,'record':i,'actual':after.hex(),'expected':expected.hex(),'ran':ran,'expected_run':erun})
   if kind in previous and before!=previous[kind]:clock_failures.append({'variant':vi,'record':i,'clock_continuity':False})
   previous[kind]=after
  # Eligibility is preserved by patching the two calls inside the original rules.
  # This demo window has no resets, countdown or session-cap transition.
  final=(paths[vi]/'loop225.bin').read_bytes()
  for kind,value in previous.items():
   address=0x226c0+10*kind
   if final[address:address+10]!=value:clock_failures.append({'variant':vi,'kind':kind,'final_mismatch':True})
  if counts!=[100,100] or accepted!=([100,100] if vi==1 else [20,20]):clock_failures.append({'variant':vi,'counts':counts,'accepted':accepted})
  clock_stats[('bridge','fine')[vi-1]]={'records':cp['clocks_samples'],'eligible_calls':counts,'accepted_pulses':accepted,'elapsed_simulated_ms':2000 if vi==2 else 10000}
 passed=passed and not clock_failures
 counter_failures=[];counter_stats={}
 for vi in (1,2):
  cp=results[vi]['probe'];cr=(paths[vi]/'counters_records.bin').read_bytes();counts=[0,0,0];accepted=[0,0,0];last={}
  for i in range(cp['counters_samples']):
   tick,kind,ran,before,after,pad=struct.unpack_from('>I4HI',cr,i*16)
   counts[kind]+=1;accepted[kind]+=ran
   erun=int(vi==1 or (tick-125)%5==0)
   expected=(before+ran)%4 if kind==0 else before-ran if kind==1 else None
   if kind==2 or ran!=erun or after!=expected or pad!=0:counter_failures.append({'variant':vi,'record':i,'kind':kind,'actual':after,'expected':expected})
   if kind in last and last[kind]!=before:counter_failures.append({'variant':vi,'record':i,'continuity':False})
   last[kind]=after
  final=(paths[vi]/'loop225.bin').read_bytes()
  if counts!=[100,0,0] or accepted!=([100,0,0] if vi==1 else [20,0,0]) or final[0x1be42]!=last.get(0):counter_failures.append({'variant':vi,'counts':counts,'accepted':accepted})
  counter_stats[('bridge','fine')[vi-1]]={'records':cp['counters_samples'],'counts':counts,'accepted':accepted,'scope':'Engine phase only; countdown/clutch not exercised by this racing demo window.'}
 passed=passed and not counter_failures
 fuel_failures=[];fuel_counts=[0]*8;fuel_carry=[0]*8;fuel_state=[struct.unpack_from('>I',initial,0x22376+4*c)[0] for c in range(8)];fuel_total_loss=0;fuel_native_loss=0;fuel_depletions=0
 fr=(paths[2]/'fuel_records.bin').read_bytes()
 for i in range(probe['fuel_samples']):
  site,address,before,rate,delta,oldrem,newrem,tick,pad=struct.unpack_from('>5I2H2I',fr,i*32)
  car=(address-0x22376)//4
  q,rem=divmod(rate+oldrem,5)
  if q>=before:q=before;rem=0;fuel_depletions+=1
  valid=site==0x6d164 and 0<=car<8 and address==0x22376+4*car and oldrem<5 and before<2**31 and rate<2**31 and (delta,newrem)==(q,rem) and 126<=tick<=225 and pad==0
  if not valid:fuel_failures.append({'record':i,'arithmetic':False})
  if before!=fuel_state[car] or oldrem!=fuel_carry[car]:fuel_failures.append({'record':i,'continuity':False})
  fuel_state[car]=before-delta;fuel_carry[car]=newrem;fuel_counts[car]+=1;fuel_total_loss+=delta;fuel_native_loss+=rate
 fuel_final=all(struct.unpack_from('>I',state,0x22376+4*c)[0]==fuel_state[c] for c in range(1)) and list(struct.unpack('>8H',(paths[2]/'fuel_remainders.bin').read_bytes()))==fuel_carry
 passed=passed and not fuel_failures and fuel_final and fuel_counts==[100]+[0]*7 and probe['fuel_resets']==0
 boost_failures=[];boost_stats={}
 for vi in (1,2):
  bp=results[vi]['probe'];br=(paths[vi]/'boost_records.bin').read_bytes();accepted=0;skipped=0;directions={'up':0,'down':0,'held':0};previous=None
  native=(paths[vi]/'loop225.bin').read_bytes();audio_delta=struct.unpack_from('>I',native,0x6bf70)[0]
  for i in range(bp['boost_samples']):
   rec=br[i*48:(i+1)*48];tick,ran,rpm,setting,before,condition,after,target,oldoff,oldrow,newoff,newrow,oldtarget,gear,pitch0,delta0,pitch1,delta1=struct.unpack('>IHhhhI6h2h4I',rec)
   erun=int(vi==1 or (tick-125)%5==0);accepted+=ran;skipped+=not ran
   expected_after=before;expected_target=oldtarget;expected_off=oldoff;expected_row=oldrow;expected_pitch=pitch0;expected_delta=delta0
   if ran:
    quotient=(abs(rpm)//265)*(1 if rpm>=0 else -1)
    factor=max(w(quotient-15),0)*setting
    expected_target=w((((condition>>8)*factor)&0xffffffff)>>14)
    if before>w(expected_target+5):expected_after=w(before-9);expected_delta=audio_delta;directions['down']+=1
    elif before<w(expected_target-5):expected_after=w(before+9);expected_delta=(-audio_delta)&0xffffffff;directions['up']+=1
    else:directions['held']+=1
    shifted=(expected_after<<13)&0xffffffff;signed_shift=shifted if shifted<2**31 else shifted-2**32
    expected_pitch=(min(signed_shift,0x300000))&0xffffffff
    targetrow=w((w(gear-1)>>1)*5);targetoff=(w(gear-1)&1)*8
    if oldrow==targetrow:
     if oldoff>targetoff:expected_off=w(oldoff-4)
     elif oldoff<targetoff:expected_off=w(oldoff+4)
    elif oldoff==4:
     if oldrow>targetrow:expected_row=w(oldrow-5)
     elif oldrow<targetrow:expected_row=w(oldrow+5)
    elif oldoff>4:expected_off=w(oldoff-4)
    else:expected_off=w(oldoff+4)
   actual=(after,target,newoff,newrow,pitch1,delta1);expected=(expected_after,expected_target,expected_off,expected_row,expected_pitch,expected_delta)
   if ran!=erun or actual!=expected:boost_failures.append({'variant':vi,'record':i,'ran':ran,'actual':actual,'expected':expected})
   if previous is not None and (before,oldoff,oldrow)!=previous:boost_failures.append({'variant':vi,'record':i,'continuity':False})
   previous=(after,newoff,newrow)
  final_state=(struct.unpack_from('>h',native,0x66c76)[0],*struct.unpack_from('>hh',native,0x6bf84))
  if bp['boost_samples']!=100 or accepted!=(100 if vi==1 else 20) or previous!=final_state:boost_failures.append({'variant':vi,'count_or_final':False})
  boost_stats[('bridge','fine')[vi-1]]={'records':bp['boost_samples'],'accepted':accepted,'skipped':skipped,'directions':directions}
 passed=passed and not boost_failures
 recovery_failures=[];recovery_stats={}
 for vi in (1,2):
  rp=results[vi]['probe'];rr=(paths[vi]/'recovery_records.bin').read_bytes();accepted=0;changes=0
  for i in range(rp['recovery_samples']):
   rec=rr[i*256:(i+1)*256];tick,pulse,gate,paused,countdown,session,pad=struct.unpack_from('>I6H',rec)
   before=rec[16:136];after=rec[136:256];erun=int(vi==1 or (tick-125)%5==0);accepted+=pulse
   # This healthy demo has no recovery state; transition fixture checks nonzero cases.
   statuses=struct.unpack_from('>8h',before)
   if pulse!=erun or before!=after or any(statuses) or pad!=0:recovery_failures.append({'variant':vi,'record':i,'statuses':statuses,'changed':before!=after})
   changes+=before!=after
  if rp['recovery_samples']!=100 or rp['recovery_contacts']!=0 or accepted!=(100 if vi==1 else 20):recovery_failures.append({'variant':vi,'counts':False})
  recovery_stats[('bridge','fine')[vi-1]]={'records':rp['recovery_samples'],'accepted':accepted,'state_changes':changes,'contact_records':rp['recovery_contacts'],'scope':'Healthy demo only; nonzero recovery is validated separately.'}
 passed=passed and not recovery_failures
 row={'recovery_stats':recovery_stats,'recovery_failures':recovery_failures,'boost_stats':boost_stats,'boost_failures':boost_failures,'fuel_records':probe['fuel_samples'],'fuel_per_car':fuel_counts,'fuel_failures':fuel_failures,'fuel_final_matches':fuel_final,'fuel_depletions':fuel_depletions,'fuel_applied_loss':fuel_total_loss,'fuel_sum_native_requested_loss':fuel_native_loss,'counter_stats':counter_stats,'counter_failures':counter_failures,'clock_stats':clock_stats,'clock_failures':clock_failures,'wear_sites_missing_this_window':sorted({'0x6e018','0x6de96','0x6de74','0x6df2a','0x6defa','0x6ded4'}-set(wear_sites)),'prior_all_branch_wear_evidence':'manifest/step5-wear-fine-validation.json','event_stats':event_stats,'event_failures':event_failures,'wear_records':probe['wear_samples'],'wear_sites':wear_sites,'wear_addresses':wear_addresses,'wear_failures':wear_failures,'wear_final_matches':wear_final,'wear_depletions':wear_depletions,'passed':passed,'steering_records':probe['steering_samples'],'steering_failures':steering_failures,'steering_final_matches':steering_final,'history_differs_from_previous_20ms_sample':different_delays,'position_records':100,'position_failures':position_failures,'position_final_matches':position_final,'heading_records':200,'heading_failures':heading_failures,'heading_final_matches':heading_final,'scalar_shadow_matches_native':scalar_shadow_ok,'fractional_feedback_speeds':sum(bool(struct.unpack_from('>i',feedback,i*8)[0]&65535) for i in range(100)),'stopped_feedbacks':sum(struct.unpack_from('>h',feedback,i*8+6)[0] for i in range(100)),'scalar_rate_records':probe['speed_records_count'],'scalar_rate_sites':rate_sites,'scalar_rate_clamps':rate_clamps,'scalar_rate_failures':rate_failures,'fractional_target_speeds':sum(bool(x&65535) for x in target_speeds),'native_states_exact':not any(mismatches.values()),'mismatches':mismatches,'records':100,'per_car':cars,'failures':failures,'shadow_matches_native':shadow_ok,'max_native_component_delta':max_delta,'max_raw_body_component':max_raw,'max_limited_body_component':max_response,'fractional_projected_components':fractions,'normalized_magnitudes_above_legacy_sqrt_range':wide_magnitudes,'records_requiring_full_product':wide_products,'max_exact_magnitude':max_magnitude,'probe':probe}
 report['profiles'][profile]=row;print(profile,json.dumps(row)[:3000],flush=True)
report['scope']='B6 player-only 20 ms arithmetic replay; native opponents are checked by the separate native-instruction control fixture.'
report['boost_scope']='B6 simulation-owned boost/audio/gear replay. S3 component separation remains accepted; full rendered FPS and interactive audio acceptance remain outstanding.'
report['control_scope']='Control/bridge are retained recovery-fine captures; only fine is the new elapsed-time build. Their native comparison is prior evidence, not a new disabled-path acceptance.'
report['status']='passed' if len(report['profiles'])==2 and all(x['passed'] for x in report['profiles'].values()) else 'incomplete_or_failed'
(r/('manifest/step5-b6-s5-replay-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
