from pathlib import Path
exec(Path('tools/check_p4_first.py').read_text().split('try:\n',1)[0])
count=0
try:
 for gear in range(1,5):
  for rpm in list(range(6501))+[-32768,-1,6501,32767]+[rng.randint(-32768,32767) for _ in range(500)]:
   def setup(sy):
    write(sy['_phase_state'],bytes(78));pack(sy['_phase_state']+6,'HH',8,8);pack(sy['_phase_state']+12,'I',100<<16);pack(sy['_phase_state']+20,'I',(rpm&65535)<<16);pack(sy['_phase_state']+32,'H',gear);pack(sy['_phase_state']+72,'H',255);pack(sy['_phase_power_status'],'h',1);write(sy['_phase_speed_cache'],bytes(8));write(sy['_time_scalar_state'],bytes(16))
   out=[]
   for j in [0,1]:
    z=run(j,'_phase_prepare_anchor',setup=setup);out.append((read(a4-0x66da,6),read(a4-0x66ca,2),read(a4-0x66ef,1),read(z[0]['_time_scalar_state'],16)))
   assert out[0]==out[1],(gear,rpm,out)
   count+=1
 report=dict(passed=True,cases=count,exhaustive_rpm_per_gear=6501,gears=4,scope='Assembled original/new anchor preparation, all eligible RPM plus signed/out-of-range native fallbacks; native globals and scalar companions exact.')
 Path('tmp/p4-anchor-reciprocal-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
