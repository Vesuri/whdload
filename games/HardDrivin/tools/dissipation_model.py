def trunc(n,d):return (abs(n)//d)*(-1 if n<0 else 1)
def update(v,rate,n,carry,last,drive,drag,brake,slope):
 carry=carry if v==last else 0
 numerator=rate*n+carry;delta=trunc(numerator,8);remainder=numerator-delta*8;limited=False
 resistance=drag+brake
 # Native net cap can reduce an opposing component, but never increase it or
 # change its direction. Any residual capped rate belongs to external forces.
 candidate=drive-slope-rate
 opposing=min(max(candidate,0),resistance) if resistance>=0 else max(min(candidate,0),resistance)
 stored_eighths=v*8+carry
 if n>0 and not (n==8 and carry==0) and stored_eighths*opposing>0 and abs(opposing)*n>abs(stored_eighths):
  numerator=(rate+opposing)*n
  value=trunc(numerator,8);remainder=numerator-value*8;delta=value-v;limited=True
 else:value=v+delta
 wrapped=(value+32768)%65536-32768
 return dict(delta=delta,full=value,value=wrapped,carry=remainder,limited=limited,opposing=opposing)
