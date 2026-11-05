"""Retired speed key must behave like an ordinary tail-only command, not pause."""
__file__=__file__.replace('test_retired_speed_clock_c.py','test_runtime_batch_c.py')
exec(open(__file__).read().split('runs=[];yields=0')[0])
runs=[]
for rate in (50,60):
 for batch in (1,3,10):
  states=[]
  for key in (0,12):
   setup(rate);c.put(p+63,b'\6');c.put(p+80,b'\0');initial_rebases=long(ptr('CLOCK')+16)
   speed=c.get(h[6]+0x1548,4)
   for start in range(1,121,batch):
    for n in range(start,min(start+batch,121)):publish(n,key)
    assert pump()==0,(rate,batch,key,start,'unexpected boundary/yield')
   assert long(ptr('CLOCK')+16)==initial_rebases
   assert long(ptr('CLOCK')+12)==long(ptr('HISTORY')+12)==long(ptr('COMMANDS')+16)==long(ptr('COMMANDS')+20)==0
   assert c.get(h[6]+0x1548,4)==speed
   assert long(ptr('SCHEDULER')+32)==120 and long(ptr('SCHEDULER')+36)==360//rate
   assert word(ptr('COMMANDS')+2)==word(ptr('COMMANDS'))==120
   assert word(ptr('COMMANDS')+4)==((360//rate)*rate+2)//3
   states.append((c.get(p,86),c.get(ptr('ENDPOINT'),sym('EP_SIZE')),c.get(ptr('CLOCK'),28),c.get(h[0]+0xc6a0,0xc2)))
  assert states[0]==states[1],(rate,batch)
  runs.append((rate,batch))
print(json.dumps(dict(status='passed',runs=runs,fields=1440,retired_commands=720,player_unread_commands=0,world_reader_at_last_deadline=True,rebases_added=0,discarded_time_input=0,native_speed_values_unchanged=True,tail_only_trajectory_equal=True)))
c.close()
