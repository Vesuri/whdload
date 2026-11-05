"""All signed heading deltas at wrap-sensitive starts and both field rates."""
from pathlib import Path
exec(Path(__file__).with_name('test_script_present_c.py').read_text().removesuffix('c.close()\n'))
c.put(gen,struct.pack('>I',7)+bytes(22));c.put(cache+sym('SPC_VALID'),b'\0\1')
c.put(cache+sym('SPC_PHASE'),bytes(2));cases=0
for start in (0,1,64,127,128,254,255):
 c.put(p+0x15b,bytes([start]));c.put(cache+sym('SPC_CURRENT')+6,bytes([start]))
 for delta in range(-128,128):
  c.put(cache+sym('SPC_NEXT')+6,bytes([(start+delta)&255]))
  for rate in (50,60):
   for phase in (0,3,rate-3-rate%3):
    call('script_present_build',{1:cache,2:gen,3:out,4:p,9:19,10:phase,11:rate},1)
    assert c.get(out+6,1)==bytes([(start+delta*(phase//3)//((rate+2)//3))&255]),(start,delta,rate,phase)
    cases+=1
print(json.dumps(dict(status='passed',heading_fraction_cases=cases)))
c.close()
