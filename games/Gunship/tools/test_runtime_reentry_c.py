"""Fresh vs retired-arena activation, followed by identical field controls."""
__file__=__file__.replace('test_runtime_reentry_c.py','test_runtime_batch_c.py')
exec(open(__file__).read().split('runs=[];yields=0')[0])
results=[]
for rate,start_tick in [(50,0),(50,16),(60,0),(60,16)]:
 baseline=None
 for retired in (False,True):
  setup(rate)
  # Saved native initialized mission, including code and object state.
  mission=c.get(low,length)
  if retired:
   for n in range(1,(16*rate+2)//3+1):
    if n==(16*rate+2)//3:c.put(p+24,b'\x01')
    publish(n,0);status=pump()
    assert status==(4 if n==(16*rate+2)//3 else 0),(rate,n,status)
   assert word(ptr('CONSUMER')+sym('TF_PHASE'))==6
  call('timing_runtime_suspend',{1:ARENA})
  if retired:call('timing_runtime_retire',{1:ARENA})
  # Simulate native mission initialization; do not reset private runtime.
  c.put(low,mission)
  c.put(p+12,struct.pack('>H',start_tick))
  c.put(h[6]+0x4c68,bytes(26))
  c.put(h[2]+0x1c,struct.pack('>I',5000))
  c.put(ptr('CAPTURE')+24,struct.pack('>I',2000))
  before=c.get(p,86)
  call('timing_runtime_activate',{1:ARENA})
  assert c.get(p,86)==before
  assert long(ptr('CLOCK'))==5000 and word(ptr('CLOCK')+20)==0
  assert word(ptr('PLAYER_CACHE'))==0
  assert word(ptr('ENDPOINT')+sym('EP_DELAY')+sym('CD_RATE'))==rate
  initial_steps=long(ptr('SCHEDULER')+32);initial_worlds=long(ptr('SCHEDULER')+36)
  trace.clear();poses=[]
  for n in range(1,121):
   call('commands_publish',{1:ptr('COMMANDS'),9:2000+n,10:[0x51,1,2,0x38][n%4]},1)
   c.put(SAMPLE,struct.pack('>6IHhhHII',5000+n,[0,1,0,255][n%4],0,0,0,2000+n,8,0,0,0,10,n))
   call('history_publish',{1:ptr('HISTORY'),2:SAMPLE},1)
   assert pump()==0
   poses.append((c.get(p,86),c.get(ptr('ENDPOINT'),sym('EP_SIZE')),c.get(h[0]+0xc6a0,194)))
  assert long(ptr('SCHEDULER')+32)-initial_steps==120
  assert long(ptr('SCHEDULER')+36)-initial_worlds==360//rate
  assert word(p+12)==start_tick+360//rate
  if baseline is None:baseline=poses
  else:assert poses==baseline,(rate,'stale state after retirement')
  results.append(dict(rate=rate,start_tick=start_tick,retired=retired,fields=120,worlds=360//rate))
print(json.dumps(dict(status='passed',runs=results,complete_player_endpoint_actor_bytes_equal=True,scope='Same-hunk mission initialization and arena reuse; native loader/menu transitions not exercised.')))
c.close()
