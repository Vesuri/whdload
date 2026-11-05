source=open(__file__.replace('test_runtime_forecast_interval_c.py','test_timing_runtime_c.py')).read()
exec(source.split("c.put(ARENA-16,")[0].split('# Loader-facing lookup')[0])
from functools import lru_cache
sym=lru_cache(None)(sym)
def rf(n):return ptr('FORECAST')+sym('RF_'+n)
runs=[];rejections=0
for rate in (50,60):
 c.put(ARENA-16,b'\xa5'*(size+32));c.put(p+24,bytes(1));c.put(h[2]+0x0c,bytes(4));prepare(rate)
 c.put(h[5]+0x60,struct.pack('>I',h[6]));c.put(h[6]+0x4c68,bytes(26));c.put(h[2]+0x1c,struct.pack('>I',100));c.put(p+66,b'\x1c')
 call('timing_runtime_activate',{1:ARENA})
 # Explicit airborne fixture, holding neutral controls; avoid native world events.
 player=bytearray(86);struct.pack_into('>HH',player,0,0x7000,0x8000);struct.pack_into('>H',player,28,4096)
 player[27]=128;player[57]=26;player[66]=28;player[65]=1;player[17]=2;c.put(p,player)
 c.put(ptr('PACKET'),bytes(10));call('endpoint_player_init',{1:ptr('ENDPOINT'),9:rate,10:0})
 span=(rate+2)//3
 call('timing_runtime_forecast_get',{1:ARENA},1);want=c.get(rf('PLAYER'),86)
 call('timing_runtime_forecast_get',{1:ARENA},0)
 call('endpoint_player_begin',{1:ptr('ENDPOINT'),2:p,9:span,10:1})
 for field in range(1,span):
  call('endpoint_player_step',{1:ptr('ENDPOINT'),2:p,3:ptr('STAGES'),4:h[0]+0x7a44,5:ptr('PACKET'),9:field})
  c.put(ptr('CLOCK')+sym('TC_PHASE'),struct.pack('>H',field*3))
  before=c.get(ARENA,sym('RT_FORECAST'));native=c.get(low,length)
  call('timing_runtime_forecast_get',{1:ARENA},0)
  assert c.get(rf('PLAYER'),86)==want and c.get(ARENA,sym('RT_FORECAST'))==before and c.get(low,length)==native
 gates=[(ptr('READY'),4,0),(ptr('CAPTURE_OWNER'),2,0),(ptr('VIEW_PHASE'),2,2),(ptr('BOUNDARY_PHASE'),2,1),(ptr('BATCH'),2,1)]
 gates += [(ptr('SCHEDULER')+sym('TS_'+x),2,1) for x in ('STATE','FIELDS','EXCESS','FAULT')]
 gates += [(ptr(block)+sym(prefix+'_FAULT'),2,1) for block,prefix in (('HISTORY','TH'),('COMMANDS','CQ'),('CLOCK','TC'))]
 gates += [(ptr(block)+sym(prefix+'_ACTIVE'),2,0) for block,prefix in (('HISTORY','TH'),('COMMANDS','CQ'),('CLOCK','TC'))]
 gates += [(ptr('CLOCK')+sym('TC_RATE'),2,49),(ptr('CLOCK')+sym('TC_PHASE'),2,rate),(ptr('ENDPOINT')+sym('EP_TICK'),2,2),(ptr('ENDPOINT')+sym('EP_DONE'),2,span+1),(ptr('ENDPOINT')+sym('EP_DONE'),2,0)]
 for address,width,value in gates:
  saved=c.get(address,width);c.put(address,value.to_bytes(width,'big'));before=c.get(ARENA,size);native=c.get(low,length)
  call('timing_runtime_forecast_get',{1:ARENA},0xfffffffd)
  assert c.get(ARENA,size)==before and c.get(low,length)==native
  c.put(address,saved);rejections+=1
 runs.append(dict(rate=rate,span=span,hits=span))
report=dict(status='passed',runs=runs,atomic_rejections=rejections,native_unchanged=True)
(root/'tmp/c/runtime-forecast-interval-test.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
c.close()
