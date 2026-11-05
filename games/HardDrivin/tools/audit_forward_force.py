"""Reconstruct native B74E..B8A2 from captured operands; no game writes."""
import json,sys
from pathlib import Path
from dissipation_model import trunc

def word(v):return (v+32768)%65536-32768

def native_sqrt(n):
 if n<=0:return 0
 current=previous=n//5000+8
 for _ in range(100):
  result=(n//current+current)//2
  if result in (current,previous):return result
  previous,current=current,result
 raise AssertionError('sqrt did not converge')

def force(v,power,road,turn,skid,braking,slope):
 drag=(-1 if v<0 else 1)+trunc(v,32 if road else 15)
 if turn:drag*=2
 if skid:drag*=2
 if abs(drag)>abs(v):drag=v
 brake=trunc(v,35) if braking else 0
 if braking and not brake:brake=trunc(word(2*v),3)
 # The native 3*v is a word followed by logical right shift.
 speed3=(3*max(v,0))&65535;root_input=speed3//2
 drive=word(native_sqrt(root_input*root_input+power)-root_input)
 rate=word(drive-drag-brake-slope)
 rate=min(rate,40)
 if not braking:rate=max(rate,-35)
 return dict(drag=drag,brake=brake,drive=drive,rate=rate)

if __name__=='__main__':
 path=Path(sys.argv[1]);samples=json.loads((path/'samples.json').read_text())['V'];rows=[]
 for r in samples:
  drag,brake,slope,drive,throttle,braking,gear,buttons,power,road,turn,skid=r['inputs']
  expected=force(r['old'],power,road,turn,skid,braking,slope)
  assert expected==dict(drag=drag,brake=brake,drive=drive,rate=r['rate']),(r,expected)
  # Diagnostic frozen-input native recurrence, then its final fractional step.
  # This is not a new live integrator: power/terrain/controls remain fixed.
  v=r['old'];remaining=r['fields'];steps=0
  while remaining:
   n=min(remaining,8);f=force(v,power,road,turn,skid,braking,slope)
   v+=trunc(f['rate']*n,8);remaining-=n;steps+=1
  rows.append(dict(field=r['field'],fields=r['fields'],old=r['old'],power=power,rate=r['rate'],live_velocity=r['value'],frozen_input_native_recurrence=v,rate_evaluations=steps))
 result=dict(passed=True,native_force_matches=len(rows),scope='Force-law operands only. Frozen-input recurrence is an offline diagnostic, not whole-car reference behavior.',rows=rows)
 (path/'force-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
