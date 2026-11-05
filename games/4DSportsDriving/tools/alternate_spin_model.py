#!/usr/bin/env python3
import math,json
from pathlib import Path
from spin_filter_model import trunc,word

def native(a):return word(a*15)>>4

def step(a,rate,angle):
 n=native(a)
 num=26723*(n-a)+rate-trunc(1670*rate,65536)
 da=trunc(num,65536);new=word(a+da);rem=0 if new==n and native(n)==n else num-da*65536
 num=890*new-378*a+trunc(890*rem-378*rate,65536)+angle
 delta=trunc(num,1280);frac=num-delta*1280
 if new==n==0:delta=frac=0
 assert min(a,n)<=new<=max(a,n)
 assert abs(rem)<65536 and abs(frac)<1280 and -32768<=delta<=32767
 return new,rem,frac,delta

def five(a,r,z):
 total=0
 for _ in range(5):a,r,z,d=step(a,r,z);total+=d
 return a,z,r,total

if __name__=='__main__':
 rho=(15/16)**.4;alpha=(1-rho)*16;k=.4*rho/(1-rho)-15
 assert [round(alpha*65536),round((1-rho)*65536),round(k*1280)]==[26723,1670,378]
 ideal=0
 for a in range(-128,129):
  v=a;angle=0
  for _ in range(5):
   new=rho*v;angle+=.4*new+k*(new-v);v=new
  ideal=max(ideal,abs(angle-a*((15/16)+(15/16)**2)))
 assert ideal<1e-10
 worst=[0,0];count=0
 for a in range(-128,129):
  n=native(a);target=native(n);expected=n+target
  for r in (-65535,0,65535):
   for z in (-1279,0,1279):
    v,_,_,angle=five(a,r,z);worst[0]=max(worst[0],abs(v-target));worst[1]=max(worst[1],abs(angle-expected));count+=1
 # Full-word single-step range, sampled extreme/zero carries, including MULS/ASR.W wrap.
 for a in range(-32768,32768):
  for r,z in [(-65535,-1279),(0,0),(65535,1279)]:step(a,r,z)
 long_rate=long_angle=0
 examples=[]
 for initial in range(-128,129):
  a=initial;r=z=total=0;n=initial;nt=0
  for i in range(250):
   a,r,z,d=step(a,r,z);total+=d
   if i%5==4:
    for _ in range(2):n=native(n);nt+=n
    long_rate=max(long_rate,abs(a-n));long_angle=max(long_angle,abs(total-nt))
  if initial in (-32,15,32,128):examples.append([initial,n,a,nt,total])
 result={'five_second_zero_carry_max_rate_error':long_rate,'five_second_zero_carry_max_angle_error':long_angle,'five_second_examples_initial_nativeRate_newRate_nativeAngle_newAngle':examples,'physical_range' :[-128,128],'common_time_cases':count,'max_rate_error':worst[0],'max_angle_error':worst[1],'full_word_single_step_cases':65536*3,'unrounded_semigroup_error':ideal,'coefficients':[26723,1670,890,378],'scope':'constant zero-command decay, sampled carry values; not full handling acceptance'}
 Path('tmp/analysis/alternate-spin-model.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
