#!/usr/bin/env python3
"""Host checks for the quantized coupled half-filter (not full handling acceptance)."""
import json,math
from pathlib import Path

def trunc(n,d): return abs(n)//d*(1 if n>=0 else -1)
def word(n): return (n+32768)%65536-32768

def step(a,q,rate,angle):
    n=trunc(word(a+q),2)
    num=31738*(n-a)+rate-trunc(15869*rate,65536)
    da=trunc(num,65536)
    new=word(a+da)
    rem=num-da*65536 if new!=n else 0
    num=834*new-322*a+trunc(834*rem-322*rate,65536)+angle
    delta=trunc(num,1280)
    frac=num-delta*1280
    if new==0 and n==0: delta=frac=0
    assert min(a,n)<=new<=max(a,n)
    assert abs(rem)<65536 and abs(frac)<1280
    assert -32768<=delta<=32767
    return new,rem,frac,delta

def main():
    rho=.5**.4
    k=.4*rho/(1-rho)-1
    assert round(1280*k)==322
    ideal_error=0
    for a in range(-128,129):
        for q in (-128,-31,0,31,128):
            v=float(a); angle=0.
            for _ in range(5):
                new=q+rho*(v-q)
                angle+=.4*new+k*(new-v)
                v=new
            n=(a+q)/2; native=n+(n+q)/2
            ideal_error=max(ideal_error,abs(angle-native))
    assert ideal_error<1e-10
    worst_rate=worst_angle=0
    examples={};count=0
    for a in range(-128,129):
        for q in range(-128,129):
            n=trunc(a+q,2); expected_angle=n; n=trunc(n+q,2);expected_angle+=n
            for c in (-65535,0,65535):
                for z in (-1279,0,1279):
                    v=a;r=c;f=z;total=0
                    for _ in range(5):
                        v,r,f,d=step(v,q,r,f);total+=d
                    er=abs(v-n);ea=abs(total-expected_angle)
                    if er>worst_rate:worst_rate=er;examples['rate']=[a,q,c,z,n,v]
                    if ea>worst_angle:worst_angle=ea;examples['angle']=[a,q,c,z,expected_angle,total]
                    count+=1
    result={'input_rate_and_command_range':[-128,128], 'rate_carries':[-65535,0,65535], 'angle_carries':[-1279,0,1279], 'cases':count, 'steps_per_case':5, 'max_rate_error_vs_two_native_steps':worst_rate, 'max_angle_error_vs_two_native_steps':worst_angle, 'unrounded_affine_semigroup_error':ideal_error, 'coefficient_k':k, 'examples':examples, 'scope':'Sampled carry values and constant command; not an exhaustive all-carry or live handling bound.'}
    Path('tmp/analysis/spin-filter-model.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
