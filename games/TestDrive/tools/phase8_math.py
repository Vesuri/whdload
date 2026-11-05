#!/usr/bin/env python3
"""Independent exact-integer vectors for the actual 68000 phase-8 helpers."""
from pathlib import Path
import json, random
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'src'
def trunc(n,d): return (1 if n>=0 else -1)*(abs(n)//d)
def ratio(x,n,d,c):
 q=trunc(x*n+c,d)
 return q,x*n+c-q*d
def distance(v,a,p,c):
 if p==5:return v>>6,0
 n=10*v+3*a
 if n<0:n=c=0
 return ratio(n,2,3200,c)
def relax(v,k,c):
 n=v*k+c
 return v-(n//65536),n%65536
def signedword(n):return (n+32768)%65536-32768
def vectors():
 groups={k:[] for k in ['sim_scale_long','sim_ratio','sim_clock_delta','sim_distance','sim_relax_word','sim_cadence','verify_width_case','sim_traffic_delta','sim_reference_velocity','sim_lcg','verify_visual_samples_case','sim_coarse_rate']}
 def add(fn,x,n,d,c,p,result):
  q,r=result
  assert -(1<<31)<=q<(1<<31)
  groups[fn].append((x,n,d,c,p,q,signedword(r)))
 for p in [2,5]:
  for x in [-(1<<31),-270336,-65537,-6,-5,-4,-1,0,1,4,5,6,65537,270336,(1<<31)-1]:
   for c in [0] if p==5 else [-4,0,4]:add('sim_scale_long',x,0,0,c,p,ratio(x,p,5,c))
  for x in [0,1,17,85,200,32767]:
   for c in [0,24]:add('sim_clock_delta',x,0,0,c,p,ratio(x,6*p,25,c))
  for v,a in [(0,0),(1,0),(63,0),(64,0),(65536,65536),(65536,-65536),(0,-270336),(10000000,270336),(0xffffff,0x100000)]:
   for c in [0,3199]:add('sim_distance',v,a,0,c,p,distance(v,a,p,c))
 for p in [2,5]:
  for v,acc in [(0,0),(0,-1536),(1,0),(100000,0),(100000,1536),(100000,-1536),(0xffffff,0x100000)]:
   for c in [0,49]:
    n=10*v-3*acc
    expected=(v,0) if p==5 else ratio(max(n,0),2,50,c if n>=0 else 0)
    if v==0:expected=(0,0)
    add('sim_traffic_delta',v,acc,0,c,p,expected)
 for p in [2,5]:
  for v in [0,1,65536,10000000,0xffffff]:
   for acc in [-0x100000,-270336,-1,0,1,270336,0x100000]:
    add('sim_reference_velocity',v,acc,0,0,p,(v if p==5 else max(0,v-trunc(3*acc,10)),0))
 for seed in [0,1,-1,0x1234,32767,-32768]:
  add('sim_lcg',seed,0,0,0,2,(signedword(seed)*6907+130253,0))
 seed=0x1234
 for step in range(126):
  initial=seed;values=[]
  for draw in range(5):
   value=signedword(seed)*6907+130253;values.append(value);seed=value&65535
  if step in [0,1,2,124,125]:add('verify_visual_samples_case',initial,0,0,0,2,(values[0],seed))
  if step==125:assert values[0]&1023==0, 'visual trigger never reaches zero'
 for p in [2,5]:
  for rate in [-858993459,-393216,-65537,-3,-2,-1,0,1,2,3,65537,393216,858993459]:
   add('sim_coarse_rate',rate,0,0,0,p,(trunc(rate*5,p),0))
 for x,n,d,c in [(0,2,5,-4),(0,2,5,4),(5,2,5,-4),(-5,2,5,4),(2147483647,2,3200,3199),(-2147483648,2,3200,-3199)]:
  add('sim_ratio',x,n,d,c,2,ratio(x,n,d,c))
 for v in [-32768,-8000,-32,-1,0,1,32,8000,32767]:
  for c in [0,65535]:add('sim_relax_word',v,827,0,c,2,relax(v,827,c))
 for p in [2,5]:
  for phase in range(5):add('sim_cadence',p,0,0,phase,p,divmod(p+phase,5))
 for code in [0,1,15,16,85,171,240,254]:
  add('verify_width_case',code,0,0,0,2,(320+64*(code>>4),320+64*(code&15)))
 # Constant-rate composition and changing-sign carry sequence, feeding previous remainder.
 for seq in [[1]*5,[-1]*5,[270336]*5,[-270336]*5,[5,-1,-4,1,-5,4]]:
  c=0;total=0
  for x in seq:
   q,r=ratio(x,2,5,c);add('sim_scale_long',x,0,0,c,2,(q,r));c=r;total+=q
  assert total*5+c==sum(seq)*2
 return groups
if __name__=='__main__':
 groups=vectors(); asm=['; Independent exact-integer vectors: tools/phase8_math.py in the local harness.', 'verify_math_units:', '    movem.l d0-a6,-(sp)', '    lea sim_p(pc),a1', '    move.w (a1),-(sp)']
 for fn,rows in groups.items():
  asm += [f'    lea verify_vectors_{fn}(pc),a2',f'    lea {fn}(pc),a3',f'    move.w #{len(rows)-1},d7', '    bsr verify_math_group']
 asm += ['    lea sim_p(pc),a1','    move.w (sp)+,(a1)','    movem.l (sp)+,d0-a6','    rts', 'verify_math_group:', '.next:', '    move.l (a2)+,d0','    move.l (a2)+,d1','    move.l (a2)+,d2','    move.l (a2)+,d3','    lea verify_math_carry(pc),a0','    move.w d3,(a0)','    move.l (a2)+,d3','    lea sim_p(pc),a1','    move.w d3,(a1)','    jsr (a3)','    move.l (a2)+,d1','    bsr verify_equal','    move.w (a0),d0','    ext.l d0','    move.l (a2)+,d1','    bsr verify_equal','    dbf d7,.next','    rts','verify_math_carry: dc.w 0','verify_width_case:','    bsr sim_width_decode','    move.w d1,(a0)','    rts','verify_visual_samples_case:','    lea sim_visual_seed(pc),a1','    move.w d0,(a1)','    bsr sim_visual_samples','    move.w (a1),(a0)','    move.l sim_visual_values(pc),d0','    rts']
 for fn,rows in groups.items():
  asm += [f'verify_vectors_{fn}:']
  asm += ['    dc.l '+','.join(str(v) for v in row) for row in rows]
 target=SOURCE/'simulation-verify.s';s=target.read_text();s=s.split('; BEGIN PHASE8 MATH')[0];s=s.replace('    bsr verify_math_units\n','')
 s=s.replace('    movem.l (sp)+,d0-a6\n    rts\nverify_equal:', '    bsr verify_math_units\n    movem.l (sp)+,d0-a6\n    rts\nverify_equal:')
 target.write_text(s.rstrip()+'\n\n; BEGIN PHASE8 MATH\n'+'\n'.join(asm)+'\n')
 out=ROOT/'tmp/phase8';out.mkdir(exist_ok=True)
 summary=dict(assertions=22+2*sum(map(len,groups.values())),vectors={k:len(v) for k,v in groups.items()})
 (out/'math-vectors.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
