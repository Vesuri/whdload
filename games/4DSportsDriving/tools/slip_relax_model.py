#!/usr/bin/env python3
import json
from pathlib import Path
from spin_filter_model import word

def native(a):
 if a<0:return word(-(word(word(-a)*15)>>4))&1023
 return (word(a*15)>>4)&1023

def step(a,r):
 if not 0<a<=1023:return native(a),0
 num=26723*((a+15)//16)+r-(1670*r//65536)
 loss,rem=divmod(num,65536);new=max(0,a-loss)
 return new,rem if new else 0

def five(a,r):
 for _ in range(5):a,r=step(a,r)
 return a,r

if __name__=='__main__':
 worst=0;count=0
 for a in range(1024):
  for r in (0,1,16384,32767,32768,49152,65534,65535):
   v,c=five(a,r);assert 0<=v<=a and 0<=c<65536
   worst=max(worst,abs(v-native(native(a))));count+=1
 for a in range(-32768,32768):
  if not 0<a<=1023:
   assert step(a,65535)==(native(a),0)
 long_worst=0
 for initial in range(1024):
  v=initial;n=initial;c=0
  for i in range(250):
   v,c=step(v,c)
   if i%5==4:
    n=native(native(n));long_worst=max(long_worst,abs(v-n))
 result={'five_second_zero_carry_max_error':long_worst,'five_step_canonical_cases' :count,'sampled_carries':[0,1,16384,32767,32768,49152,65534,65535],'max_error_vs_two_native_steps':worst,'noncanonical_event_words_checked':65536-1023,'scope':'canonical decay sampled carries; exact original one-time canonicalization; not full handling acceptance'}
 Path('tmp/analysis/slip-relax-model.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
