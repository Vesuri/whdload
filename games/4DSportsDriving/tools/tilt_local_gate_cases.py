#!/usr/bin/env python3
"""Build independent gate expectations plus regression vectors for premature snaps."""
import sys,re,math,json
from pathlib import Path
src=Path(sys.argv[1]);p=src/'simulation_tilt_gate_cases.i';s=p.read_text();rows=[]
def abswrap(q):return abs((q+262144)%524288-262144)
for a,b,c,e in re.findall(r' dc.l (-?\d+),(-?\d+)\n dc.w (-?\d+),0\n dc.l (\d+)',s):
 a,b,c,e=map(int,(a,b,c,e));ref=abswrap(2*(b-65536+c)+5*a);assert ref==e
 rows.append((a,b,c))
for sign in (-1,1):
 for old,delta in [(7,-610),(5,-600),(3,-272)]:
  for carry in (-128,0,127):rows.append((sign*delta,(256+sign*old)*256,sign*carry if carry!=-128 else -128))
 for target in (407,408,409):rows.append((-272*sign,(256+3*sign)*256,(target+272-768)*sign))
# Exact captured inputs, plus reflected orientations, exercise the observed
# landing and airborne failures rather than only synthetic small-angle cases.
root=Path(__file__).resolve().parents[1]
for capture in ('matched308-gate50','crest-gate-baseline50','crest-gate-guard50'):
 for row in json.loads((root/'tmp/prof'/capture/'gate-audit.json').read_text())['rows']:
  a,b,c=(row[k] for k in ('delta_q8','baseline_q8','carry'))
  rows.append((a,b,c))
  rows.append((-a,131072-b,-c))
rows=list(dict.fromkeys(rows))
text='; Independent Q9 oracle: BOTH actual and reference results must be near level.\nsim_tilt_gate_cases:\n'
for a,b,c in rows:
 expected=max(abswrap(2*(b-65536+c)+5*a),abswrap(2*(b-65536+c+a)))
 text+=f' dc.l {a},{b}\n dc.w {c},0\n dc.l {expected}\n'
p.write_text(text+'sim_tilt_gate_cases_end:\n')
p=src/'simulation_tilt_cases.i';s=p.read_text();extra='; Regression: reference-step crossing must not snap a non-level actual state.\n'
for sign in (-1,1):
 for old,new in [(7,4.6),(5,2.65)]:
  def v(angle):r=angle*math.pi/512;return (round(8192*math.cos(r)),round(-8192*math.sin(r)))
  x,y=v(sign*old);xx,yy=v(sign*new)
  delta=(math.atan2(xx,yy)-math.atan2(x,y))*512/math.pi
  for carry in (-128,0,127):
   expect=round((sign*old+delta)*256)+carry
   extra+=f' dc.w {x},{y},{xx},{yy},{carry},4\n dc.l {expect}\n'
s=s.replace('sim_tilt_cases_end:',extra+'sim_tilt_cases_end:');p.write_text(s)
p=src/'simulation_physics_verify.s';s=p.read_text();assert 'dc.w 23,SIM_TILT_TESTS' in s;p.write_text(s.replace('dc.w 23,SIM_TILT_TESTS','dc.w 24,SIM_TILT_TESTS'))
print(json.dumps(dict(gate_cases=len(rows),new_angle_cases=12)))
